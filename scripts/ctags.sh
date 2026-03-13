#!/usr/bin/env bash

ctags --exclude='*.pxd' --exclude='*.js' --exclude='*/migrations/00*.py' --exclude='*/deprecated/*' \
    --python-kinds=-i -R \
    einvoicing cz_utils gstnapi \
    .venv/lib/python3.?/site-packages .venv/src
