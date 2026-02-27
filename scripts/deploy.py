from scripts.utils import load_config
import requests
import logging
import os
from scripts.auth import get_token_with_username_and_password

DEPLOY = "http://localhost:8088/v2/deployments"
CONFIG_FILE = "config.yaml"
PROCESS_FOLDER = "processes"
TIMEOUT = 15
log = logging.getLogger("deploy-module")

def headers(token): return {"Authorization": f"Bearer {token}"}

def deploy_file(token, tenant, path):
    with open(path, "rb") as f:
        files = {
            "resources": (os.path.basename(path), f, "application/octet-stream")
        }

        data = {"tenantId": tenant}
        r = requests.post(
            DEPLOY,
            headers=headers(token),
            files=files,
            data=data,
            timeout=TIMEOUT
        )

    if r.status_code in (200, 201):
        log.info("Deployment success | tenant=%s | file=%s", tenant, os.path.basename(path))
    else:
        log.error(
            "Deployment failed | tenant=%s | file=%s | status=%s | body=%s",
            tenant,
            os.path.basename(path),
            r.status_code,
            r.text
        )


def validate_deployments(entries):
    for i, d in enumerate(entries):
        if "tenant" not in d or "username" not in d or "password" not in d:
            raise ValueError(f"Invalid deployment entry at index {i}: {d}")


def main():
    cfg = load_config()
    deployments = cfg.get("deployments", [])

    if not deployments:
        log.warning("No deployments section found. Nothing to deploy.")
        return

    validate_deployments(deployments)

    if not os.path.isdir(PROCESS_FOLDER):
        raise RuntimeError(f"Process folder not found: {PROCESS_FOLDER}")

    process_files = [
        f for f in os.listdir(PROCESS_FOLDER)
        if f.endswith(".bpmn")
    ]

    if not process_files:
        log.warning("No BPMN files found in folder: %s", PROCESS_FOLDER)
        return

    for entry in deployments:
        tenant = entry["tenant"]
        username = entry["username"]
        password = entry["password"]

        log.info("Authenticating | user=%s | tenant=%s", username, tenant)

        try:
            token = get_token_with_username_and_password(
                username=username,
                password=password
            )
        except Exception as e:
            log.error("Authentication failed | user=%s | error=%s", username, str(e))
            continue

        for file in process_files:
            path = os.path.join(PROCESS_FOLDER, file)
            deploy_file(token, tenant, path)

    log.info("All deployments completed")


if __name__ == "__main__":
    main()