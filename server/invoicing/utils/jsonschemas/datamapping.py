"""
JSON schemas related to datamapping
"""

from pygstn.utils import json

from cz_utils.json_schema import (
    AnyOf,
    Array,
    Boolean,
    JsonValidator,
    Object,
    Optional,
    Ref,
    StrictObject,
    String,
    Tuple,
    Type,
)

###################################################################################
# Specification of Invoicing to display to the user for providing column
# mapping
MappingSpecField = StrictObject(dict(name=String, displayName=String, help=Optional(String), required=Boolean))
MappingSpecSection = StrictObject(dict(name=String, description=String, fields=Array(items=Ref("MappingSpecField"))))
MappingSpec = StrictObject(
    dict(
        sections=Array(items=Ref("MappingSpecSection")),
        all_or_none=Array(items=Array(String)),
        exclusive_or=Array(items=Tuple(String, String)),
    )
)

ExampleData = Object()

###################################################################################
# Column mapping chosen by the user
DbColumnConfig = StrictObject(
    dict(
        type=String(enum=["column"]),
        column=String,
        transformation=Optional(String),
    )
)

ConstantConfig = StrictObject(
    dict(
        type=String(enum=["constant"]),
        value=String,
        transformation=Optional(String),
    )
)

FieldConfig = AnyOf([Ref("DbColumnConfig"), Ref("ConstantConfig")])

ColumnMapping = Object(additionalProperties=Ref("FieldConfig"))
###################################################################################

Urls = StrictObject(
    dict(
        setDataMapping=String,
        setColumnMapped=String,
    )
)

DbColumns = Array(items=Optional(String))

Table = String

DbChooseColumnsEntrypointArg = StrictObject(
    dict(
        id=String,
        dbColumns=Ref("DbColumns"),
        invoicingSpec=Ref("MappingSpec"),
        exampleData=Ref("ExampleData"),
        initialColumnMapping=Ref("ColumnMapping"),
        urls=Ref("Urls"),
        table=String,
    )
)


definitions = dict(
    DbColumns=DbColumns,
    DbChooseColumnsEntrypointArg=DbChooseColumnsEntrypointArg,
    MappingSpecField=MappingSpecField,
    MappingSpecSection=MappingSpecSection,
    MappingSpec=MappingSpec,
    ExampleData=ExampleData,
    DbColumnConfig=DbColumnConfig,
    ConstantConfig=ConstantConfig,
    FieldConfig=FieldConfig,
    ColumnMapping=ColumnMapping,
    Urls=Urls,
    Table=Table,
)

###################################################################################
# Validators
DbChooseColumnsEntrypointArgValidator = JsonValidator(
    Type.construct(DbChooseColumnsEntrypointArg, definitions=definitions)
)

MappingSpecValidator = JsonValidator(Type.construct(MappingSpec, definitions=definitions))

ColumnMappingValidator = JsonValidator(Type.construct(ColumnMapping, definitions=definitions))
###################################################################################


AllTypes = Object(
    properties=dict(p1=Ref("DbChooseColumnsEntrypointArg"), p2=Ref("MappingSpec"), p3=Ref("ColumnMapping")),
    definitions=definitions,
)

if __name__ == "__main__":
    print(json.dumps(Type.construct(AllTypes), indent=2))


