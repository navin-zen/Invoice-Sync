if __name__ == "__main__":
    import django

    django.setup()

import sys
import time

from django.db.models import F
from django.utils import timezone
from invoicing.utils.purchase_gstzen_cloud import post_all_purchases_to_gstzen
from scripts.backup_configuration import main as backup_main

from gstnapi.models import ScheduledTask


def delete_tasks_older_than_a_week():
    print(timezone.now().isoformat(), "Deleting tasks older than a week", file=sys.stderr, flush=True)
    ScheduledTask.objects2.can_be_cleared().delete()


def main():
    counter = 0
    while True:
        if counter == 0:
            counter = 21600
            delete_tasks_older_than_a_week()
            # backup_main() skip for now
        counter -= 1
        for st in ScheduledTask.objects2.to_be_run().created_since(300):
            print(st, file=sys.stderr, flush=True)
            ScheduledTask.objects2.filter(uuid=st.uuid).update(
                status=ScheduledTask.S_RUNNING,
                invocation_time=timezone.now(),
                num_tries=F("num_tries") + 1,
            )
            st.execute_once()
        try:
            post_all_purchases_to_gstzen()
        except Exception as ex:
            print(ex, file=sys.stderr, flush=True)
        print(timezone.now().isoformat(), "All is well", file=sys.stderr, flush=True)
        time.sleep(4)


if __name__ == "__main__":
    main()
