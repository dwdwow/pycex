from enum import Enum
from dataclasses import dataclass
from typing import Optional

from cex.cex_name import CexName


class SymbolType(str, Enum):
    SPOT = "SPOT"
    UM_FUTURES = "UM_FUTURES" 
    CM_FUTURES = "CM_FUTURES"


SYMBOL_TYPES = [SymbolType.SPOT, SymbolType.UM_FUTURES, SymbolType.CM_FUTURES]


def is_valid_symbol_type(symbol_type: SymbolType) -> bool:
    return symbol_type in SYMBOL_TYPES


@dataclass
class Symbol:
    # Required fields
    cex: CexName
    type: SymbolType 
    asset: str
    quote: str
    symbol: str
    mid_symbol: str
    q_precision: int
    p_precision: int

    # Optional fields
    taker_fee_tier: Optional[float] = None
    maker_fee_tier: Optional[float] = None
    min_trade_qty: Optional[float] = None
    min_trade_quote: Optional[float] = None
    tradable: Optional[bool] = None
    can_market: Optional[bool] = None
    can_margin: Optional[bool] = None
    is_cross: Optional[bool] = None

    is_perpetual: Optional[bool] = None

    # CM futures specific fields
    contract_size: Optional[float] = None
    contract_type: Optional[str] = None

    # Delivery contract specific fields
    delivery_date: Optional[int] = None
    onboard_date: Optional[int] = None



