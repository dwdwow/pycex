from dataclasses import dataclass
import time
from typing import NotRequired, TypedDict

from cex.symbol import (
    Symbol,
    SymbolType
)
from cex.cex_name import (
    CexName
)
from cex.bnc.endpoints import (
    API_ENDPOINT,
    API_V3
)
from cex.bnc.rest import (
    request
)
from cex.bnc.enums import (
    KlineInterval,
    SymbolStatus,
    AcctSybPermission,
    OrderType,
    RateLimitType,
    RateLimiterInterval
)

# Data structures
ServerTime = TypedDict("ServerTime", {"serverTime": int})


ExchangeSymbol = TypedDict("ExchangeSymbol", {
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


def to_cex_symbol(exchange_symbol: ExchangeSymbol) -> Symbol:
    filters_info = analyze_exchange_symbol_filters(exchange_symbol["filters"])
    return Symbol(
        cex=CexName.BINANCE,
        type=SymbolType.SPOT,
        asset=exchange_symbol["baseAsset"],
        quote=exchange_symbol["quoteAsset"],
        symbol=exchange_symbol["symbol"],
        mid_symbol="",
        q_precision=filters_info["qPrec"],
        p_precision=filters_info["pPrec"],
        tradable=exchange_symbol["status"] == SymbolStatus.TRADING,
        can_market=OrderType.MARKET in exchange_symbol["orderTypes"],
        can_margin=exchange_symbol["isMarginTradingAllowed"]
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


ExchangeInfo = TypedDict("ExchangeInfo", {
    "timezone": str,
    "serverTime": int,
    "rateLimits": list[RateLimiter],
    "exchangeFilters": list[any],
    "symbols": list[ExchangeSymbol],
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
async def ping_endpoint() -> None:
    """Ping the spot API endpoint to check connectivity.
    
    Raises:
        Exception: If request fails
    """
    await request(API_ENDPOINT, API_V3 + "/ping")


async def get_server_time() -> ServerTime:
    """Get server time from spot API.
    
    Returns:
        Response with server timestamp
        
    Raises:
        Exception: If request fails
    """
    return await request(API_ENDPOINT, API_V3 + "/time")


async def get_exchange_info(
    *,
    symbol: str = None,
    symbols: list[str] = None,
    permissions: list[AcctSybPermission] = None,
    show_permission_sets: bool = None,
    symbol_status: SymbolStatus = None
    ) -> ExchangeInfo:
    """Get spot exchange information.
    
    Args:
        params: Optional parameters to filter the response
        
    Returns:
        Response with complete exchange data
        
    Raises:
        Exception: If request fails
    """
    
    return await request(API_ENDPOINT, API_V3 + "/exchangeInfo", params=locals())


async def get_symbols() -> list[Symbol]:
    """Get all spot trading symbols converted to internal Symbol format.
    
    Returns:
        List of Symbol objects
        
    Raises:
        ValueError: If request fails or symbol parsing fails
    """
    exchange_info = await get_exchange_info()
    symbols = []
    
    for symbol_data in exchange_info["symbols"]:
        symbol = to_cex_symbol(symbol_data)
        symbols.append(symbol)
    
    return symbols


# ========== Order Book ==========

RawOrderBook = TypedDict("RawOrderBook", {
    "lastUpdateId": int,
    "bids": list[list[str]],
    "asks": list[list[str]],
    # Futures
    "E": NotRequired[int],  # Event time
    "T": NotRequired[int],  # Transaction time
    # CM Futures
    "symbol": NotRequired[str],
    "pair": NotRequired[str]
})


OrderBook = TypedDict("OrderBook", {
    "lastUpdateId": int,
    "bids": list[list[float]],
    "asks": list[list[float]],
    # UM && CM Futures
    "E": NotRequired[int],  # Event time
    "T": NotRequired[int],  # Transaction time
    # CM Futures
    "symbol": NotRequired[str],
    "pair": NotRequired[str],
    # Local additions
    "localTime": NotRequired[int],  # Nanoseconds
    "symbolType": NotRequired[SymbolType]
})


async def get_raw_order_book(
    *,
    symbol: str,
    limit: int = None
) -> RawOrderBook:
    """Get raw order book for spot symbol.
    
    Args:
        symbol: Trading symbol
        limit: Limit for order book depth (default 100, range [100, 5000])
    
    Returns:
        Response with raw order book data
    """
    resp = await request(API_ENDPOINT, API_V3 + "/depth", params=locals())
    
    
    # Fill symbol and pair
    if resp:
        resp["symbol"] = symbol
        resp["pair"] = symbol
    
    return resp


async def get_order_book(
    *,
    symbol: str,
    limit: int = None
) -> OrderBook:
    """Get order book for spot symbol with parsed floats.
    
    Args:
        symbol: Trading symbol
        limit: Limit for order book depth (default 100, range [100, 5000])
    
    Returns:
        OrderBook with float prices and quantities
    """
    raw_order_book = await get_raw_order_book(symbol=symbol, limit=limit)
    
    # Parse bids
    bids = []
    for bid in raw_order_book["bids"]:
        bids.append([float(bid[0]), float(bid[1])])
    
    # Parse asks
    asks = []
    for ask in raw_order_book["asks"]:
        asks.append([float(ask[0]), float(ask[1])])
    
    return OrderBook(
        lastUpdateId=raw_order_book["lastUpdateId"],
        bids=bids,
        asks=asks,
        symbol=symbol,
        pair=symbol,
        localTime=time.time_ns(),
        symbolType=SymbolType.SPOT
    )


# ========== Trades ==========

Trade = TypedDict("Trade", {
    "id": int,
    "price": str,
    "qty": str,
    "quoteQty": str,
    "time": int,
    "isBuyerMaker": bool,
    # Spot
    "isBestMatch": NotRequired[bool]
})


async def get_trades(
    *,
    symbol: str,
    limit: int = None
) -> list[Trade]:
    """Get recent trades for spot symbol.
    
    Args:
        symbol: Trading symbol
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        Response with list of trades
    """
    return await request(API_ENDPOINT, API_V3 + "/trades", params=locals())


async def get_historical_trades(
    *,
    symbol: str,
    limit: int = None,
    fromId: int = None
) -> list[Trade]:
    """Get historical trades for spot symbol.
    
    Args:
        symbol: Trading symbol
        limit: Limit (default 500, range [500, 1000])
        fromId: Trade ID to fetch from
    
    Returns:
        Response with list of historical trades
    """
    return await request(API_ENDPOINT, API_V3 + "/historicalTrades", params=locals())


# ========== Aggregate Trades ==========

AggTrade = TypedDict("AggTrade", {
    "a": int,  # Aggregate trade ID
    "p": str,  # Price
    "q": str,  # Quantity
    "f": int,  # First trade ID
    "l": int,  # Last trade ID
    "T": int,  # Timestamp
    "m": bool,  # Is buyer maker
    "M": bool   # Is best match
})


async def get_agg_trades(
    *,
    symbol: str,
    fromId: int = None,
    startTime: int = None,
    endTime: int = None,
    limit: int = None
) -> list[AggTrade]:
    """Get aggregate trades for spot symbol.
    
    Args:
        symbol: Trading symbol
        fromId: Aggregate trade ID to fetch from (INCLUSIVE)
        startTime: Timestamp in ms (INCLUSIVE)
        endTime: Timestamp in ms (INCLUSIVE)
        limit: Limit (default 500, max 1000)
    
    Returns:
        Response with list of aggregate trades
    """
    return await request(API_ENDPOINT, API_V3 + "/aggTrades", params=locals())


# ========== Klines ==========

# RawKline format:
# [
#   1499040000000,      // 0: Kline open time
#   "0.01634790",       // 1: Open price
#   "0.80000000",       // 2: High price
#   "0.01575800",       // 3: Low price
#   "0.01577100",       // 4: Close price
#   "148976.11427815",  // 5: Volume
#   1499644799999,      // 6: Kline close time
#   "2434.19055334",    // 7: Quote asset volume
#   308,                // 8: Number of trades
#   "1756.87402397",    // 9: Taker buy base asset volume
#   "28.46694368",      // 10: Taker buy quote asset volume
#   "0"                 // 11: Unused field, ignore
# ]

RawKline = list[int | str]

@dataclass
class Kline:
    open_time: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    close_time: int
    quote_asset_volume: float
    number_of_trades: int
    base_asset_taker_buy_volume: float
    quote_asset_taker_buy_volume: float
    
    def valid(self) -> bool:
        return self.open_time != 0
    

def raw_kline_to_kline(raw_kline: RawKline) -> Kline:
    return Kline(
        open_time=raw_kline[0],
        open_price=float(raw_kline[1]),
        high_price=float(raw_kline[2]),
        low_price=float(raw_kline[3]),
        close_price=float(raw_kline[4]),
        volume=float(raw_kline[5]),
        close_time=raw_kline[6],
        quote_asset_volume=float(raw_kline[7]),
        number_of_trades=raw_kline[8],
        base_asset_taker_buy_volume=float(raw_kline[9]),
        quote_asset_taker_buy_volume=float(raw_kline[10])
    )


async def get_raw_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw kline data for spot symbol.
    
    Args:
        symbol: Trading symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        Response with list of raw klines
    """
    interval = interval.value
    return await request(API_ENDPOINT, API_V3 + "/klines", params=locals())


async def get_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get kline data for spot symbol with parsed values.
    
    Args:
        symbol: Trading symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of Kline objects
    """
    raw_klines = await get_raw_klines(
        symbol=symbol,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


# ========== Average Price ==========

AvgPrice = TypedDict("AvgPrice", {
    "mins": int,
    "price": str,
    "closeTime": int
})


async def get_avg_price(*, symbol: str) -> AvgPrice:
    """Get average price for spot symbol.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Response with average price data
    """
    return await request(API_ENDPOINT, API_V3 + "/avgPrice", params=locals())


# ========== 24hr Ticker Statistics ==========

Ticker24HrStats = TypedDict("Ticker24HrStats", {
    # MINI & FULL
    "symbol": str,
    "lastPrice": str,
    "openPrice": str,
    "highPrice": str,
    "lowPrice": str,
    "volume": str,
    "quoteVolume": str,
    "openTime": int,
    "closeTime": int,
    "firstId": int,
    "lastId": int,
    "count": int,
    # FULL
    "priceChange": NotRequired[str],
    "priceChangePercent": NotRequired[str],
    "weightedAvgPrice": NotRequired[str],
    "prevClosePrice": NotRequired[str],
    "lastQty": NotRequired[str],
    # FULL, SPOT
    "bidPrice": NotRequired[str],
    "bidQty": NotRequired[str],
    "askPrice": NotRequired[str],
    "askQty": NotRequired[str]
})


async def get_ticker_24hr_stats(
    *,
    symbol: str,
    type: str = None
) -> Ticker24HrStats:
    """Get 24hr ticker statistics for spot symbol.
    
    Args:
        symbol: Trading symbol (required)
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with 24hr ticker statistics
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/24hr", params=locals())


async def get_ticker_24hr_stats_list(
    *,
    symbols: list[str] = None,
    type: str = None
) -> list[Ticker24HrStats]:
    """Get 24hr ticker statistics for multiple spot symbols.
    
    Args:
        symbols: List of trading symbols (optional, returns all if not provided)
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with list of 24hr ticker statistics
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/24hr", params=locals())


# ========== Trading Day Ticker Statistics ==========

TickerTradingDayStats = TypedDict("TickerTradingDayStats", {
    "symbol": str,
    "priceChange": str,
    "priceChangePercent": str,
    "weightedAvgPrice": str,
    "openPrice": str,
    "highPrice": str,
    "lowPrice": str,
    "lastPrice": str,
    "volume": str,
    "quoteVolume": str,
    "openTime": int,
    "closeTime": int,
    "firstId": int,
    "lastId": int,
    "count": int
})


async def get_ticker_trading_day_stats(
    *,
    symbol: str,
    timeZone: str = None,
    type: str = None
) -> TickerTradingDayStats:
    """Get trading day ticker statistics for spot symbol.
    
    Args:
        symbol: Trading symbol (required)
        timeZone: Timezone string
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with trading day ticker statistics
    
    Raises:
        Exception: If symbol is not provided
    """
    if not symbol:
        raise Exception("bnc: get_spot_ticker_trading_day_stats, symbol is required")
    
    return await request(API_ENDPOINT, API_V3 + "/ticker/tradingDay", params=locals())


async def get_ticker_trading_day_stats_list(
    *,
    symbols: list[str],
    timeZone: str = None,
    type: str = None
) -> list[TickerTradingDayStats]:
    """Get trading day ticker statistics for multiple spot symbols.
    
    Args:
        symbols: List of trading symbols (max 100)
        timeZone: Timezone string
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with list of trading day ticker statistics
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/tradingDay", params=locals())


# ========== Ticker Price ==========

TickerPrice = TypedDict("TickerPrice", {
    "symbol": str,
    "price": str,
    # Futures
    "time": NotRequired[int],
    # CM Futures
    "pair": NotRequired[str]
})


async def get_ticker_price(*, symbol: str) -> TickerPrice:
    """Get ticker price for spot symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Response with ticker price
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/price", params=locals())


async def get_ticker_price_list(
    *,
    symbols: list[str] = None
) -> list[TickerPrice]:
    """Get ticker prices for multiple spot symbols.
    
    Args:
        symbols: List of trading symbols (optional, returns all if not provided)
    
    Returns:
        Response with list of ticker prices
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/price", params=locals())


# ========== Order Book Ticker ==========

OrderBookTicker = TypedDict("OrderBookTicker", {
    "symbol": str,
    "bidPrice": str,
    "bidQty": str,
    "askPrice": str,
    "askQty": str,
    # Futures
    "time": NotRequired[int]
})


async def get_order_book_ticker(*, symbol: str) -> OrderBookTicker:
    """Get order book ticker for spot symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Response with order book ticker
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/bookTicker", params=locals())


async def get_ticker_book_ticker_list(
    *,
    symbols: list[str] = None
) -> list[OrderBookTicker]:
    """Get order book tickers for multiple spot symbols.
    
    Args:
        symbols: List of trading symbols (optional, returns all if not provided)
    
    Returns:
        Response with list of order book tickers
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker/bookTicker", params=locals())


# ========== Ticker Statistics ==========

TickerStats = TypedDict("TickerStats", {
    "symbol": str,
    "priceChange": str,
    "priceChangePercent": str,
    "weightedAvgPrice": str,
    "openPrice": str,
    "highPrice": str,
    "lowPrice": str,
    "lastPrice": str,
    "volume": str,
    "quoteVolume": str,
    "openTime": int,
    "closeTime": int,
    "firstId": int,
    "lastId": int,
    "count": int
})


async def get_ticker_stats(
    *,
    symbol: str,
    windowSize: str = None,
    type: str = None
) -> TickerStats:
    """Get ticker statistics for spot symbol.
    
    Args:
        symbol: Trading symbol (required)
        windowSize: Window size (1m-59m, 1h-23h, 1d-7d, default 1d)
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with ticker statistics
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker", params=locals())


async def get_ticker_stats_list(
    *,
    symbols: list[str],
    windowSize: str = None,
    type: str = None
) -> list[TickerStats]:
    """Get ticker statistics for multiple spot symbols.
    
    Args:
        symbols: List of trading symbols (max 100)
        windowSize: Window size (1m-59m, 1h-23h, 1d-7d, default 1d)
        type: FULL or MINI (default FULL)
    
    Returns:
        Response with list of ticker statistics
    """
    return await request(API_ENDPOINT, API_V3 + "/ticker", params=locals())


