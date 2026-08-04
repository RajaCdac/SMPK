"""Indian numbering amount-to-words (Oracle PEN_FIRST_BILL_REPORT_LIC style)."""

_ONES = (
    "",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
    "THIRTEEN",
    "FOURTEEN",
    "FIFTEEN",
    "SIXTEEN",
    "SEVENTEEN",
    "EIGHTEEN",
    "NINETEEN",
)
_TENS = (
    "",
    "",
    "TWENTY",
    "THIRTY",
    "FORTY",
    "FIFTY",
    "SIXTY",
    "SEVENTY",
    "EIGHTY",
    "NINETY",
)


def _under_thousand(n):
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} HUNDRED")
        n %= 100
    if n >= 20:
        tens = _TENS[n // 10]
        ones = _ONES[n % 10]
        parts.append(f"{tens}{ones}".strip())
    elif n > 0:
        parts.append(_ONES[n])
    return " ".join(p for p in parts if p).strip()


def _indian_words(n):
    n = int(n)
    if n == 0:
        return "ZERO"
    parts = []
    crore = n // 10_000_000
    n %= 10_000_000
    lakh = n // 100_000
    n %= 100_000
    thousand = n // 1_000
    n %= 1_000

    if crore:
        parts.append(f"{_indian_words(crore)} CRORE")
    if lakh:
        parts.append(f"{_under_thousand(lakh)} LAKH".strip())
    if thousand:
        parts.append(f"{_under_thousand(thousand)} THOUSAND".strip())
    if n:
        parts.append(_under_thousand(n))
    return " ".join(p for p in parts if p).strip()


def rupees_amount_in_words(amount):
    """Return 'RUPEES ... ONLY' in Oracle report style."""
    from decimal import Decimal, ROUND_HALF_UP

    value = Decimal(str(amount or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = ""
    if value < 0:
        sign = "MINUS "
        value = abs(value)
    words = _indian_words(int(value))
    return f"{sign}RUPEES {words} ONLY".strip()
