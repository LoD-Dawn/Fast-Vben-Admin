#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python -m app.backend_pre_start

# The prestart container uses the administrator credential. Application containers
# receive only the app_runtime credential after this provisioning step.
python -m app.platform.provision_db_roles

# Run the selected edition under the module migration orchestrator
python -m app.modules.migrate --edition "${APP_EDITION:-suite}"

# New tables created by the selected migrations must be visible to the runtime role.
python -m app.platform.provision_db_roles

# Seed through the same non-superuser credential used by API and Worker processes.
POSTGRES_USER="$APP_RUNTIME_DB_USER" \
POSTGRES_PASSWORD="$APP_RUNTIME_DB_PASSWORD" \
python -m app.initial_data
