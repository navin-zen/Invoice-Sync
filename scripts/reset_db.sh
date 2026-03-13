
set -e
set -v
rm -f db.sqlite3
./activator .envs/.development python manage.py migrate
./activator .envs/.development python seed_data/populate_states.py
#./activator env DJANGO_SETTINGS_MODULE=config.settings.development python create_gstins.py
#./activator env DJANGO_SETTINGS_MODULE=config.settings.development python seed_data/populate_einvoices.py --gstin 29AAFCC9980MZZT
