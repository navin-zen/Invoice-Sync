"""
Utilities related to summarizing status of Purchase Invoices import session.
"""

from invoicing.models import CachedData
from invoicing.utils.count_purchase_sync import get_purchase_sync_count_json


def get_sync_details():
    """
    Returns details of the recently completed and currently running sync
    sessions.
    """
    ###########################################################
    # First, get the recently completed session
    completed_session_end_marker = CachedData.objects2.datatype(CachedData.DT_PURCHASE_FINISH).youngest()
    if completed_session_end_marker:
        completed_session = completed_session_end_marker.group
    else:
        completed_session = None
    ###########################################################
    # Next, get the recent session
    in_progress_session = CachedData.objects2.datatype(CachedData.DT_PURCHASE_SESSION_MARKER).youngest()
    if in_progress_session == completed_session:
        # If recent session has already completed, we have no session in progress.
        in_progress_session = None
    ###########################################################
    return {
        "completed_session": session_sync_details(completed_session),
        "in_progress_session": session_sync_details(in_progress_session),
    }


def session_sync_details(session):
    """
    Return details of a sync session.
    """
    if not session:
        return None
    assert isinstance(session, CachedData) and (session.datatype == CachedData.DT_PURCHASE_SESSION_MARKER)
    error_cd = CachedData.objects2.datatype(CachedData.DT_PURCHASE_ERRORS).filter(group=session).first()
    return {
        "uuid": session.uuid,
        "create_date": session.create_date,
        "modify_date": session.modify_date,
        "sync_summary": get_purchase_sync_count_json(session=session),
        "errors": error_cd and error_cd.data_json,
    }


