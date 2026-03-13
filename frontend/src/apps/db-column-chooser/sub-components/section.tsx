import React from "react";

import type { ColumnMapping, DbColumns, ExampleData, FieldConfig, MappingSpecSection } from "../definitions";
import { ConfigureField, type SelectionType } from "./configure-fields";

interface MappingSectionDisplayProps {
  section: MappingSpecSection;
  dbColumns: DbColumns;
  transformations: Array<string>;
  exampleData: ExampleData;
  setFieldConfig(fieldName: string, config: FieldConfig): void;
  initialColumnMapping: ColumnMapping;
}

export function MappingSectionDisplay(props: MappingSectionDisplayProps) {
  const [showSection, setShowSection] = React.useState(false);
  const { section, dbColumns, transformations, setFieldConfig, exampleData } = props;
  function initialFieldValues(fieldName: string) {
    const cm = props.initialColumnMapping[fieldName];
    return {
      initialChosenType: cm?.type ?? ("" as SelectionType),
      initialChosenColumn: cm?.type === "column" ? (cm?.column ?? "") : "",
      initialConstantValue: cm?.type === "constant" ? (cm?.value ?? "") : "",
      initialChosenTransformation: cm?.transformation ?? "",
    };
  }
  const fields = section.fields.map((f, idx) => (
    <div key={idx}>
      {idx > 0 ? <hr /> : null}
      <ConfigureField
        fieldName={f.name}
        name={f.displayName}
        // @ts-ignore
        helpText={f.help}
        dbColumns={dbColumns}
        transformations={transformations}
        setFieldConfig={setFieldConfig}
        exampleData={exampleData}
        required={f.required}
        {...initialFieldValues(f.name)}
      />
    </div>
  ));
  const blockClassName = showSection ? "card-block" : "card-block hidden-xs-up";

  return (
    <div className="mb-3 card">
      <div className="card-header" onClick={() => setShowSection(!showSection)}>
        <div className="pull-right">
          <h3>
            <i className={showSection ? "fa fa-chevron-down" : "fa fa-chevron-right"}></i>
          </h3>
        </div>
        <h3>{section.name}</h3>
      </div>
      <div className={blockClassName}>{fields}</div>
    </div>
  );
}
