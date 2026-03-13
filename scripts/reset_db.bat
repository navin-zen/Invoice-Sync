
rm -f db.sqlite3
python manage.py migrate
env DJANGO_SETTINGS_MODULE=config.settings.development python seed_data/populate_states.py
env DJANGO_SETTINGS_MODULE=config.settings.development python create_gstins.py
env DJANGO_SETTINGS_MODULE=config.settings.development python seed_data/populate_einvoices.py --gstin 29AAFCC9980MZZT
