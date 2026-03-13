"""
Utilities for Pusher
"""

import uuid

from django.conf import settings
from django.contrib.messages.storage.base import LEVEL_TAGS

from cz_utils.json_schema import Integer, JsonValidator, Object, String

# from pusher import Pusher

# pusher = Pusher(
#     app_id=settings.PUSHER_APP_ID,
#     key=settings.PUSHER_KEY,
#     secret=settings.PUSHER_SECRET,
#     cluster=settings.PUSHER_CLUSTER,
# )
pusher = None

# https://docs.djangoproject.com/en/1.11/ref/contrib/messages/#message-tags
LevelTag = String(
    enum=[
        "debug",
        "info",
        "success",
        "warning",
        "danger",
    ]
)

Notification = Object(
    properties={
        "type": String(enum=["notification"]),
        "message": String,
        "level": Integer,
        "level_tag": LevelTag,
    },
    required=[
        "type",
        "message",
        "level",
        "level_tag",
    ],
)

# Describe the current progress of some activity
# For example: Processing Invoices: 23 / 100 (23% complete)
Progress = Object(
    properties={
        "type": String(enum=["progress"]),
        "message": String,
        "current": Integer,
        "total": Integer,
    },
    required=[
        "type",
        "message",
        "current",
        "total",
    ],
)

# The output of deferred view, the URL to download the generated file
DeferredOutput = Object(
    properties={
        "type": String(enum=["deferredoutput"]),
        "url": String,
        "message": String,
    },
    required=[
        "type",
        "url",
    ],
)

# Just a ping to client and the client can do whatever they want.
Ping = Object(
    properties={
        "type": String(enum=["ping"]),
    },
    required=["type"],
)

NotificationValidator = JsonValidator(Notification)
ProgressValidator = JsonValidator(Progress)
DeferredOutputValidator = JsonValidator(DeferredOutput)
PingValidator = JsonValidator(Ping)


def trigger(channel_name, event_name, data, fail_silently=False):
    """
    Publish a message to a channel.

    :param: channel_name - The name of the channel (a string)
    :param: event_name - The name of the event to publish (a string)
    :param: data - The data payload
    """
    if not channel_name.startswith("private-"):
        raise ValueError("We only allow publishing to private channels.")
    if getattr(settings, "IS_TESTING", None):
        return
    try:
        pusher.trigger(channel_name, event_name, data)
    except Exception:
        if fail_silently:
            pass
        else:
            raise


def trigger_notification(channel_name, level, message, fail_silently=False):
    """
    Publish a notification message
    """
    data = {
        "type": "notification",
        "message": message,
        "level": level,
        "level_tag": LEVEL_TAGS[level],
    }
    NotificationValidator(data)
    trigger(channel_name, "all", data, fail_silently)


def trigger_progress(channel_name, data, fail_silently=False):
    """
    Publish a progress message
    """
    data["type"] = "progress"
    ProgressValidator(data)
    trigger(channel_name, "all", data, fail_silently)


def trigger_deferred_output(channel_name, url, message="", fail_silently=False):
    """
    Publish a deferredoutput message
    """
    data = dict(type="deferredoutput", url=url, message=message)
    DeferredOutputValidator(data)
    trigger(channel_name, "all", data, fail_silently)


def trigger_ping(channel_name, fail_silently=False):
    data = dict(type="ping")
    PingValidator(data)
    trigger(channel_name, "all", data, fail_silently)


def new_channel():
    """
    Return the name of a new channel.
    """
    return "private-" + uuid.uuid4().hex
