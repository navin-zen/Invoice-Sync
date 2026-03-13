import os

if __name__ == "__main__":
    import sys

    import django

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from utils.database import CustomDatabase


def run():
    CustomDatabase.test_database_connection()
    # CustomDatabase.display_tables_in_database()
    # CustomDatabase.display_all_columns_in_table()


if __name__ == "__main__":
    run()
