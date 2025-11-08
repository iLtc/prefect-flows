from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable
import requests


@task(log_prints=True)
def get_access_token() -> str:
    refresh_token = Secret.load("tesla-refresh-token").get()
    client_id = Secret.load("tesla-client-id").get()

    url = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=data, headers=headers).json()

    access_token = response["access_token"]
    new_refresh_token = response["refresh_token"]

    Secret(value=new_refresh_token).save("tesla-refresh-token", overwrite=True)

    print("Access token refreshed")

    return access_token


@task(log_prints=True)
def get_charging_eta(token: str) -> tuple[int, int, int]:
    vehicle_id = Variable.get("tesla-vehicle-id")

    url = f"https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/{vehicle_id}/vehicle_data"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers).json()

    battery_level = response["response"]["charge_state"]["battery_level"]
    target_battery_level = response["response"]["charge_state"]["charge_limit_soc"]
    minutes_to_full_charge = response["response"]["charge_state"]["minutes_to_full_charge"]

    print(f"Battery level: {battery_level}%, Target battery level: {target_battery_level}%, Minutes to full charge: {minutes_to_full_charge} minutes")

    return battery_level, target_battery_level, minutes_to_full_charge


@task(log_prints=True)
def send_notification(battery_level: int, target_battery_level: int, minutes_to_full_charge: int):
    if minutes_to_full_charge > 30:
        print(f"Minutes to full charge is greater than 30 minutes, skipping notification")

        return

    api_key = Secret.load("pushover-api-key").get()
    user_key = Secret.load("pushover-user-key").get()

    time_to_full_charge = ""

    if minutes_to_full_charge < 60:
        time_to_full_charge = f"{minutes_to_full_charge} minutes"
    else:
        time_to_full_charge = f"{minutes_to_full_charge // 60} hours {minutes_to_full_charge % 60} minutes"

    url = 'https://api.pushover.net/1/messages.json'
    data = {
        'token': api_key,
        'user': user_key,
        'title': 'Tesla Charging ETA',
        'message': f'Battery level: {battery_level}%, Target battery level: {target_battery_level}%, Time to full charge: {time_to_full_charge}'
    }

    requests.post(url, data=data)


@flow
def tesla_charging_eta():
    token = get_access_token()
    battery_level, target_battery_level, minutes_to_full_charge = get_charging_eta(token)
    send_notification(battery_level, target_battery_level, minutes_to_full_charge)


if __name__ == "__main__":
    tesla_charging_eta()
