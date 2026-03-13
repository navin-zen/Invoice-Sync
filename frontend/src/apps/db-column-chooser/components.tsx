import React from "react";
import { connect } from "react-redux";

import { httpPost } from "@/lib/fetch";

import { incrementAction } from "./actions";
import type { ColumnMapping, ExampleData, FieldConfig, MappingSpec, Urls } from "./definitions";
import type { State } from "./state";
import { MappingSectionDisplay } from "./sub-components/section";

/**
 * Properties of the App that don't come from the state
 */
interface AppOwnProps {
  dbColumns: Array<string>;
  mappingSpec: MappingSpec;
  exampleData: ExampleData;
  urls: Urls;
  initialColumnMapping: ColumnMapping; // Existing column mapping if any provided by the user
  table: string;
}

/**
 * Properties of the App
 */
interface AppPropsFromState {
  value: number;
}

/**
 * Properties that come with a connection to the dispatch function
 */
interface AppPropsFromDispatch {
  increment: typeof incrementAction;
}

/**
 * All props
 */
interface AppProps extends AppOwnProps, AppPropsFromState, AppPropsFromDispatch {}

function saveColumnMapping(
  url: string,
  data: { table: string; details: ColumnMapping },
  setSaveInProgress: (b: boolean) => void,
) {
  setSaveInProgress(true);
  httpPost(url, JSON.stringify(data), "application/json")
    .then((_) => {
      setSaveInProgress(false);
    })
    .catch((_) => {
      setSaveInProgress(false);
    });
}

function AppInternal(props: AppProps) {
  const transformations = ["absolute_value", "left_16", "right_16", "month_end", "blank_errors"];
  const columnMapping: ColumnMapping = props.initialColumnMapping;
  const [saveInProgress, setSaveInProgress] = React.useState(false);

  /*
   * Set the configuration of a field.
   */
  function setFieldConfig(fieldName: string, config: FieldConfig) {
    if (!config) {
      console.log("Clearing field", fieldName);
      delete columnMapping[fieldName];
    } else {
      console.log("Setting field", fieldName, config);
      columnMapping[fieldName] = config;
    }
    console.log("setFieldConfig", columnMapping);
  }

  const sectionCards = props.mappingSpec.sections.map((s, idx) => (
    <MappingSectionDisplay
      key={idx}
      section={s}
      dbColumns={props.dbColumns}
      setFieldConfig={setFieldConfig}
      transformations={transformations}
      exampleData={props.exampleData}
      initialColumnMapping={props.initialColumnMapping}
    />
  ));

  return (
    <div>
      <div className="cz-card-border">{sectionCards}</div>
      <div className="text-center">
        <button
          disabled={saveInProgress}
          className="btn btn-primary"
          onClick={() =>
            saveColumnMapping(
              props.urls.setDataMapping,
              { details: columnMapping, table: props.table },
              setSaveInProgress,
            )
          }
        >
          Save Column Mapping Configuration
        </button>
        <a href={props.urls.setColumnMapped} className="ml-3 btn btn-info">
          Go Back
        </a>
      </div>
    </div>
  );
}

/**
 * Function to return props based on the present state
 */
function mapStateToProps(state: State, _: AppOwnProps): AppPropsFromState {
  return {
    value: state.value,
  };
}

/**
 * Can be a function that returns props, or can be an object.
 *
 * If it is an object, redux will automatically wrap the action creators
 * with dispatch.
 */
const mapDispatchToProps: AppPropsFromDispatch = {
  increment: incrementAction,
};

/**
 * Function to return props.
 *
 * The props values can be used to call the dispatch() function.
 */
export const App = connect(mapStateToProps, mapDispatchToProps)(AppInternal);
