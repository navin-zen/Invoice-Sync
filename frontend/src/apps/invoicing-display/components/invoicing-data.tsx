import { IndianNumberFormatDisplay } from "@/components/cz-react-components/number-format";
import { num2text } from "@/lib/num2text";

import { type Address, INVOICING_DATA_SAMPLE, type INVOICING_DATA_TYPE, type ItemListType, type ItemType } from "./invoicing-data-definitions";

interface InvoicingProps {
  data: INVOICING_DATA_TYPE;
}

interface InvoicingLineItemsProps {
  itemList: ItemListType;
  data: INVOICING_DATA_TYPE;
}

interface LineItemProps {
  lineitem: ItemType;
}

function LineItem(props: LineItemProps) {
  const gstRate = props.lineitem?.GstRt;
  const igstAmount = props.lineitem?.IgstAmt;
  const Barcde = props.lineitem?.Barcde ? <span className="h6"> Bar code:{props.lineitem?.Barcde}</span> : null;
  return (
    <tbody>
      <tr>
        <td rowSpan={2}></td>
        <td className="px-2" colSpan={3}>
          {props.lineitem?.PrdDesc}
          <br />
          {Barcde}
        </td>
        <td className="text-center" rowSpan={2}>
          <IndianNumberFormatDisplay decimalScale={2} value={gstRate} />
        </td>
        <td className="pr-2 text-right" rowSpan={2}>
          <IndianNumberFormatDisplay decimalScale={2} value={props.lineitem?.AssAmt} />
        </td>
        <td className="pr-2 text-right" rowSpan={2}>
          {igstAmount}
        </td>
      </tr>
      <tr>
        <td className="text-center">{props.lineitem?.HsnCd}</td>
        <td className="text-center">
          {props.lineitem?.Qty} {props.lineitem?.Unit}
        </td>
        <td className="text-center">{props.lineitem?.UnitPrice}</td>
      </tr>
    </tbody>
  );
}

function InvoicingLineItems(props: InvoicingLineItemsProps) {
  const rows = props.itemList.map((i, idx) => <LineItem key={idx} lineitem={i} />);
  return (
    <table className="table table-sm table-bordered">
      <thead className="thead-inverse">
        <tr>
          <th className="text-center align-middle" rowSpan={2}>
            #
          </th>
          <th className="text-center" colSpan={3}>
            Description
          </th>
          <th className="text-center align-middle" rowSpan={2}>
            GST <br /> Rate
          </th>
          <th className="text-center align-middle" rowSpan={2}>
            Taxable <br /> Value
          </th>
          <th className="text-center align-middle" rowSpan={2}>
            IGST
          </th>
        </tr>
        <tr>
          <th className="text-center">HSN</th>
          <th className="text-center">Quantity</th>
          <th className="text-center">Unit Rate</th>
        </tr>
      </thead>
      {rows}
      <tr>
        <td className="text-right" colSpan={5}>
          Total Amounts (INR)
        </td>
        <td className="pr-2 text-right font-weight-bold">
          <IndianNumberFormatDisplay decimalScale={2} value={props.data.ValDtls?.AssVal} />
        </td>
        <td className="pr-2 text-right font-weight-bold">
          <IndianNumberFormatDisplay decimalScale={2} value={props.data.ValDtls?.IgstVal} />
        </td>
      </tr>
      <tr>
        <td className="text-right" colSpan={7}>
          Invoice Total (in figures):
          <span className="pl-2 font-weight-bold">
            <IndianNumberFormatDisplay decimalScale={2} value={props.data.ValDtls?.TotInvVal} />
          </span>
        </td>
      </tr>
      <tr>
        <td className="text-right" colSpan={7}>
          Invoice Total amount in words:
          <span className="pl-2 font-weight-bold">{num2text(props.data.ValDtls?.TotInvVal)}</span>
        </td>
      </tr>
    </table>
  );
}

interface AddressProps {
  address: Address;
}

export function MyAddress(props: AddressProps) {
  const TrdNm = props.address?.TrdNm ? (
    <span className="font-weight-bold">
      {props.address?.TrdNm}
      <br />
    </span>
  ) : null;
  const Bno = props.address?.Bno ? <span>{props.address?.Bno}, </span> : null;
  const Bnm = props.address?.Bnm ? <span>{props.address?.Bnm} ,</span> : null;
  const Flno = props.address?.Flno ? <span>{props.address?.Flno} ,</span> : null;
  const Loc = props.address?.Loc ? <span>{props.address?.Loc}</span> : null;
  const Stcd = props.address?.Stcd ? (
    <span className="text-muted">
      State Code: {props.address?.Stcd} - {props.address.Stcd}
    </span>
  ) : null;
  const Pin = props.address?.Pin ? (
    <span className="text-muted">
      State: {props.address?.Stcd} - {props.address.Pin}
      <br />
    </span>
  ) : null;
  const Gstin = props.address?.Gstin ? (
    <div>
      <span className="text-muted">Gstin: </span>
      <span className="font-weight-bold">
        {props.address?.Gstin}
        <br />
      </span>
    </div>
  ) : null;
  const phone = props.address?.Ph ? (
    <span>
      Phone: {props.address?.Ph}
      <br />
    </span>
  ) : null;
  const email = props.address?.Em ? (
    <span>
      Email: {props.address?.Em}
      <br />
    </span>
  ) : null;
  const district = props.address?.Dst ? (
    <span>
      District{props.address?.Dst}
      <br />
    </span>
  ) : null;
  return (
    <div>
      <span>{Gstin}</span>
      {TrdNm}
      {Bno}
      {Bnm}
      {Flno}
      {Loc}
      {phone}
      {email}
      {district}
      <span>{Pin}</span>
      <span>{Stcd}</span>
    </div>
  );
}

export function Invoicing(props: InvoicingProps) {
  const No = props.data.DocDtls?.No ? (
    <div>
      <span className="text-muted">Invoice Number: </span>
      <span className="font-weight-bold">{props.data.DocDtls?.No}</span>
    </div>
  ) : null;
  const Dt = props.data.DocDtls?.Dt ? (
    <div>
      <span className="text-muted">Invoice Date: </span>
      <span className="font-weight-bold">{props.data.DocDtls?.Dt}</span>
    </div>
  ) : null;
  const Pos = props.data.BuyerDtls?.Stcd ? (
    <div>
      <span className="text-muted">Place of Supply: </span>
      <span className="font-weight-bold">{props.data.BuyerDtls?.Stcd}</span>
    </div>
  ) : null;
  const RegRev = props.data.TranDtls?.RegRev == "RC";
  const revchrg = RegRev ? (
    <div>
      <span className="text-muted">Reverse Charge: </span>
      <span className="font-weight-bold">Yes</span>
    </div>
  ) : (
    <div>
      <span className="text-muted">Reverse Charge: </span>
      <span className="font-weight-bold"> No</span>
    </div>
  );
  return (
    <div className="container">
      <h5 className="pb-3 text-center">
        <span className="text-muted">Doc Identifier</span> {props.data.Irn}
      </h5>
      <div className="my-3 mx-2 row">
        <div className="col-3">
          <h6 className="text-muted">Supplier Information</h6>
          <MyAddress address={props.data.SellerDtls} />
        </div>
        <div className="col-3">
          <h6 className="text-muted">Recipient Information</h6>
          <MyAddress address={props.data.BuyerDtls} />
        </div>
        <div className="col-3">
          <h6 className="text-muted">Ship to adress</h6>
          <MyAddress address={props.data.ShipDtls} />
        </div>
        <div className="col-3">
          <h6 className="text-muted">Details of Invoice</h6>
          <span>{No}</span>
          <span>{Dt}</span>
          <span>{Pos}</span>
          <span>{revchrg}</span>
        </div>
      </div>
      <InvoicingLineItems itemList={props.data.ItemList} data={INVOICING_DATA_SAMPLE} />
    </div>
  );
}
