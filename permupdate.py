from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pytz

@task(log_prints=True)
def get_updates() -> list[int]:
    data = Variable.get("permupdate")

    response = requests.get(data["url"]).json()
    monthly_backlog = response["monthly_backlog"]

    month_to_backlog = {}

    for month in monthly_backlog:
        month_to_backlog[month["month"]] = month["backlog"]

    results = []

    for month in data["months"]:
        results.append(month_to_backlog[month])

    print(results)

    return results


@task(log_prints=True)
def update_spreadsheet(results: list[int]):
    json_data = Secret.load("google-service-account-permupdate").get()
    perm_sheet_id = Secret.load("perm-sheet-id").get()

    credentials = service_account.Credentials.from_service_account_info(json_data)
    service = build("sheets", "v4", credentials=credentials)

    range = "PERM!B2:B18"

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=perm_sheet_id, range=range)
        .execute()
    )
    old_rows = result.get("values", [])

    new_rows = [[x] for x in results]

    needs_update = False

    for old, new in zip(old_rows, new_rows):
        if int(old[0].replace(",", "")) != new[0]:
            needs_update = True
            break

    if not needs_update:
        print("No updates needed")
        return

    body = {
        "values": new_rows
    }

    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=perm_sheet_id,
            range=range,
            valueInputOption="USER_ENTERED",
            body=body
        )
        .execute()
    )

    print(f"{result.get('updatedCells')} cells updated.")

    current_time = datetime.now(pytz.timezone('America/Los_Angeles'))
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

    service.spreadsheets().values().update(
        spreadsheetId=perm_sheet_id,
        range="PERM!I1",
        valueInputOption="RAW",
        body={"values": [[current_time_str]]}
    ).execute()


@flow
def permupdate():
    results = get_updates()
    update_spreadsheet(results)


if __name__ == "__main__":
    permupdate()