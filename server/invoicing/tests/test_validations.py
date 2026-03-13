import datetime
import decimal

from django.test.testcases import TestCase as DjangoTestCase
from invoicing.utils.api.common import typecast_and_get_state
from invoicing.utils.utils import parse_tax_rate
from invoicing.utils.validate_fields import (
    qty_to_decimal_round2,
    validate_date,
    validate_invoicing_gstin,
    validate_emailid,
    validate_hsncode,
    validate_invnumber,
    validate_invtype,
    validate_pincode,
    validate_revchrg_and_isexp,
    validate_str,
    validate_unit,
)
from pygstn.validation_error import ValidationError

from seed_data import populate_states
from taxmaster.models import State


class TestCase(DjangoTestCase):
    @classmethod
    def setUpTestData(self):
        populate_states.run()

    def test_validate_revchrg_and_isexp(self):
        true_data = [
            "Y",
            "Yes",
            "YES",
            "y",
            "yes",
            '"YES"',
            "   Y   ",
        ]
        false_data = [
            None,
            "",
            "   ",
            "N",
            "No",
            "NO",
            "n",
            "no",
            '"NO"',
            "   N   ",
        ]
        error_data = [
            23,
            23.33,
            "None",
        ]
        for t in true_data:
            self.assertEqual(validate_revchrg_and_isexp(t), "Y")
        for f in false_data:
            self.assertEqual(validate_revchrg_and_isexp(f), "N")
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_revchrg_and_isexp(e)
        self.assertEqual(validate_revchrg_and_isexp(None, default=23), 23)
        with self.assertRaises(ValueError):  # 0 will be converted to a string
            validate_revchrg_and_isexp(0, default=23)
        self.assertEqual(validate_revchrg_and_isexp("", default=23), 23)
        self.assertEqual(validate_revchrg_and_isexp(" ", default=24), 24)

    def test_parse_state(self):
        karnataka = State.objects2.get(alphaCode="KA")
        self.assertEqual(typecast_and_get_state(29), karnataka)
        self.assertEqual(typecast_and_get_state(29.0), karnataka)
        self.assertEqual(typecast_and_get_state(" 29 "), karnataka)
        self.assertEqual(typecast_and_get_state("29"), karnataka)
        self.assertEqual(typecast_and_get_state("karnataka"), karnataka)
        self.assertEqual(typecast_and_get_state(" Karnataka "), karnataka)
        delhi = State.objects2.get(alphaCode="DL")
        self.assertEqual(typecast_and_get_state("07"), delhi)
        self.assertEqual(typecast_and_get_state(7), delhi)
        self.assertEqual(typecast_and_get_state("7"), delhi)
        with self.assertRaises(ValueError):
            typecast_and_get_state(88)
        with self.assertRaises(ValueError):
            typecast_and_get_state("karna")

    def test_get_uqc(self):
        self.assertEqual(validate_unit(123), "OTH")
        self.assertEqual(validate_unit(None), "OTH")
        self.assertEqual(validate_unit(""), "OTH")
        self.assertEqual(validate_unit("NOS"), "NOS")
        self.assertEqual(validate_unit("nos"), "NOS")
        self.assertEqual(validate_unit(" nos "), "NOS")
        self.assertEqual(validate_unit("NOS-NUMBER"), "NOS")

    def test_hsn(self):
        error_data = [23, 23.33, "None", None, "123", 12345, "Pathak"]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_hsncode(e)
        self.assertEqual(validate_hsncode("1234"), "1234")
        self.assertEqual(validate_hsncode(1234), "1234")
        self.assertEqual(validate_hsncode("123456"), "123456")
        self.assertEqual(validate_hsncode("12345678"), "12345678")

    def test_invtype(self):
        error_data = [
            23,
            "None",
        ]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_invtype(e)
        self.assertEqual(validate_invtype(""), "INV")
        self.assertEqual(validate_invtype(None), "INV")
        self.assertEqual(validate_invtype("inv"), "INV")
        self.assertEqual(validate_invtype("crn"), "CRN")
        self.assertEqual(validate_invtype(" INV "), "INV")
        self.assertEqual(validate_invtype(" credit note "), "CRN")

    def test_pincode(self):
        error_data = [
            123,
            "abcd",
        ]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_pincode(e)
        self.assertEqual(validate_pincode(560077), "560077")
        self.assertEqual(validate_pincode(999999), "999999")
        self.assertEqual(validate_pincode("560077"), "560077")
        self.assertEqual(validate_pincode("999999"), "999999")

    def test_invnumber(self):
        error_data = [
            None,
            "",
            " ",
            "$abc",
            "12345678910111223234",
        ]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_invnumber(e)
        self.assertEqual(validate_invnumber("17-03-2020/ABC"), "17-03-2020/ABC")
        self.assertEqual(validate_invnumber(" 17-03-2020/ABC "), "17-03-2020/ABC")
        self.assertEqual(validate_invnumber("17-03-2020/ABC\t"), "17-03-2020/ABC")

    def test_qty(self):
        self.assertEqual(qty_to_decimal_round2(""), 1)
        self.assertEqual(qty_to_decimal_round2("  "), 1)
        self.assertEqual(qty_to_decimal_round2(None), 1)
        self.assertEqual(qty_to_decimal_round2("123"), 1)
        self.assertEqual(qty_to_decimal_round2(23), 23)
        self.assertEqual(qty_to_decimal_round2("abc"), 1)

    def test_gstin(self):
        value_error_data = [
            None,
            "",
        ]
        error_data = [
            " ",
            "$abc",
            123,
            "12345678910111223234",
            "33CEIPN3322D1Z",
            "29CEIPN3322D1ZY",
        ]
        for e in value_error_data:
            with self.assertRaises(ValueError):
                validate_invoicing_gstin(e)
        for e in error_data:
            with self.assertRaises(ValidationError):
                validate_invoicing_gstin(e)
        self.assertEqual(validate_invoicing_gstin("33CEIPN3322D1ZY"), "33CEIPN3322D1ZY")

    def test_date(self):
        error_data = ["$abc", 12 / 14 / 2020, 123, "", None, " "]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_date(e)
        self.assertEqual(validate_date("12/10/2019"), datetime.date(2019, 10, 12))
        self.assertEqual(validate_date("12-10-2019"), datetime.date(2019, 10, 12))

    def test_taxrate(self):
        error_data = [
            "$abc",
            13,
            "12345678910111223234",
        ]
        for e in error_data:
            with self.assertRaises(ValueError):
                parse_tax_rate(e)
        self.assertEqual(parse_tax_rate(None), 0)
        self.assertEqual(parse_tax_rate(""), 0)
        self.assertEqual(parse_tax_rate(0.1), round(decimal.Decimal(0.1), 1))
        self.assertEqual(parse_tax_rate("0.1%"), round(decimal.Decimal(0.1), 1))
        self.assertEqual(parse_tax_rate(" 0.1% "), round(decimal.Decimal(0.1), 1))

    def test_emailid(self):
        error_data = [
            "$abc",
            "abc@",
        ]
        for e in error_data:
            with self.assertRaises(ValueError):
                validate_emailid(e)
        self.assertEqual(validate_emailid(13), None)
        self.assertEqual(validate_emailid(None), None)
        self.assertEqual(validate_emailid(""), None)
        self.assertEqual(validate_emailid("abc@gmail.com"), "abc@gmail.com")

    def test_validate_str(self):
        self.assertEqual(validate_str(None), None)
        self.assertEqual(validate_str(""), "")
        self.assertEqual(validate_str("None"), "None")
        self.assertEqual(validate_str(23), "23")


