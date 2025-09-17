from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

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

    values = [[x] for x in results]
    body = {
        "values": values
    }

    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=perm_sheet_id,
            range="PERM!B2:B18",
            valueInputOption="USER_ENTERED",
            body=body
        )
        .execute()
    )

    print(f"{result.get('updatedCells')} cells updated.")


@flow
def permupdate():
    results = get_updates()
    update_spreadsheet(results)


if __name__ == "__main__":
    permupdate()