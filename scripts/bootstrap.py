import logging
import argparse
from utils import load_config, request, generate_users_for_keycloak, generate_users_for_camunda, generate_groups, generate_group_tenant_assignments, generate_group_role_assignments, get_required_env, tenant_selection
from auth import get_token

KEYCLOAK_DOMAIN = get_required_env("KEYCLOAK_DOMAIN")
CAMUNDA_REALM = get_required_env("CAMUNDA_REALM")
CAMUNDA_IDENTITY_URL = get_required_env("CAMUNDA_IDENTITY_URL")

KEYCLOAK_ADMIN_URL = f"{KEYCLOAK_DOMAIN}/auth/admin/realms/{CAMUNDA_REALM}"

log = logging.getLogger("bootstrap-module")


def get_user(token, username):
    response = request(
        "GET",
        f"{KEYCLOAK_ADMIN_URL}/users",
        token,
        params={"username": username}
    )

    if response.status_code != 200:
        log.error(
            "User lookup failed | username=%s | status=%s | body=%s",
            username, response.status_code, response.text
        )
        return None

    users = response.json()

    for user in users:
        if user.get("username") == username:
            return user

    return None


def get_realm_role(token, role_name):
    r = request(
        "GET",
        f"{KEYCLOAK_ADMIN_URL}/roles/{role_name}",
        token
    )

    if r.status_code != 200:
        raise RuntimeError(f"Role fetch failed {role_name}: {r.text}")

    return r.json()


def assign_realm_role_to_user(token, username, role_name):
    user = get_user(token, username)
    user_id = user["id"]
    if not user_id:
        log.error("User not found | username=%s", username)
        return

    role = get_realm_role(token, role_name)

    r = request(
        "POST",
        f"{KEYCLOAK_ADMIN_URL}/users/{user_id}/role-mappings/realm",
        token,
        json=[{
            "id": role["id"],
            "name": role["name"]
        }]
    )

    if r.status_code in (204, 200):
        log.info("Role assigned | user=%s | role=%s", username, role_name)
    else:
        log.error(
            "Role assignment failed | user=%s | role=%s | status=%s | body=%s",
            username, role_name, r.status_code, r.text
        )


def create_keycloak_user(token, user_data):
    username = user_data["username"]

    if get_user(token, username):
        log.info("User already exists | username=%s", username)
        return

    response = request(
        "POST",
        f"{KEYCLOAK_ADMIN_URL}/users",
        token,
        json=user_data
    )

    if response.status_code in (200, 201):
        log.info("User created | username=%s", username)
        assign_realm_role_to_user(token, username, "Web Modeler")
    else:
        log.error(
            "User creation failed | username=%s | status=%s | body=%s",
            username, response.status_code, response.text
        )


def tenant_exists(token, tenant_id):
    r = request("GET", f"{CAMUNDA_IDENTITY_URL}/tenants/{tenant_id}", token)
    return r.status_code == 200


def create_tenant(token, tenant):
    if tenant_exists(token, tenant["id"]):
        log.info("Tenant already exists | tenantId=%s", tenant["id"])
        return

    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/tenants",
        token,
        json={"tenantId": tenant["id"], "name": tenant["name"]}
    )

    if r.status_code in (200, 201):
        log.info("Tenant created | tenantId=%s", tenant["id"])
    else:
        log.error("Tenant creation failed | tenantId=%s | status=%s | body=%s",
                  tenant["id"], r.status_code, r.text)


def group_exists(token, group_id):
    r = request("GET", f"{CAMUNDA_IDENTITY_URL}/groups/{group_id}", token)
    return r.status_code == 200


def create_group(token, group):
    if group_exists(token, group["groupId"]):
        log.info("Group already exists | groupId=%s", group["groupId"])
        return

    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/groups",
        token,
        json={"groupId": group["groupId"], "name": group["name"]}
    )

    if r.status_code in (200, 201):
        log.info("Group created | groupId=%s", group["groupId"])
    else:
        log.error("Group creation failed | groupId=%s | status=%s | body=%s",
                  group["groupId"], r.status_code, r.text)


def role_exists_on_group(token, role_id, group_id):
    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/groups/{group_id}/roles/search",
        token,
        json={
            "sort": [{"field": "name", "order": "ASC"}],
            "filter": {"roleId": role_id},
            "page": {"from": 0, "limit": 100}
        }
    )

    if r.status_code != 200:
        log.error("Fetch group roles failed | groupId=%s | status=%s | body=%s",
                  group_id, r.status_code, r.text)
        return False

    roles = r.json().get("items", [])
    return any(role["roleId"] == role_id for role in roles)


def assign_role_to_group(token, role_id, group_id):
    if role_exists_on_group(token, role_id, group_id):
        log.info("Role already assigned | roleId=%s | groupId=%s", role_id, group_id)
        return

    r = request(
        "PUT",
        f"{CAMUNDA_IDENTITY_URL}/roles/{role_id}/groups/{group_id}",
        token
    )

    if r.status_code in (200, 204):
        log.info("Role assigned | roleId=%s | groupId=%s", role_id, group_id)
    else:
        log.error("Role assignment failed | roleId=%s | groupId=%s | status=%s | body=%s",
                  role_id, group_id, r.status_code, r.text)


def user_in_group(token, username, group_id):
    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/groups/{group_id}/users/search",
        token,
        json={
            "sort": [{"field": "username", "order": "ASC"}],
            "page": {"from": 0, "limit": 100}
        }
    )

    if r.status_code != 200:
        log.error("Fetch group users failed | groupId=%s | status=%s | body=%s",
                  group_id, r.status_code, r.text)
        return False

    users = r.json().get("items", [])
    return any(u.get("username") == username for u in users)


def assign_user_to_group(token, username, group_id):
    if user_in_group(token, username, group_id):
        log.info("User already in group | username=%s | groupId=%s", username, group_id)
        return

    r = request(
        "PUT",
        f"{CAMUNDA_IDENTITY_URL}/groups/{group_id}/users/{username}",
        token
    )

    if r.status_code in (200, 204):
        log.info("User assigned to group | username=%s | groupId=%s", username, group_id)
    else:
        log.error("User assignment failed | username=%s | groupId=%s | status=%s | body=%s",
                  username, group_id, r.status_code, r.text)


def authorization_exists(token, username):
    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/authorizations/search",
        token,
        json={
            "sort": [
                {
                "field": "ownerId",
                "order": "ASC"
                }
            ],
            "filter": {
                "ownerId": username,
                "ownerType": "USER",
                "resourceType": "RESOURCE"
            },
            "page": {"from": 0, "limit": 1}
        }
    )

    if r.status_code != 200:
        log.error(
            "Authorization search failed | username=%s | status=%s | body=%s",
            username, r.status_code, r.text
        )
        return False

    items = r.json().get("items", [])
    return len(items) > 0


def create_authorization(token, username):

    if authorization_exists(token, username):
        log.info("Authorization already exists | username=%s", username)
        return

    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/authorizations",
        token,
        json={
            "ownerId": username,
            "ownerType": "USER",
            "resourceId": "*",
            "resourceType": "RESOURCE",
            "permissionTypes": [
                "CREATE",
                "READ",
                "DELETE_DRD",
                "DELETE_FORM",
                "DELETE_PROCESS",
                "DELETE_RESOURCE"
            ]
        }
    )

    if r.status_code in (200, 201, 204):
        log.info("Created Authorization | username=%s", username)
    else:
        log.error(
            "Authorization creation failed | username=%s | status=%s | body=%s",
            username, r.status_code, r.text
        )


def group_assigned_to_tenant(token, group_id, tenant_id):
    r = request(
        "POST",
        f"{CAMUNDA_IDENTITY_URL}/tenants/{tenant_id}/groups/search",
        token,
        json={"page": {"from": 0, "limit": 100}}
    )

    if r.status_code != 200:
        log.error("Fetch tenant groups failed | tenantId=%s | status=%s | body=%s",
                  tenant_id, r.status_code, r.text)
        return False

    groups = r.json().get("items", [])
    return any(g.get("groupId") == group_id for g in groups)


def assign_group_to_tenant(token, group_id, tenant_id):
    if group_assigned_to_tenant(token, group_id, tenant_id):
        log.info("Group already assigned to tenant | groupId=%s | tenantId=%s",
                 group_id, tenant_id)
        return

    r = request(
        "PUT",
        f"{CAMUNDA_IDENTITY_URL}/tenants/{tenant_id}/groups/{group_id}",
        token
    )

    if r.status_code in (200, 204):
        log.info("Group assigned to tenant | groupId=%s | tenantId=%s",
                 group_id, tenant_id)
    else:
        log.error("Group assignment failed | groupId=%s | tenantId=%s | status=%s | body=%s",
                  group_id, tenant_id, r.status_code, r.text)


def main():
    parser = argparse.ArgumentParser(description="Deploy BPMN files")
    parser.add_argument(
        "--region",
        required=True,
        help="Region config file"
    )
    
    parser.add_argument(
        "--tenants",
        required=False,
        help="Tenants List"
    )
    
    args = parser.parse_args()

    cfg = load_config(args.region)
    admin_token = get_token("admin", cfg)
    web_modeler_token = get_token("web-modeler", cfg)
    
    if args.tenants:
        cfg = tenant_selection(args, cfg)
        
    # Generate Keycloak users and create them in Keycloak
    for user in generate_users_for_keycloak(cfg):
        create_keycloak_user(admin_token, user)

    # Create Camunda Tenants
    for tenant in cfg.get("tenants", []):
        create_tenant(web_modeler_token, tenant)

    # Create Camunda Groups
    for group in generate_groups(cfg):
        create_group(web_modeler_token, group)

    # Assign Roles to Groups
    for group_roles in generate_group_role_assignments(cfg, ["readonly-admin"]):
        for role_id in group_roles["roles"]:
            assign_role_to_group(web_modeler_token, role_id, group_roles["group"])
    
    # Generate Camunda Users and assign them to Groups along with Authorizations
    for user in generate_users_for_camunda(cfg):
        assign_user_to_group(web_modeler_token, user["username"], user["group"])
        create_authorization(web_modeler_token, user["username"])

    # Assign Groups to Tenants
    for assignment in generate_group_tenant_assignments(cfg):
        assign_group_to_tenant(web_modeler_token, assignment["group"], assignment["tenant"])


if __name__ == "__main__":
    main()