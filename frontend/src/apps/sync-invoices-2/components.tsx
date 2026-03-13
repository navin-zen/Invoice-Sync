import React from "react";
import { connect } from "react-redux";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { genericRequestAction, incrementAction } from "./actions";
import type { State, SyncStatus } from "./state";
import { SyncErrorsDisplay, SyncStatusDisplay } from "./sub-components";

/**
 * Properties of the App that don't come from the state
 */
interface AppOwnProps {
  message: string;
}

/**
 * Properties of the App
 */
interface AppPropsFromState {
  value: number;
  syncStatus: SyncStatus;
  errors: Array<string>;
}

/**
 * Properties that come with a connection to the dispatch function
 */
interface AppPropsFromDispatch {
  increment: typeof incrementAction;
  genericRequest: typeof genericRequestAction;
}

/**
 * All props
 */
interface AppProps extends AppOwnProps, AppPropsFromState, AppPropsFromDispatch {}

class AppInternal extends React.Component<AppProps, {}> {
  syncButton() {
    if (this.props.syncStatus === "running") {
      return (
        <Button className="ml-auto" disabled={true}>
          Sync Invoices
        </Button>
      );
    } else {
      return (
        <Button className="ml-auto" onClick={() => this.props.genericRequest("sync-invoices")}>
          Sync Invoices
        </Button>
      );
    }
  }
  render() {
    return (
      <Card className="min-h-[50vh]">
        <CardHeader className="flex-row items-center space-y-0">
          <CardTitle>Sync Invoices</CardTitle>
          {this.syncButton()}
        </CardHeader>
        <CardContent>
          <SyncStatusDisplay status={this.props.syncStatus} />
          <SyncErrorsDisplay errors={this.props.errors} />
        </CardContent>
      </Card>
    );
  }
}

/**
 * Function to return props based on the present state
 */
function mapStateToProps(state: State, _: AppOwnProps): AppPropsFromState {
  return {
    value: state.value,
    syncStatus: state.syncStatus,
    errors: state.errors,
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
  genericRequest: genericRequestAction,
};

/**
 * Function to return props.
 *
 * The props values can be used to call the dispatch() function.
 */
export const App = connect(mapStateToProps, mapDispatchToProps)(AppInternal);
