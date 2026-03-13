/* Converts the amount from number into words */

export function num2text(value: number): string {
  const fraction = Math.round(frac(value) * 100);
  let f_text = "";

  if (fraction > 0) {
    f_text = "And " + convert_number(fraction) + " Paise";
  }

  return "Rupees " + convert_number(value) + f_text + " Only";
}

function frac(f: number) {
  return f % 1;
}

function convert_number(n: number) {
  if (n < 0 || n > 999999999) {
    return "NUMBER OUT OF RANGE!";
  }
  const Gn = Math.floor(n / 10000000); /* Crore */
  n -= Gn * 10000000;
  const kn = Math.floor(n / 100000); /* lakhs */
  n -= kn * 100000;
  const Hn = Math.floor(n / 1000); /* thousand */
  n -= Hn * 1000;
  const Dn = Math.floor(n / 100); /* Tens (deca) */
  n = n % 100; /* Ones */
  const tn = Math.floor(n / 10);
  const one = Math.floor(n % 10);
  let res = "";

  if (Gn > 0) {
    res += convert_number(Gn) + " Crore";
  }
  if (kn > 0) {
    res += (res == "" ? "" : " ") + convert_number(kn) + " Lakh";
  }
  if (Hn > 0) {
    res += (res == "" ? "" : " ") + convert_number(Hn) + " Thousand";
  }

  if (Dn) {
    res += (res == "" ? "" : " ") + convert_number(Dn) + " Hundred";
  }

  const ones = [
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
  ];
  const tens = ["", "", "Twenty", "Thirty", "Fourty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

  if (tn > 0 || one > 0) {
    if (!(res == "")) {
      res += " And ";
    }
    if (tn < 2) {
      res += ones[tn * 10 + one];
    } else {
      res += tens[tn];
      if (one > 0) {
        res += "-" + ones[one];
      }
    }
  }

  if (res == "") {
    res = "zero";
  }
  return res;
}
