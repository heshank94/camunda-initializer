import logging
import requests
from utils import get_required_env

KEYCLOAK_DOMAIN = get_required_env("KEYCLOAK_DOMAIN")
CAMUNDA_REALM = get_required_env("CAMUNDA_REALM")

ADMIN_TOKEN_URL = f"{KEYCLOAK_DOMAIN}/auth/realms/master/protocol/openid-connect/token"
TOKEN_URL = f"{KEYCLOAK_DOMAIN}/auth/realms/{CAMUNDA_REALM}/protocol/openid-connect/token"
log = logging.getLogger("auth-module")

# ------------------ TOKEN ------------------
def request_token(data: dict, url) -> str:
    try:
        r = requests.post(url, data=data, timeout=10)
    except requests.RequestException as e:
        raise RuntimeError(f"Token request failed: {e}")

    if r.status_code != 200:
        raise RuntimeError(f"Token request failed | status={r.status_code} | body={r.text}")

    body = r.json()
    if "access_token" not in body:
        raise RuntimeError(f"Access token missing in response: {body}")

    return body["access_token"]

def get_token(client: str, cfg) -> str:
    client_cfg = cfg["camunda"][client]
    
    url = ADMIN_TOKEN_URL if client == "admin" else TOKEN_URL
    
    log.info("Requesting token | user=%s | url=%s", client_cfg["username"], url)

    return request_token({
        "grant_type": "password",
        "client_id": client_cfg["client_id"],
        "username": client_cfg["username"],
        "password": client_cfg["password"]
    }, url)

def get_token_with_username_and_password(username: str, password: str) -> str:
    log.info("Requesting token | user=%s", username)

    return request_token({
        "grant_type": "password",
        "client_id": "web-modeler",
        "username": username,
        "password": password
    }, TOKEN_URL)