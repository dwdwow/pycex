from typing import TypedDict

from endpoints import API_ENDPOINT, API_V3
from rest import request, Request, Response
from enums import SymbolStatus, AcctSybPermission, OrderType, RateLimitType, RateLimiterInterval


import os
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from symbol import Symbol, SymbolType
from cex_name import CexName


# Data structures
ServerTime = TypedDict("ServerTime", {"serverTime": int})


SpotExchangeSymbol = TypedDict("SpotExchangeSymbol", {
    "symbol": str,
    "status": SymbolStatus,
    "baseAsset": str,
    "baseAssetPrecision": int,
    "quoteAsset": str,
    "quotePrecision": int,
    "quoteAssetPrecision": int,
    "baseCommissionPrecision": int,
    "quoteCommissionPrecision": int,
    "orderTypes": list[OrderType],
    "icebergAllowed": bool,
    "ocoAllowed": bool,
    "otoAllowed": bool,
    "quoteOrderQtyMarketAllowed": bool,
    "allowTrailingStop": bool,
    "cancelReplaceAllowed": bool,
    "amendAllowed": bool,
    "isSpotTradingAllowed": bool,
    "isMarginTradingAllowed": bool,
    "filters": list[dict[str, any]],
    "permissions": list[AcctSybPermission],
    "permissionSets": list[list[AcctSybPermission]],
    "defaultSelfTradePreventionMode": str,
    "allowedSelfTradePreventionModes": list[str]
})


def to_cex_symbol(exchange_symbol: SpotExchangeSymbol) -> Symbol:
    filters_info = analyze_exchange_symbol_filters(exchange_symbol.filters)
    return Symbol(
        cex=CexName.BINANCE,
        type=SymbolType.SPOT,
        asset=exchange_symbol.base_asset,
        quote=exchange_symbol.quote_asset,
        symbol=exchange_symbol.symbol,
        q_precision=filters_info.q_prec,
        p_precision=filters_info.p_prec,
        tradable=exchange_symbol.status == SymbolStatus.TRADING,
        can_market=OrderType.MARKET in exchange_symbol.order_types,
        can_margin=exchange_symbol.is_margin_trading_allowed
    )


RateLimiter = TypedDict("RateLimiter", {
    "rateLimitType": RateLimitType,
    "interval": RateLimiterInterval,
    "intervalNum": int,
    "limit": int
})


Sor = TypedDict("Sor", {
    "baseAsset": str,
    "symbols": list[str]
})


SpotExchangeInfo = TypedDict("SpotExchangeInfo", {
    "timezone": str,
    "serverTime": int,
    "rateLimits": list[RateLimiter],
    "exchangeFilters": list[any],
    "symbols": list[SpotExchangeSymbol],
    "sors": list[Sor]
})



ExchangeSymbolFiltersInfo = TypedDict("ExchangeSymbolFiltersInfo", {
    "pPrec": int,
    "qPrec": int,
    "canMarket": bool
})


# Helper functions
def get_prec_just_for_binance_filter(size: str) -> int:
    """Extract precision from Binance filter size string.
    
    Args:
        size: Size string like "0.01" or "1000"
        
    Returns:
        Precision value
        
    Raises:
        ValueError: If size format is unknown
    """
    parts = size.split(".")
    integer_part = parts[0]
    
    # Look for '1' in integer part
    one_index = integer_part.find("1")
    if one_index != -1:
        return one_index - len(integer_part) + 1
    
    # If no decimal part, error
    if len(parts) == 1:
        raise Exception(f"unknown size: {size}")
    
    # Look for '1' in decimal part
    decimal_part = parts[1]
    one_index = decimal_part.find("1")
    if one_index != -1:
        return one_index + 1
    
    raise Exception(f"unknown size: {size}")


def analyze_exchange_symbol_filters(filters: list[dict[str, any]]) -> ExchangeSymbolFiltersInfo:
    """Analyze exchange symbol filters to extract precision and trading capabilities.
    
    Args:
        filters: List of filter dictionaries from exchange info
        
    Returns:
        ExchangeSymbolFiltersInfo with parsed data
        
    Raises:
        ValueError: If filter format is unexpected
    """
    p_prec = 0
    q_prec = 0
    can_market = False
    
    for filter_data in filters:
        filter_type = filter_data.get("filterType")
        
        if not isinstance(filter_type, str):
            raise Exception(f"exchange info filter type is not string, type {filter_type}")
        
        if filter_type == "PRICE_FILTER":
            tick_size = filter_data.get("tickSize")
            if not isinstance(tick_size, str):
                raise Exception(f"exchange info tickSize type is not string, tick size {tick_size}")
            
            p_prec = get_prec_just_for_binance_filter(tick_size)
                
        elif filter_type == "LOT_SIZE":
            step_size = filter_data.get("stepSize")
            if not isinstance(step_size, str):
                raise Exception(f"exchange info stepSize type is not string, step size {step_size}")
            
            q_prec = get_prec_just_for_binance_filter(step_size)
    
    return ExchangeSymbolFiltersInfo(
        pPrec=p_prec,
        qPrec=q_prec,
        canMarket=can_market
    )


# API Functions
def ping_spot_endpoint() -> None:
    """Ping the spot API endpoint to check connectivity.
    
    Raises:
        Exception: If request fails
    """
    req = Request(
        base_url=API_ENDPOINT,
        path=API_V3 + "/ping",
    )
    
    request(req)


def get_spot_server_time() -> Response[ServerTime]:
    """Get server time from spot API.
    
    Returns:
        Response with server timestamp
        
    Raises:
        Exception: If request fails
    """
    req = Request(
        base_url=API_ENDPOINT,
        path=API_V3 + "/time",
    )
    
    return request(req)


def get_spot_exchange_info(
    *,
    symbol: str = None,
    symbols: list[str] = None,
    permissions: list[AcctSybPermission] = None,
    show_permission_sets: bool = None,
    symbol_status: SymbolStatus = None
    ) -> Response[SpotExchangeInfo]:
    """Get spot exchange information.
    
    Args:
        params: Optional parameters to filter the response
        
    Returns:
        Response with complete exchange data
        
    Raises:
        Exception: If request fails
    """
    
    req = Request(
        base_url=API_ENDPOINT,
        path=API_V3 + "/exchangeInfo",
        params=locals(),
    )
    
    return request(req)


def get_spot_symbols() -> list[Symbol]:
    """Get all spot trading symbols converted to internal Symbol format.
    
    Returns:
        List of Symbol objects
        
    Raises:
        ValueError: If request fails or symbol parsing fails
    """
    exchange_info = get_spot_exchange_info()
    symbols = []
    
    for symbol_data in exchange_info.symbols:
        symbol = symbol_data.to_cex_symbol()
        symbols.append(symbol)
    
    return symbols




