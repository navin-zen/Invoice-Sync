#!/usr/bin/env bash

ROOT_DIR=$(readlink -f $(dirname $0))
cd ${ROOT_DIR}
rm -rfv .venv
python3 -m venv .venv
./activator pip install -r requirements.txt
