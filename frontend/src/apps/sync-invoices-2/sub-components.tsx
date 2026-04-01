import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";

import type { SyncStatus } from "./state";

interface SyncStatusDisplayProps {
  status: SyncStatus;
  message?: string;
}

export function SyncStatusDisplay(props: SyncStatusDisplayProps) {
  if (props.status === "initial") {
    return (
      <h3 className="tracking-tight leading-none text-center text-muted-foreground">Invoices not being synced.</h3>
    );
  } else if (props.status === "running") {
    return (
      <h3 className="font-semibold tracking-tight leading-none text-center text-primary">
        <i className="mr-2 fa-solid fa-spin fa-spinner"></i>{props.message || "Syncing in progress"}
      </h3>
    );
  } else if (props.status === "complete") {
    return (
      <h3 className="font-semibold tracking-tight leading-none text-center text-brand-green-500">
        <i className="mr-2 fa-circle-check fa-solid"></i>Syncing complete
      </h3>
    );
  } else {
    return null;
  }
}

interface SyncErrorsDisplayProps {
  errors: Array<string>;
}

export function SyncErrorsDisplay(props: SyncErrorsDisplayProps) {
  const rows = (props.errors || []).map((error, idx) => (
    <TableRow key={idx}>
      <TableCell>{error}</TableCell>
    </TableRow>
  ));
  return (
    <Table>
      <TableBody>{rows}</TableBody>
    </Table>
  );
}
