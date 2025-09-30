from enum import Enum


class CexName(str, Enum):
    BINANCE = "BINANCE"


CEX_NAMES = [CexName.BINANCE]


def not_cex_name(name: CexName) -> bool:
    return name not in CEX_NAMES
