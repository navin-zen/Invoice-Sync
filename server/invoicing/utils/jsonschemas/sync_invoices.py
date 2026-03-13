"""
Schema for Invoicing Sync Invoices View
"""

from pygstn.utils import json

from cz_utils.json_schema import Array, Boolean, JsonValidator, Object, Ref, StrictObject, String, Type

SyncInvoicesEntrypointArg = StrictObject(
    dict(
        id=String,
        syncUrl=String,
    )
)

SyncInvoicesUrls = StrictObject(dict(sync_invoices=String, status=String))

SyncInvoicesResponse = StrictObject(
    dict(
        session_uuid=String,
        urls=Ref("SyncInvoicesUrls"),
    )
)

SyncInvoicesStatusResponse = StrictObject(
    dict(
        completed=Boolean,
        errors=Array(items=String),
    )
)

definitions = dict(
    SyncInvoicesEntrypointArg=SyncInvoicesEntrypointArg,
    SyncInvoicesUrls=SyncInvoicesUrls,
    SyncInvoicesResponse=SyncInvoicesResponse,
    SyncInvoicesStatusResponse=SyncInvoicesStatusResponse,
)

SyncInvoicesEntrypointValidator = JsonValidator(Type.construct(SyncInvoicesEntrypointArg, definitions=definitions))

SyncInvoicesResponseValidator = JsonValidator(Type.construct(SyncInvoicesResponse, definitions=definitions))

SyncInvoicesStatusResponseValidator = JsonValidator(Type.construct(SyncInvoicesStatusResponse, definitions=definitions))


AllTypes = Object(
    properties=dict(
        p1=Ref("SyncInvoicesEntrypointArg"),
        p2=Ref("SyncInvoicesResponse"),
        p3=Ref("SyncInvoicesStatusResponse"),
    ),
    definitions=definitions,
)

if __name__ == "__main__":
    print(json.dumps(Type.construct(AllTypes), indent=2))


