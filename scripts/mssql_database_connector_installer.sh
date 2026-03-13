echo "Updating and upgrading packages"
sudo apt-get update && sudo apt-get upgrade -y

echo "Installing build-essential python3-dev unixodbc-dev python3-venv"
sudo apt-get install build-essential python3-dev unixodbc-dev python3-venv git -y

echo "Downloading and extracting einvoicing-local-ui-latest-2025-04-18.tar.gz"
wget https://img-www.gstzen.in/pdfs/einvoicing-local-ui/einvoicing-local-ui-latest-2025-04-18.tar.gz -O einvoicing-local-ui-latest-2025-04-18.tar.gz
tar -zxf einvoicing-local-ui-latest-2025-04-18.tar.gz
mv projects/einvoicing-local-UI/server einvoicing-local-ui
rm -rf projects einvoicing-local-ui-latest-2025-04-18.tar.gz

echo "Creating static files"
cd einvoicing-local-UI/config/static
mkdir generated
mkdir generated/javascript

cd ../../
mkdir .staticfiles
mkdir .staticfiles/generated
mkdir .staticfiles/generated/javascript

cd ../../
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' \
    -O einvoicing-local-UI/config/static/generated/javascript/bundle.js
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' \
    -O einvoicing-local-UI/.staticfiles/generated/javascript/bundle.js
wget https://img-www.gstzen.in/pdfs/einvoicing-local-ui/vite.tar.gz -O vite.tar.gz
tar -zxf vite.tar.gz
sudo rm -rf einvoicing-local-UI/config/static/vite
sudo mv dist einvoicing-local-UI/config/static/vite
sudo rm -rf vite.tar.gz

echo "Installing requirements"
cd einvoicing-local-UI
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
export PATH=".venv/bin:$PATH"
uv sync

echo "Resetting the database"
bash scripts/reset_db.sh

echo "Installing tdsodbc"
sudo apt-get install tdsodbc -y
sudo odbcinst -i -d -f /usr/share/tdsodbc/odbcinst.ini

echo "Starting the connector"
./activator .envs/.development services/rev-specific/keep-supervisor-alive

echo "Installation complete. Open http://localhost:9007/e/ to access the interface."
