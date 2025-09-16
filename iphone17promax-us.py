from prefect import flow, task
from prefect.blocks.system import Secret
import requests

@task
def get_stores() -> list[dict]:
    url = 'https://www.apple.com/shop/fulfillment-messages?fae=true&pl=true&mts.0=regular&cppart=ATT_IPHONE17PRO&parts.0=MFXM4LL/A&location=San%20Jose,%20CA'

    r = requests.get(url)
    return r.json()['body']['content']['pickupMessage']['stores']


@task
def check_availability(stores: list[dict]) -> list[str]:
    results = []

    for store in stores:
        if 'Fri Sep 19' in store['partsAvailability']['MFXM4LL/A']['pickupSearchQuote']:
            results.append(store['storeName'])

    return results


@task
def send_notification(results: list[str]):
    if len(results) == 0:
        return

    api_key = Secret.load("pushover-api-key").get()
    user_key = Secret.load("pushover-user-key").get()

    url = 'https://api.pushover.net/1/messages.json'
    data = {
        'token': api_key,
        'user': user_key,
        'title': 'iPhone 17 Pro Max in US',
        'message': '在以下门店有货：' + ', '.join(results) + '，快去抢吧！'
    }

    requests.post(url, data=data)


@flow
def iphone17promax_us():
    stores = get_stores()
    results = check_availability(stores)
    send_notification(results)


if __name__ == "__main__":
    # iphone17promax_us()

    iphone17promax_us.from_source(
        source="https://github.com/iLtc/prefect-flows.git",
        entrypoint="iphone17promax-us.py:iphone17promax_us"
    ).deploy(
        name="iphone17promax-us",
        work_pool_name="docker-pool",
        cron="*/5 * * * *"
    )