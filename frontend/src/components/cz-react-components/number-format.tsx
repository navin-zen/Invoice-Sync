import { NumericFormat, type NumericFormatProps } from "react-number-format";

export function IndianNumberFormat(props: NumericFormatProps) {
  return <NumericFormat thousandsGroupStyle="lakh" fixedDecimalScale={true} thousandSeparator={true} {...props} />;
}

export function IndianNumberFormatDisplay(props: NumericFormatProps) {
  return <IndianNumberFormat displayType="text" {...props} />;
}
