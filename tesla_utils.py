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