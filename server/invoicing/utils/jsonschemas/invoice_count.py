import json

from cz_utils.json_schema import Array, JsonValidator, Number, Object, Ref, StrictObject, String, Type

InvoiceCountDetails = StrictObject(
    properties=dict(
        cancelled=Number(min=0),
        end_date=String,
        start_date=String,
        generated=Number(min=0),
        label=String(minLength=1),
        pending=Number(min=0),
        total=Number(min=0),
        type=String(minLength=1),
    )
)

InvoiceCountDetailsList = Array(items=Ref("InvoiceCountDetails"))

definitions = dict(InvoiceCountDetails=InvoiceCountDetails, InvoiceCountDetailsList=InvoiceCountDetailsList)

InvoiceCountDetailsListValidator = JsonValidator(Type.construct(InvoiceCountDetailsList, definitions=definitions))

AllTypes = Object(
    properties=dict(
        p1=Ref("InvoiceCountDetailsList"),
    ),
    definitions=definitions,
)

if __name__ == "__main__":
    print(json.dumps(Type.construct(AllTypes), indent=2))


