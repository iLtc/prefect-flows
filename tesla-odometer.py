from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from tesla_utils import get_access_token
from datetime import datetime
import pytz


@task(log_prints=True)
def get_odometer(token: str) -> int:
    vehicle_id = Variable.get("tesla-vehicle-id")

    url = f"https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/{vehicle_id}/vehicle_data"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers).json()

    odometer = int(response["response"]["vehicle_state"]["odometer"])

    print(f"Odometer: {odometer} miles")

    return odometer


@task(log_prints=True)
def update_spreadsheet(odometer: int):
    json_data = Secret.load("google-service-account-permupdate").get()
    tesla_sheet_id = Secret.load("perm-sheet-id").get()

    credentials = service_account.Credentials.from_service_account_info(json_data)
    service = build("sheets", "v4", credentials=credentials)

    service.spreadsheets().values().update(
        spreadsheetId=tesla_sheet_id,
        range="Tesla!K1",
        valueInputOption="RAW",
        body={"values": [[odometer]]}
    ).execute()

    current_time = datetime.now(pytz.timezone('America/Los_Angeles'))
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    service.spreadsheets().values().update(
        spreadsheetId=tesla_sheet_id,
        range="Tesla!N1",
        valueInputOption="RAW",
        body={"values": [[current_time_str]]}
    ).execute()


@flow
def tesla_odometer():
    token = get_access_token()
    odometer = get_odometer(token)
    update_spreadsheet(odometer)


if __name__ == "__main__":
    tesla_odometer()