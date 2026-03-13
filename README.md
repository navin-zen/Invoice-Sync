# On-Prem E-Invoice Server

## Local Development

- Sync the pacakages for the project

```sh
uv sync
```

- Setup the database

```sh
./script/reset_db.sh
```

- Build the frontend

```sh
❯ cd frontend/
❯ pnpm install
❯ pnpm build-js
❯ pnpm build-css
```

- Run the server

```sh
❯ cd backend/
❯ ./activator .envs/.development ./manage.py runserver 0.0.0.0:9007
```

## Client Installation

Assuming the user has Ubuntu 24.04 LTS on WSL2

- Install dependencies

```sh
❯ sudo apt update && sudo apt upgrade
❯ sudo apt-get install build-essential python3-dev unixodbc-dev python3-venv
```

- Get the latest image from s3

```sh
❯ wget https://img-www.gstzen.in/pdfs/einvoicing-local-ui/einvoicing-local-ui-latest-2025-04-18.tar.gz -O einvoicing-local-ui-latest.tar.gz
❯ tar -zxf einvoicing-local-ui-latest.tar.gz
❯ cd einvoicing-local-UI
❯ cd config/static
❯ mkdir generated
❯ mkdir generated/javascript
❯ cd ../../
❯ mkdir .staticfiles
❯ mkdir .staticfiles/generated
❯ cd ~
❯ wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O einvoicing-local-UI/config/static/generated/javascript/bundle.js
❯ wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O einvoicing-local-UI/.staticfiles/generated/javascript/bundle.js
❯
```

```sh
bash reset_db.sh
```



```sh
./activator .envs/.development services/rev-specific/keep-supervisor-alive
# Check process status first
./activator .envs/.development supervisorctl -c services/rev-specific/supervisord.conf status
# View autosync logs
tail -f services/rev-specific/autosync/autosync.log
tail -f services/rev-specific/autosync/autosync.err
# View run_tasks logs
tail -f services/rev-specific/run_tasks/run_tasks.err

# Stop just one program
./activator .envs/.development supervisorctl -c services/rev-specific/supervisord.conf shutdown


./activator .envs/.development supervisorctl -c services/rev-specific/supervisord.conf stop run_tasks
# Restart just one program (useful after code changes)
./activator .envs/.development supervisorctl -c services/rev-specific/supervisord.conf restart run_tasks
# Restart all programs
./activator .envs/.development supervisorctl -c services/rev-specific/supervisord.conf restart all


./activator .envs/.development python seed_data/populate_states.py
```

```sh
We will need to find a better way to provide the bundle.js.
```

```sh
Install Oracle instantclient for Oracle DB integration
```

```sh
wget <https://download.oracle.com/otn_software/linux/instantclient/211000/
```

instantclient-basic-linux.x64-21.1.0.0.0.zip>

```sh
sudo apt install unzip
```

```sh
unzip instantclient-basic-linux.x64-21.1.0.0.0.zip
```

```sh
vim activator (enter the correct version of the instantclient)
```

```sh
sudo apt-get install libaio1
```

```sh
Install FreeTDS driver for Microsoft SQL Server Integration
```

```sh
sudo apt-get install tdsodbc
```

```sh
sudo odbcinst -i -d -f /usr/share/tdsodbc/odbcinst.ini
```
# Invoice-Sync
