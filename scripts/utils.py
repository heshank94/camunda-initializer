import requests
import yaml
import logging
import os

TIMEOUT = 15

# ------------------ LOGGING ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ------------------ CONFIG ------------------
def load_config(file_path="../config.yaml"):
    if not os.path.exists(file_path):
        raise RuntimeError(f"Config file not found: {file_path}")
    with open(file_path) as f:
        return yaml.safe_load(f)

# ------------------ HTTP ------------------
def headers(token, content_type="application/json"):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
        "Accept": "application/json"
    }

def request(method, url, token, **kwargs):
    try:
        r = requests.request(
            method,
            url,
            headers=headers(token, kwargs.pop("content_type", "application/json")),
            timeout=TIMEOUT,
            **kwargs
        )
        return r
    except requests.RequestException as e:
        logging.getLogger("utils").error("HTTP request failed | %s %s | %s", method, url, str(e))
        raise
    
def generate_users_for_camunda(config):
    camunda_users = []

    for tenant in config.get("tenants", []):
        tenant_id = tenant["id"]
        camunda_users.append({
            "username": f"{tenant_id.lower()}-user",
            "password": f"{tenant_id.lower()}-user-123",
            "group": f"{tenant_id.lower()}-team",
            "tenant": tenant_id
        })
    return camunda_users


def generate_users_for_keycloak(config):
    keycloak_users = []

    for tenant in config.get("tenants", []):
        tenant_id = tenant["id"].lower()
        username = f"{tenant_id}-user"
        password = f"{tenant_id}-user-123"

        keycloak_users.append({
            "username": username,
            "enabled": True,
            "email": f"{username}@gmail.com",
            "firstName": tenant_id,
            "lastName": "User",
            "credentials": [
                {
                    "type": "password",
                    "value": password,
                    "temporary": False
                }
            ]
        })        
    return keycloak_users


def generate_groups(config):
    groups = []

    for tenant in config.get("tenants", []):
        tenant_id = tenant["id"]
        groups.append({
            "groupId": f"{tenant_id.lower()}-team",
            "name": f"{tenant_id.upper()} Team"
        })
    return groups


def generate_group_tenant_assignments(config):
    assignments = []

    for tenant in config.get("tenants", []):
        tenant_id = tenant["id"]

        assignments.append({
            "group": f"{tenant_id.lower()}-team",
            "tenant": tenant_id
        })
    return assignments


def generate_group_role_assignments(config, roles=None):
    if roles is None:
        roles = ["readonly-admin"]

    assignments = []

    for tenant in config.get("tenants", []):
        tenant_id = tenant["id"]

        assignments.append({
            "group": f"{tenant_id.lower()}-team",
            "roles": roles
        })
    return assignments