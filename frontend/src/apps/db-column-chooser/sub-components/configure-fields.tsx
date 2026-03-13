import React from "react";

import type { ExampleData, FieldConfig } from "../definitions";

export type SelectionType = "column" | "constant" | "";

interface ConfigureFieldProps {
  fieldName: string;
  name: string;
  helpText: string;
  required: boolean;
  dbColumns: Array<string>;
  transformations: Array<string>;
  exampleData: ExampleData;
  setFieldConfig(fieldName: string, config: FieldConfig): void;
  initialChosenType: SelectionType;
  initialChosenColumn: string;
  initialConstantValue: string;
  initialChosenTransformation: string;
}

export function ConfigureField(props: ConfigureFieldProps) {
  const [chosenType, setChosenType] = React.useState(props.initialChosenType);
  const [chosenColumn, setChosenColumn] = React.useState(props.initialChosenColumn);
  const [constantValue, setConstantValue] = React.useState(props.initialConstantValue);
  const [chosenTransformation, setChosenTransformation] = React.useState(props.initialChosenTransformation);

  function callSetFieldConfig() {
    if (chosenType === "column") {
      if (chosenColumn) {
        return props.setFieldConfig(props.fieldName, {
          type: chosenType,
          column: chosenColumn,
          transformation: chosenTransformation,
        });
      }
    } else if (chosenType === "constant") {
      return props.setFieldConfig(props.fieldName, {
        type: chosenType,
        value: constantValue,
        transformation: chosenTransformation,
      });
    }
    // @ts-ignore
    return props.setFieldConfig(props.fieldName, null);
  }

  React.useEffect(() => {
    callSetFieldConfig();
  }, [chosenType, chosenColumn, chosenTransformation, constantValue]);

  function getInputDisplay(st: SelectionType) {
    if (st === "column") {
      const options = props.dbColumns.map((i, idx) => (
        <option key={idx} value={i}>
          {i}
        </option>
      ));
      return (
        <div>
          <select
            id="columns"
            className="form-control"
            style={{ width: "100%" }}
            value={chosenColumn}
            onChange={(event) => setChosenColumn(event.target.value)}
          >
            <option value="">Choose a Column</option>
            {options}
          </select>
          <small className="text-muted">Name of the column in your database.</small>
        </div>
      );
    } else if (st === "constant") {
      return (
        <div>
          <input
            type="text"
            value={constantValue}
            className="textinput textInput form-control"
            onChange={(event) => setConstantValue(event.target.value)}
          />
          <small className="text-muted">Value of the column.</small>
        </div>
      );
    } else {
      return null;
    }
  }

  function getTransformations(st: SelectionType) {
    if (st != "") {
      const transformations = props.transformations.map((i, idx) => (
        <option key={idx} value={i}>
          {i}
        </option>
      ));
      return (
        <div>
          <select
            id="transformations"
            className="select2-widget form-control"
            style={{ width: "100%" }}
            value={chosenTransformation}
            onChange={(event) => setChosenTransformation(event.target.value)}
          >
            <option value="">Choose Transformation</option>
            {transformations}
          </select>
          <small className="text-muted">The transformation that you want to apply for {props.name}.</small>
        </div>
      );
    }
  }

  function exampleValue() {
    if (chosenType === "column") {
      if (chosenColumn) {
        return props.exampleData[chosenColumn] ?? null;
      }
    } else if (chosenType === "constant") {
      return constantValue;
    }
  }

  const inputDisplay = getInputDisplay(chosenType);
  const transformations = getTransformations(chosenType);
  const helpTextDisplay = props.helpText ? <div className="mb-3 text-muted">{props.helpText}</div> : null;
  return (
    <div>
      <h5>
        <span className={props.required ? "cz-bold" : ""}>{props.name}</span>
        {props.required ? (
          <span className="ml-1" style={{ color: "red" }}>
            *
          </span>
        ) : null}
      </h5>
      {helpTextDisplay}
      <div className="row">
        <div className="col-sm-3 md-form">
          <select
            className="select2-widget form-control"
            style={{ width: "100%" }}
            id="columns"
            value={chosenType}
            onChange={(event) => setChosenType(event.target.value as SelectionType)}
          >
            <option value="">Choose value source</option>
            <option value="column">From Database</option>
            <option value="constant">Use Constant Value</option>
          </select>
        </div>
        <div className="col-sm-3">{inputDisplay}</div>
        <div className="col-sm-3">{transformations}</div>
        <div className="col-sm-3">
          <strong>{exampleValue()}</strong>
        </div>
      </div>
    </div>
  );
}
