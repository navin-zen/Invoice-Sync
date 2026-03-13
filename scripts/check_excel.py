import os

import click

if __name__ == "__main__":
    import sys

    import django

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from utils.importer import CustomXls


@click.command()
@click.option("--file-path", help="The file path of the excel file")
# @click.option("--sheet-number", help="The sheet number for which you want the headers")

# Uncomment the above @click.option when executing get_headers function with sheet_number as the 2nd argument


def run(file_path):
    content = open(file_path, "rb").read()
    in_stream = open(file_path, "rb")  # NOQA
    # CustomXls.get_worksheets(content)
    # CustomXls.get_excel_data(content)

    CustomXls.get_header_rows(content)


if __name__ == "__main__":
    run()
