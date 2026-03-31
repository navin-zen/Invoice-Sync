import os
import sys

# Setup Django
if __name__ == "__main__":
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()

from invoicing.models import GstIn, PermanentAccountNumber
from taxmaster.models import State

gstins = [
    "33AAACE3061A1ZI",
    "03AAACE3061A1ZL",
    "05AAACE3061A1ZH",
    "06AAACE3061A1ZF",
    "07AAACE3061A2ZC",
    "08AAACE3061A1ZB",
    "09AAACE3061A1Z9",
    "19AAACE3061A1Z8",
    "21AAACE3061A1ZN",
    "23AAACE3061A1ZJ",
    "24AAACE3061A1ZH",
    "27AAACE3061A1ZB",
    "29AAACE3061A1Z7",
    "30AAACE3061A1ZO",
    "32AAACE3061A1ZK",
    "34AAACE3061A1ZG",
    "36AAACE3061A1ZC",
    "37AAACE3061A1ZA",
]


def add_gstins():
    added_count = 0
    # Remove duplicates but maintain order
    unique_gstins = []
    for g in gstins:
        if g not in unique_gstins:
            unique_gstins.append(g)

    for i, gstin_str in enumerate(unique_gstins, start=1):
        gstin_str = gstin_str.strip().upper()
        if not gstin_str:
            continue

        pan_str = gstin_str[2:12]
        state_code = gstin_str[:2]
        name = f"g{i + 1}"

        try:
            # 1. Get/Create PAN
            pan, _ = PermanentAccountNumber.objects.get_or_create(
                number=pan_str, defaults={"name": name}
            )

            # 2. Get State
            state = State.objects.get(code=state_code)

            # 3. Get/Create GSTIN
            gstin, created = GstIn.objects.get_or_create(
                gstin=gstin_str,
                defaults={"name": name, "permanentaccountnumber": pan, "state": state},
            )

            if created:
                print(f"Added GSTIN: {gstin_str} with name: {name}")
                added_count += 1
            else:
                print(f"GSTIN {gstin_str} already exists.")

        except State.DoesNotExist:
            print(
                f"Error: State with code {state_code} not found for GSTIN {gstin_str}"
            )
        except Exception as e:
            print(f"Error adding {gstin_str}: {e}")

    print(f"\nDone! Added {added_count} new GSTINs.")


if __name__ == "__main__":
    add_gstins()
