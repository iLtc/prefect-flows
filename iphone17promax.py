from prefect import flow, task
from prefect.blocks.system import Secret
import requests

@task
def get_stores() -> list[dict]:
    url = 'https://www.apple.com.cn/shop/fulfillment-messages?fae=true&pl=true&mts.0=regular&parts.0=MG064CH/A&location=%E5%AE%89%E5%BE%BD%20%E5%90%88%E8%82%A5%20%E7%91%B6%E6%B5%B7%E5%8C%BA'

    r = requests.get(url)
    return r.json()['body']['content']['pickupMessage']['stores']


@task
def check_availability(stores: list[dict]) -> list[str]:
    results = []

    for store in stores:
        if '可取货' in store['partsAvailability']['MG064CH/A']['pickupSearchQuote']:
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
        'title': 'iPhone 17 Pro Max 有货了',
        'message': '在以下门店有货：' + ', '.join(results)
    }

    requests.post(url, data=data)


@flow
def main():
    stores = get_stores()
    results = check_availability(stores)
    send_notification(results)


if __name__ == "__main__":
    main()