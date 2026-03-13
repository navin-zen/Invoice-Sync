import datetime

"""
Enums for Tax Return Types.

This is common between taxpayer.models.TaxReturn and xxx models
"""

RETURN_TYPE_ENUMS = (
    GSTR1,
    GSTR2,
    GSTR3,
    GSTR1A,
    GSTR2A,
    GSTR3B,
    GSTR4,
    GSTR6,
    GSTR9,
    GSTR10,
    ITC01,
    ITC02,
    ITC03,
    ITC04,
    TRAN1,
    TRAN2,
    TRAN3,
    GSTR9A,
    GSTR6A,
    GSTR9C,
    GSTR4A,
    RET1,
    RET2,
    RET3,
    ANX1,
    ANX2,
    RET1A,
    RET2A,
    RET3A,
    ANX1A,
    PMT08,
) = range(8000, (8000 + 31))

[MONTHLY, QUARTERLY, ANNUAL] = range(8200, 8200 + 3)


RETURN_TYPE_INFO = [
    (
        GSTR1,
        "GSTR-1 Monthly Outward Supply",
        "GSTR-1",
        MONTHLY,
    ),
    (
        GSTR2,
        "GSTR-2 Monthly Inward Supply",
        "GSTR-2",
        MONTHLY,
    ),
    (
        GSTR3,
        "GSTR-3 Monthly GST Return",
        "GSTR-3",
        MONTHLY,
    ),
    (
        GSTR1A,
        "GSTR-1A Monthly Outward Supply (Auto)",
        "GSTR-1A",
        MONTHLY,
    ),
    (
        GSTR2A,
        "GSTR-2A Monthly Inward Supply (Auto)",
        "GSTR-2A",
        MONTHLY,
    ),
    (
        GSTR3B,
        "GSTR-3B Consolidated Monthly GST Return",
        "GSTR-3B",
        MONTHLY,
    ),
    (
        GSTR4,
        "GSTR-4 - Quarterly Return for Registered Person opting for Composition Levy",
        "GSTR-4",
        QUARTERLY,
    ),
    (
        GSTR6,
        "GSTR-6 - Return for Input Service Distributor",
        "GSTR-6",
        ANNUAL,
    ),
    (
        GSTR6A,
        "GSTR-6A - 6A Return for Input Service Distributor",
        "GSTR-6A",
        QUARTERLY,
    ),
    (
        GSTR9,
        "GSTR-9 - Annual Return",
        "GSTR-9",
        ANNUAL,
    ),
    (
        GSTR10,
        "GSTR-10 - Final Return",
        "GSTR-10",
        MONTHLY,
    ),
    (
        ITC01,
        "ITC-01 - Declaration for claim of input tax credit under sub-section (1) of section 18",
        "ITC-01",
        MONTHLY,
    ),
    (
        ITC02,
        (
            "ITC-02 - Declaration for transfer of ITC in case of sale, merger, demerger, amalgamation, lease "
            "or transfer of a business under sub-section (3) of section 18"
        ),
        "ITC-02",
        MONTHLY,
    ),
    (
        ITC03,
        (
            "ITC-03 - Declaration for intimation of ITC reversal/payment of tax on inputs held in "
            "stock, inputs contained in semi-finished and finished goods held in stock and "
            "capital goods under sub-section (4) of section 18"
        ),
        "ITC-03",
        MONTHLY,
    ),
    (
        ITC04,
        "ITC-04 - Details of goods/capital goods sent to job worker and received back",
        "ITC-04",
        MONTHLY,
    ),
    (
        TRAN1,
        "TRAN-1 Transition Return 1",
        "TRAN-1",
        MONTHLY,
    ),
    (
        TRAN2,
        "TRAN-2 Transition Return 2",
        "TRAN-2",
        MONTHLY,
    ),
    (
        TRAN3,
        "TRAN-3 Transition Return 3",
        "TRAN-3",
        MONTHLY,
    ),
    (
        GSTR9A,
        "GSTR-9A Annual Return (For Composition Taxpayer)",
        "GSTR-9A",
        ANNUAL,
    ),
    (
        GSTR9C,
        "GSTR-9C Annual Return Audit",
        "GSTR-9C",
        ANNUAL,
    ),
    (
        GSTR4A,
        "GSTR-4A - Quarterly Return for Registered Person opting for Composition Levy",
        "GSTR-4A",
        QUARTERLY,
    ),
    (
        RET1,
        "RET-1 Normal GST Return",
        "RET-1",
        MONTHLY,
    ),
    (
        RET2,
        "RET-2 Sahaj GST Return",
        "RET-2",
        QUARTERLY,
    ),
    (
        RET3,
        "RET-3 Sugam GST Return",
        "RET-3",
        QUARTERLY,
    ),
    (
        ANX1,
        "ANX-1 Annexure of Outward Supplies",
        "ANX-1",
        MONTHLY,
    ),
    (
        ANX2,
        "ANX-2 Annexure of Inward Supplies",
        "ANX-2",
        MONTHLY,
    ),
    (
        RET1A,
        "RET-1A Normal GST Return (Amendment)",
        "RET-1A",
        MONTHLY,
    ),
    (
        RET2A,
        "RET-2A Sahaj GST Return (Amendment)",
        "RET-2A",
        QUARTERLY,
    ),
    (
        RET3A,
        "RET-3A Sugam GST Return (Amendment)",
        "RET-3A",
        QUARTERLY,
    ),
]

RETURN_TYPES = [(enum, long_name) for (enum, long_name, _, _) in RETURN_TYPE_INFO]
SHORT_NAME_MAP = {enum: short_name for (enum, _, short_name, _) in RETURN_TYPE_INFO}
RETURN_FREQUENCY_MAP = {enum: freq for (enum, _, _, freq) in RETURN_TYPE_INFO}


def return_period_display(return_type, return_period):
    """
    Properly formatted return period
    """
    freq = RETURN_FREQUENCY_MAP.get(return_type, MONTHLY)
    if freq == MONTHLY:
        format = "%b %Y"
    elif freq == QUARTERLY:
        format = "%b %Y"
    elif freq == ANNUAL:
        format = "%Y"
    else:
        format = ""
    return datetime.date.strftime(return_period, format)


