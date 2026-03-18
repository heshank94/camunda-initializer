## Steps to Execute Scripts

- Make sure camunda docker compose containers are up and working with multi tenancy enabled.
- Enable "Direct access grants" for web-modeler client id.

- Use below env variables

```cmd
export CAMUNDA_WEB_MODELER_USERNAME=demo
export CAMUNDA_WEB_MODELER_PASSWORD=demo
export KEYCLOAK_DOMAIN=http://localhost:18080
export CAMUNDA_REALM=camunda-platform
export CAMUNDA_IDENTITY_URL=http://localhost:8088/v2
```
    

- Navigate to scripts
    - cd scripts

- Run bootstrap script (tenants optional)

    `py bootstrap.py --region=<config_name> --tenants=<list_of_tenants>`
    

- Run deploy script (tenants optional)
    
    `py deploy.py --region=<config_name> --tenants=<list_of_tenants>`