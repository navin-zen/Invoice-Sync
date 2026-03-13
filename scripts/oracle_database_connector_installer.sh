sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install build-essential python3-dev unixodbc-dev python3-venv -y
wget https://img-www.gstzen.in/pdfs/einvoicing-local-ui/einvoicing-local-ui-latest.tar.gz -O einvoicing-local-ui-latest.tar.gz
tar -zxf einvoicing-local-ui-latest.tar.gz
cd projects/einvoicing-local-UI/config/static
mkdir generated
mkdir generated/javascript
cd ../../
mkdir .staticfiles
mkdir .staticfiles/generated
mkdir .staticfiles/generated/javascript
cd ../../
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O projects/einvoicing-local-UI/config/static/generated/javascript/bundle.js
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O projects/einvoicing-local-UI/.staticfiles/generated/javascript/bundle.js
cd projects/einvoicing-local-UI
python3 -m venv .venv
sudo apt install git -y
./activator pip install -r requirements.txt
bash reset_db.sh
wget https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basic-linux.x64-21.1.0.0.0.zip
sudo apt install unzip -y
unzip instantclient-basic-linux.x64-21.1.0.0.0.zip
sudo apt-get install libaio1 -y
.envs/.development services/rev-specific/keep-supervisor-alive
