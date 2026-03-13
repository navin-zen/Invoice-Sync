from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf.urls import url
from einvoicing import consumers

application = ProtocolTypeRouter(
    {
        # Empty for now (http->django views is added by default)
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(
                    [
                        url(r"^e/gstins/$", consumers.EinvoicingConsumer),
                    ]
                ),
            )
        ),
    }
)
