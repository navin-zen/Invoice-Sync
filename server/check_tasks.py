import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from gstnapi.models import ScheduledTask

try:
    tasks = ScheduledTask.objects2.to_be_run()
    print(f"To be run tasks count: {tasks.count()}")
except Exception as e:
    print(f"Error checking tasks: {e}")
