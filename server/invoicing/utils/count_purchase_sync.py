
import datetime
from invoicing.models import PurchaseInvoice
from invoicing.utils.utils import month_range

def get_purchase_count_details(status_details, date_range_details, gstin=None, session=None):
    qs = PurchaseInvoice.objects2
    if gstin:
        qs = qs.filter(gstin=gstin)
    if session:
        qs = qs.filter(upload_uuid=session.uuid)

    count_details = []
    for (start, end), datelabel in date_range_details:
        row = {
            "label": datelabel,
            "start_date": start,
            "end_date": end,
        }
        row.update(
            {
                label: qs.filter(
                    purchase_status__in=statuses,
                    create_date__date__range=[start, end],
                ).count()
                for statuses, label in status_details
            }
        )
        count_details.append(row)

    # Add "All Time" row (no date filter)
    all_time_row = {
        "label": "All Time",
        "start_date": None,
        "end_date": None,
    }
    all_time_row.update(
        {
            label: qs.filter(
                purchase_status__in=statuses,
            ).count()
            for statuses, label in status_details
        }
    )
    count_details.append(all_time_row)

    return count_details

def get_purchase_sync_count_json(gstin=None, session=None):
    today = datetime.date.today()
    _, _, DOW = today.isocalendar()
    week_start = today - datetime.timedelta(days=DOW)
    month_start = today.replace(day=1)
    yesterday = today - datetime.timedelta(days=1)

    week = (week_start, today)
    prev_week = (week_start - datetime.timedelta(days=7), week_start - datetime.timedelta(days=1))
    month = (month_start, today)
    prev_month = month_range(month_start - datetime.timedelta(days=1))

    status_choices = [
        ([PurchaseInvoice.PIS_ERROR], "error"),
        ([PurchaseInvoice.PIS_CANDIDATE], "pending"),
        ([PurchaseInvoice.PIS_UPLOADED], "uploaded"),
        (
            [PurchaseInvoice.PIS_ERROR, PurchaseInvoice.PIS_CANDIDATE, PurchaseInvoice.PIS_UPLOADED],
            "total",
        ),
    ]

    date_range_details = [
        ((today, today), "Today"),
        ((yesterday, yesterday), "Yesterday"),
        (week, "Week"),
        (prev_week, "Previous Week"),
        (month, "Month to date"),
        (prev_month, "Previous month"),
    ]

    return get_purchase_count_details(status_choices, date_range_details, gstin=gstin, session=session)


