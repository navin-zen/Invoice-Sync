import django

if __name__ == "__main__":
    django.setup()

from einvoicing.models import GstIn, PermanentAccountNumber

from taxmaster.models import State


def main():
    pan = PermanentAccountNumber(number="AAFCC9980M", name="GSTZen Demo Private Limited")
    pan.full_clean()
    pan.save()
    for g in ["29AAFCC9980MZZT"]:
        gstin = GstIn(permanentaccountnumber=pan, state=State.objects.get(code=g[:2]), gstin=g, name=pan.name)
        gstin.full_clean()
        gstin.save()


if __name__ == "__main__":
    main()
