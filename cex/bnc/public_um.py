import time

from typing import TypedDict, NotRequired

from cex.symbol import (
    Symbol,
    SymbolType
)
from cex.cex_name import (
    CexName
)
from cex.bnc.rest import (
    request
)
from cex.bnc.endpoints import (
    API_UM_FUTURES_ENDPOINT,
    FAPI_V1,
    FUTURES_DATA
)
from cex.bnc.enums import (
    ContractType, KlineInterval, SymbolStatus, ContractStatus, 
    OrderType, TimeInForce, RateLimitType, RateLimiterInterval
)
from cex.bnc.public_spot import (
    OrderBookTicker, RawOrderBook, OrderBook, Ticker24HrStats,
    TickerPrice, Trade, AggTrade, RawKline,
    Kline, analyze_exchange_symbol_filters, raw_kline_to_kline
)


# ========== Server Time ==========

ServerTime = TypedDict("ServerTime", {"serverTime": int})


async def get_server_time() -> ServerTime:
    """Get UM Futures server time.
    
    Returns:
        Server time data
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/time")


# ========== Exchange Info ==========

ExchangeSymbol = TypedDict("ExchangeSymbol", {
    "symbol": str,  # e.g. SPOT/PERPETUAL:"BTCUSDT", Delivery:"BTCUSDT_200925" CM:"BTCUSD_PERP"
    "pair": str,  # underlying symbol e.g. "BTCUSDT" "BTCUSD"
    "contractType": ContractType,
    "deliveryDate": int,
    "onboardDate": int,
    "status": SymbolStatus,
    "contractStatus": NotRequired[ContractStatus],
    "contractSize": NotRequired[float],
    "baseAsset": str,
    "quoteAsset": str,
    "marginAsset": str,
    "pricePrecision": int,
    "quantityPrecision": int,
    "baseAssetPrecision": int,
    "quotePrecision": int,
    "underlyingType": str,
    "underlyingSubType": list[str],
    "settlePlan": int,
    "triggerProtect": str,
    "filters": list[dict[str, any]],
    "orderTypes": list[OrderType],
    "timeInForce": list[TimeInForce],
    "liquidationFee": str,
    "marketTakeBound": str,
    "permissionSets": NotRequired[list[any]]
})


def to_cex_symbol(exchange_symbol: ExchangeSymbol) -> Symbol:
    """Convert FuturesExchangeSymbol to internal Symbol format."""
    
    filters_info = analyze_exchange_symbol_filters(exchange_symbol["filters"])
    
    return Symbol(
        cex=CexName.BINANCE,
        type=SymbolType.UM_FUTURES,
        asset=exchange_symbol["baseAsset"],
        quote=exchange_symbol["quoteAsset"],
        symbol=exchange_symbol["symbol"],
        mid_symbol="",
        q_precision=filters_info["qPrec"],
        p_precision=filters_info["pPrec"],
        tradable=(
            exchange_symbol.get("status") == SymbolStatus.TRADING or 
            exchange_symbol.get("contractStatus") == ContractStatus.TRADING
        ),
        can_market=OrderType.MARKET in exchange_symbol["orderTypes"],
        is_perpetual=exchange_symbol["contractType"] == ContractType.PERPETUAL,
        contract_size=exchange_symbol.get("contractSize"),
        contract_type=exchange_symbol["contractType"].value if isinstance(exchange_symbol["contractType"], ContractType) else str(exchange_symbol["contractType"]),
        delivery_date=exchange_symbol["deliveryDate"],
        onboard_date=exchange_symbol["onboardDate"]
    )


MarginAsset = TypedDict("MarginAsset", {
    "asset": str,  # The asset code (e.g. "BTC")
    "marginAvailable": bool,  # Whether the asset can be used as margin in Multi-Assets mode
    "autoAssetExchange": str  # Auto-exchange threshold in Multi-Assets margin mode
})


RateLimiter = TypedDict("RateLimiter", {
    "rateLimitType": RateLimitType,
    "interval": RateLimiterInterval,
    "intervalNum": int,
    "limit": int
})


ExchangeInfo = TypedDict("ExchangeInfo", {
    "timezone": str,
    "serverTime": int,
    "rateLimits": list[RateLimiter],
    "exchangeFilters": list[any],
    "assets": list[MarginAsset],
    "symbols": list[ExchangeSymbol]
})


async def get_exchange_info() -> ExchangeInfo:
    """Get UM Futures exchange information.
    
    Returns:
        FuturesExchangeInfo with complete exchange data
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/exchangeInfo")


async def get_symbols() -> list[Symbol]:
    """Get all UM Futures trading symbols converted to internal Symbol format.
    
    Returns:
        List of Symbol objects
    """
    exchange_info = await get_exchange_info()
    symbols = []
    
    for symbol_data in exchange_info["symbols"]:
        symbol = to_cex_symbol(symbol_data)
        symbols.append(symbol)
    
    return symbols


# ========== Order Book ==========


async def get_raw_order_book(
    *,
    symbol: str,
    limit: int = None
) -> RawOrderBook:
    """Get raw order book for UM Futures symbol.
    
    Args:
        symbol: Trading symbol
        limit: Limit for order book depth (default 500, range 5, 10, 20, 50, [100, 1000])
    
    Returns:
        Raw order book data
    """
    resp = await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/depth", params=locals())
    
    # Fill symbol and pair
    if resp:
        resp["symbol"] = symbol
        pair = symbol
        if "_" in pair:
            resp["pair"] = pair.split("_")[0]
    
    return resp


async def get_order_book(
    *,
    symbol: str,
    limit: int = None
) -> OrderBook:
    """Get order book for UM Futures symbol with parsed floats.
    
    Args:
        symbol: Trading symbol
        limit: Limit for order book depth (default 500, range 5, 10, 20, 50, [100, 1000])
    
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
        E=raw_order_book.get("E"),
        T=raw_order_book.get("T"),
        symbol=raw_order_book.get("symbol"),
        pair=raw_order_book.get("pair"),
        localTime=time.time_ns(),
        symbolType=SymbolType.UM_FUTURES
    )


# ========== Trades ==========

async def get_trades(
    *,
    symbol: str,
    limit: int = None
) -> list[Trade]:
    """Get recent trades for UM Futures symbol.
    
    Args:
        symbol: Trading symbol
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of trades
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/trades", params=locals())


async def get_historical_trades(
    *,
    symbol: str,
    limit: int = None,
    fromId: int = None
) -> list[Trade]:
    """Get historical trades for UM Futures symbol.
    
    DEPRECATED - must use API key, weird
    
    Args:
        symbol: Trading symbol
        limit: Limit (default 500, range [500, 1000])
        fromId: Trade ID to fetch from
    
    Returns:
        List of historical trades
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/historicalTrades", params=locals())


# ========== Aggregate Trades ==========

async def get_agg_trades(
    *,
    symbol: str,
    fromId: int = None,
    startTime: int = None,
    endTime: int = None,
    limit: int = None
) -> list[AggTrade]:
    """Get aggregate trades for UM Futures symbol.
    
    Args:
        symbol: Trading symbol
        fromId: Aggregate trade ID to fetch from (INCLUSIVE)
        startTime: Timestamp in ms (INCLUSIVE)
        endTime: Timestamp in ms (INCLUSIVE)
        limit: Limit (default 500, max 1000)
    
    Returns:
        List of aggregate trades
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/aggTrades", params=locals())


# ========== Klines ==========

async def get_raw_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw kline data for UM Futures symbol.
    
    Args:
        symbol: Trading symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of raw klines
    """
    interval = interval.value
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/klines", params=locals())


async def get_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get kline data for UM Futures symbol with parsed values.
    
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


async def get_raw_continuous_klines(
    *,
    pair: str,
    contractType: ContractType,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw continuous contract kline data.
    
    Args:
        pair: Pair symbol
        contractType: Contract type (PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (max 1500 for continuous contract)
    
    Returns:
        List of raw klines
    """
    contractType = contractType.value
    interval = interval.value
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/continuousKlines", params=locals())


async def get_continuous_klines(
    *,
    pair: str,
    contractType: ContractType,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get continuous contract kline data with parsed values.
    
    Args:
        pair: Pair symbol
        contractType: Contract type (PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (max 1500 for continuous contract)
    
    Returns:
        List of Kline objects
    """
    raw_klines = await get_raw_continuous_klines(
        pair=pair,
        contractType=contractType,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


async def get_raw_index_price_klines(
    *,
    pair: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw index price kline data.
    
    Args:
        pair: Pair symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of raw klines
    """
    interval = interval.value
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/indexPriceKlines", params=locals())


async def get_index_price_klines(
    *,
    pair: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get index price kline data with parsed values.
    
    Args:
        pair: Pair symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of Kline objects
    """
    raw_klines = await get_raw_index_price_klines(
        pair=pair,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


async def get_raw_mark_price_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw mark price kline data.
    
    Args:
        symbol: Trading symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of raw klines
    """
    interval = interval.value
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/markPriceKlines", params=locals())


async def get_mark_price_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get mark price kline data with parsed values.
    
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
    raw_klines = await get_raw_mark_price_klines(
        symbol=symbol,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


async def get_raw_premium_index_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw premium index kline data.
    
    Args:
        symbol: Trading symbol
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit (default 500, range [500, 1000])
    
    Returns:
        List of raw klines
    """
    interval = interval.value
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/premiumIndexKlines", params=locals())


async def get_premium_index_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get premium index kline data with parsed values.
    
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
    raw_klines = await get_raw_premium_index_klines(
        symbol=symbol,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


# ========== Mark Price and Funding Rate ==========

MarkPriceInfo = TypedDict("MarkPriceInfo", {
    "symbol": str,
    "markPrice": str,
    "indexPrice": str,
    "estimatedSettlePrice": str,
    "lastFundingRate": str,
    "interestRate": str,
    "nextFundingTime": int,
    "time": int
})


async def get_mark_price_info(*, symbol: str) -> MarkPriceInfo:
    """Get mark price info for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Mark price information
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/premiumIndex", params=locals())


async def get_all_mark_price_info() -> list[MarkPriceInfo]:
    """Get mark price info for all UM Futures symbols.
    
    Returns:
        List of mark price information
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/premiumIndex")


FundingRate = TypedDict("FundingRate", {
    "symbol": str,
    "fundingRate": str,
    "fundingTime": int,
    "markPrice": NotRequired[str]
})


async def get_funding_rate_history(
    *,
    symbol: str = None,
    startTime: int = None,
    endTime: int = None,
    limit: int = None
) -> list[FundingRate]:
    """Get funding rate history for UM Futures.
    
    Args:
        symbol: Trading symbol (default all symbols)
        startTime: Start time in ms
        endTime: End time in ms
        limit: Limit (default 100, range [100, 1000])
    
    Returns:
        List of funding rates
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/fundingRate", params=locals())


FundingInfo = TypedDict("FundingInfo", {
    "symbol": str,
    "adjustedFundingRateCap": str,
    "adjustedFundingRateFloor": str,
    "fundingIntervalHours": int,
    "disclaimer": bool
})


async def get_funding_info_list() -> list[FundingInfo]:
    """Get funding info for all UM Futures symbols.
    
    Returns:
        List of funding information
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/fundingInfo")


# ========== 24hr Ticker Statistics ==========


async def get_ticker_24hr_stats(
    *,
    symbol: str,
    type: str = None
) -> Ticker24HrStats:
    """Get 24hr ticker statistics for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
        type: FULL or MINI (default FULL)
    
    Returns:
        24hr ticker statistics
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/24hr", params=locals())


async def get_ticker_24hr_stats_list() -> list[Ticker24HrStats]:
    """Get 24hr ticker statistics for all UM Futures symbols.
    
    Returns:
        List of 24hr ticker statistics
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/24hr")


async def get_ticker_price(*, symbol: str) -> TickerPrice:
    """Get ticker price for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Ticker price
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/price", params=locals())


async def get_ticker_price_list() -> list[TickerPrice]:
    """Get ticker prices for all UM Futures symbols.
    
    Returns:
        List of ticker prices
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/price")


async def get_order_book_ticker(*, symbol: str) -> OrderBookTicker:
    """Get order book ticker for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Order book ticker
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/bookTicker", params=locals())


async def get_ticker_book_ticker_list() -> list[OrderBookTicker]:
    """Get order book tickers for all UM Futures symbols.
    
    Returns:
        List of order book tickers
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/ticker/bookTicker")


# ========== Delivery Price ==========


DeliveryPrice = TypedDict("DeliveryPrice", {
    "deliveryTime": int,
    "deliveryPrice": str
})


async def get_delivery_price_list(*, pair: str) -> list[DeliveryPrice]:
    """Get delivery price list for UM Futures pair.
    
    Args:
        pair: Pair symbol (required)
    
    Returns:
        List of delivery prices
    
    Raises:
        Exception: If pair is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, "/futures/data/delivery-price", params=locals())


# ========== Open Interest ==========

OpenInterest = TypedDict("OpenInterest", {
    "symbol": str,
    "openInterest": str,
    "time": int,
    # CM Futures
    "pair": NotRequired[str],
    "contractType": NotRequired[ContractType]
})


async def get_open_interest(*, symbol: str) -> OpenInterest:
    """Get open interest for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Open interest data
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/openInterest", params=locals())


OpenInterestStats = TypedDict("OpenInterestStats", {
    "symbol": str,
    "sumOpenInterest": str,
    "sumOpenInterestValue": str,
    "CMCCirculatingSupply": str,
    "timestamp": int
})


async def get_open_interest_stats(
    *,
    symbol: str,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[OpenInterestStats]:
    """Get open interest statistics for UM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of open interest statistics
    
    Raises:
        Exception: If symbol or period is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/openInterestHist", params=locals())


# ========== Long/Short Ratio ==========

LongShortRatio = TypedDict("LongShortRatio", {
    "symbol": str,
    "longShortRatio": str,
    "longAccount": str,
    "shortAccount": str,
    "timestamp": int
})


async def get_top_trader_long_short_position_ratio(
    *,
    symbol: str,
    period: str,
    limit: int = None,
    startTime: int = None,
    endTime: int = None
) -> list[LongShortRatio]:
    """Get top trader long/short position ratio for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        startTime: Start time in ms
        endTime: End time in ms
    
    Returns:
        List of long/short ratios
    
    Raises:
        Exception: If symbol or period is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/topLongShortPositionRatio", params=locals())


async def get_top_trader_long_short_account_ratio(
    *,
    symbol: str,
    period: str,
    limit: int = None,
    startTime: int = None,
    endTime: int = None
) -> list[LongShortRatio]:
    """Get top trader long/short account ratio for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        startTime: Start time in ms
        endTime: End time in ms
    
    Returns:
        List of long/short ratios
    
    Raises:
        Exception: If symbol or period is not provided
    """
    if not symbol:
        raise Exception("bnc: symbol is required")
    if not period:
        raise Exception("bnc: period is required")
    
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/topLongShortAccountRatio", params=locals())


async def get_global_long_short_account_ratio(
    *,
    symbol: str,
    period: str,
    limit: int = None,
    startTime: int = None,
    endTime: int = None
) -> list[LongShortRatio]:
    """Get global long/short account ratio for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        startTime: Start time in ms
        endTime: End time in ms
    
    Returns:
        List of long/short ratios
    
    Raises:
        Exception: If symbol or period is not provided
    """
    if not symbol:
        raise Exception("bnc: symbol is required")
    if not period:
        raise Exception("bnc: period is required")
    
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/globalLongShortAccountRatio", params=locals())


# ========== Taker Buy/Sell Ratio ==========

TakerBuySellRatio = TypedDict("TakerBuySellRatio", {
    "buySellRatio": str,
    "buyVol": str,
    "sellVol": str,
    "timestamp": int
})


async def get_taker_buy_sell_ratio(
    *,
    symbol: str,
    period: str,
    limit: int = None,
    startTime: int = None,
    endTime: int = None
) -> list[TakerBuySellRatio]:
    """Get taker buy/sell volume ratio for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        startTime: Start time in ms
        endTime: End time in ms
    
    Returns:
        List of taker buy/sell ratios
    
    Raises:
        Exception: If symbol or period is not provided
    """
    if not symbol:
        raise Exception("bnc: symbol is required")
    if not period:
        raise Exception("bnc: period is required")
    
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/takerlongshortRatio", params=locals())


# ========== Futures Basis ==========

FuturesBasis = TypedDict("FuturesBasis", {
    "indexPrice": str,
    "contractType": ContractType,
    "basisRate": str,
    "futuresPrice": str,
    "annualizedBasisRate": str,
    "basis": str,
    "pair": str,
    "timestamp": int
})


async def get_futures_basis(
    *,
    pair: str,
    contractType: ContractType,
    period: str,
    limit: int,
    startTime: int = None,
    endTime: int = None
) -> list[FuturesBasis]:
    """Get futures basis data for UM Futures.
    
    Args:
        pair: Pair symbol (required)
        contractType: Contract type (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit [30, 500] (required)
        startTime: Start time in ms
        endTime: End time in ms
    
    Returns:
        List of futures basis data
    
    Raises:
        Exception: If required parameters are not provided
    """
    if not pair:
        raise Exception("bnc: pair is required")
    if not contractType:
        raise Exception("bnc: contractType is required")
    if not period:
        raise Exception("bnc: period is required")
    contractType = contractType.value
    return await request(API_UM_FUTURES_ENDPOINT, FUTURES_DATA + "/basis", params=locals())


# ========== Composite Index Symbol Info ==========

FuturesBaseAsset = TypedDict("FuturesBaseAsset", {
    "baseAsset": str,
    "quoteAsset": str,
    "weightInQuantity": str,
    "weightInPercentage": str
})


CompositeIndexSymbolInfo = TypedDict("CompositeIndexSymbolInfo", {
    "symbol": str,
    "time": int,
    "component": str,
    "baseAssetList": list[FuturesBaseAsset]
})


async def get_composite_index_symbol_info(*, symbol: str) -> CompositeIndexSymbolInfo:
    """Get composite index symbol info for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Composite index symbol information
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/indexInfo", params=locals())


async def get_composite_index_symbol_info_list() -> list[CompositeIndexSymbolInfo]:
    """Get composite index symbol info for all UM Futures symbols.
    
    Returns:
        List of composite index symbol information
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/indexInfo")


# ========== Multi-Assets Mode Asset Index ==========

MultiAssetsModeAssetIndex = TypedDict("MultiAssetsModeAssetIndex", {
    "symbol": str,
    "time": int,
    "index": str,
    "bidBuffer": str,
    "askBuffer": str,
    "bidRate": str,
    "askRate": str,
    "autoExchangeBidBuffer": str,
    "autoExchangeAskBuffer": str,
    "autoExchangeBidRate": str,
    "autoExchangeAskRate": str
})


async def get_multi_assets_mode_asset_index(*, symbol: str) -> MultiAssetsModeAssetIndex:
    """Get multi-assets mode asset index for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Multi-assets mode asset index
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/assetIndex", params=locals())


async def get_multi_assets_mode_asset_index_list() -> list[MultiAssetsModeAssetIndex]:
    """Get multi-assets mode asset index for all UM Futures symbols.
    
    Returns:
        List of multi-assets mode asset indexes
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/assetIndex")


# ========== Index Price Constituents ==========

IndexPriceConstituentInfo = TypedDict("IndexPriceConstituentInfo", {
    "exchange": str,
    "symbol": str,
    # UM Futures
    "price": str,
    "weight": str
})


IndexPriceConstituents = TypedDict("IndexPriceConstituents", {
    "symbol": str,
    "time": int,
    "constituents": list[IndexPriceConstituentInfo]
})


async def get_index_price_constituent_info(*, symbol: str) -> IndexPriceConstituents:
    """Get index price constituent info for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Index price constituents
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/constituents", params=locals())


# ========== Insurance Fund ==========

InsuranceFundAsset = TypedDict("InsuranceFundAsset", {
    "asset": str,
    "marginBalance": str,
    "updateTime": int
})


InsuranceFundBalanceSnapshot = TypedDict("InsuranceFundBalanceSnapshot", {
    "symbols": list[str],
    "assets": list[InsuranceFundAsset]
})


async def get_insurance_fund_balance_snapshot(*, symbol: str) -> InsuranceFundBalanceSnapshot:
    """Get insurance fund balance snapshot for UM Futures.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Insurance fund balance snapshot
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/insuranceBalance", params=locals())


async def get_insurance_fund_balance_snapshot_list() -> list[InsuranceFundBalanceSnapshot]:
    """Get insurance fund balance snapshot for all UM Futures symbols.
    
    Returns:
        List of insurance fund balance snapshots
    """
    return await request(API_UM_FUTURES_ENDPOINT, FAPI_V1 + "/insuranceBalance")
