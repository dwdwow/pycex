from typing import TypedDict, NotRequired
import time

from cex.symbol import (
    Symbol,
    SymbolType
)
from cex.bnc.endpoints import (
    API_CM_FUTURES_ENDPOINT,
    DAPI_V1,
    FUTURES_DATA
)
from cex.bnc.rest import (
    request
)
from cex.bnc.enums import (
    ContractType,
    KlineInterval,
)
from cex.bnc.public_spot import (
    OrderBookTicker,
    RawOrderBook,
    OrderBook,
    Ticker24HrStats,
    TickerPrice,
    Trade,
    RawKline,
    Kline,
    raw_kline_to_kline
)
from cex.bnc.public_um import (
    ExchangeInfo,
    FundingRate,
    FundingInfo,
    IndexPriceConstituents,
    OpenInterest,
    to_cex_symbol
)


# ========== Server Time ==========

ServerTime = TypedDict("ServerTime", {"serverTime": int})


async def check_server_time() -> ServerTime:
    """Check CM Futures server time.
    
    Returns:
        Server time data
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/time")


# ========== Exchange Info ==========

async def get_exchange_info() -> ExchangeInfo:
    """Get CM Futures exchange information.
    
    Returns:
        FuturesExchangeInfo with complete exchange data
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/exchangeInfo")


async def get_symbols() -> list[Symbol]:
    """Get all CM Futures trading symbols converted to internal Symbol format.
    
    Returns:
        List of Symbol objects
    """
    exchange_info = await get_exchange_info()
    symbols = []
    
    for symbol_data in exchange_info["symbols"]:
        symbol = to_cex_symbol(symbol_data)
        symbol.type = SymbolType.CM_FUTURES
        symbols.append(symbol)
    
    return symbols


# ========== Order Book ==========

async def get_raw_order_book(
    *,
    symbol: str,
    limit: int = None
) -> RawOrderBook:
    """Get raw order book for CM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
        limit: Limit for order book depth
    
    Returns:
        Raw order book data
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/depth", params=locals())


async def get_order_book(
    *,
    symbol: str,
    limit: int = None
) -> OrderBook:
    """Get order book for CM Futures symbol with parsed floats.
    
    Args:
        symbol: Trading symbol (required)
        limit: Limit for order book depth
    
    Returns:
        OrderBook with float prices and quantities
    
    Raises:
        Exception: If symbol is not provided
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
        symbol=raw_order_book.get("symbol"),
        pair=raw_order_book.get("pair"),
        E=raw_order_book.get("E"),
        T=raw_order_book.get("T"),
        localTime=time.time_ns(),
        symbolType=SymbolType.CM_FUTURES
    )


# ========== Trades ==========

async def get_trades(
    *,
    symbol: str,
    limit: int = None
) -> list[Trade]:
    """Get recent trades for CM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
        limit: Limit
    
    Returns:
        List of trades
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/trades", params=locals())


async def get_historical_trades(
    *,
    symbol: str,
    limit: int = None,
    fromId: int = None
) -> list[Trade]:
    """Get historical trades for CM Futures symbol.
    
    DEPRECATED - should use API KEY
    
    Args:
        symbol: Trading symbol (required)
        limit: Limit
        fromId: Trade ID to fetch from
    
    Returns:
        List of historical trades
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/historicalTrades", params=locals())


# ========== Premium Index ==========

PremiumIndexInfo = TypedDict("PremiumIndexInfo", {
    "symbol": str,  # Symbol name, e.g. "BTCUSD_PERP"
    "pair": str,  # Trading pair, e.g. "BTCUSD"
    "markPrice": str,
    "indexPrice": str,
    "estimatedSettlePrice": str,  # Only useful in the last hour before settlement
    "lastFundingRate": str,  # Latest funding rate (perpetual only, empty for delivery)
    "interestRate": str,  # Base asset interest rate (perpetual only, empty for delivery)
    "nextFundingTime": int,  # Next funding time in ms (perpetual only, 0 for delivery)
    "time": int  # Current timestamp in ms
})


async def get_premium_index_info(
    *,
    symbol: str = None,
    pair: str = None
) -> list[PremiumIndexInfo]:
    """Get premium index info for CM Futures.
    
    Args:
        symbol: Trading symbol
        pair: Trading pair
    
    Returns:
        List of premium index information
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/premiumIndex", params=locals())


# ========== Funding Rate ==========

async def get_funding_rate_history(
    *,
    symbol: str,
    startTime: int = None,
    endTime: int = None,
    limit: int = None
) -> list[FundingRate]:
    """Get funding rate history for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
        startTime: Start time in ms
        endTime: End time in ms
        limit: Limit (default 100, range [100, 1000])
    
    Returns:
        List of funding rates
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/fundingRate", params=locals())


async def get_funding_info_list() -> list[FundingInfo]:
    """Get funding info for all CM Futures symbols.
    
    Returns:
        List of funding information
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/fundingInfo")


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
    """Get raw kline data for CM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of raw klines
    
    Raises:
        Exception: If symbol is not provided
    """
    interval = interval.value
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/klines", params=locals())


async def get_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get kline data for CM Futures symbol with parsed values.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of Kline objects
    
    Raises:
        Exception: If symbol is not provided
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
    symbol: str,
    pair: str,
    contractType: ContractType,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw continuous contract kline data for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
        contractType: Contract type
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of raw klines
    
    Raises:
        Exception: If symbol is not provided
    """
    contractType = contractType.value
    interval = interval.value
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/continuousKlines", params=locals())


async def get_continuous_klines(
    *,
    symbol: str,
    pair: str,
    contractType: ContractType,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get continuous contract kline data for CM Futures with parsed values.
    
    Args:
        symbol: Trading symbol (required)
        contractType: Contract type
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of Kline objects
    
    Raises:
        Exception: If symbol is not provided
    """
    raw_klines = await get_raw_continuous_klines(
        symbol=symbol,
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
    symbol: str,
    pair: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[RawKline]:
    """Get raw index price kline data for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of raw klines
    
    Raises:
        Exception: If symbol is not provided
    """
    interval = interval.value
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/indexPriceKlines", params=locals())


async def get_index_price_klines(
    *,
    symbol: str,
    pair: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get index price kline data for CM Futures with parsed values.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of Kline objects
    
    Raises:
        Exception: If symbol is not provided
    """
    raw_klines = await get_raw_index_price_klines(
        symbol=symbol,
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
    """Get raw mark price kline data for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of raw klines
    
    Raises:
        Exception: If symbol is not provided
    """
    interval = interval.value
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/markPriceKlines", params=locals())


async def get_mark_price_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get mark price kline data for CM Futures with parsed values.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of Kline objects
    
    Raises:
        Exception: If symbol is not provided
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
    """Get raw premium index kline data for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of raw klines
    
    Raises:
        Exception: If symbol is not provided
    """
    interval = interval.value
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/premiumIndexKlines", params=locals())


async def get_premium_index_klines(
    *,
    symbol: str,
    interval: KlineInterval,
    startTime: int = None,
    endTime: int = None,
    timeZone: str = None,
    limit: int = None
) -> list[Kline]:
    """Get premium index kline data for CM Futures with parsed values.
    
    Args:
        symbol: Trading symbol (required)
        interval: Kline interval
        startTime: Start time in ms
        endTime: End time in ms
        timeZone: Timezone string
        limit: Limit
    
    Returns:
        List of Kline objects
    
    Raises:
        Exception: If symbol is not provided
    """
    raw_klines = await get_raw_premium_index_klines(
        symbol=symbol,
        interval=interval,
        startTime=startTime,
        endTime=endTime,
        timeZone=timeZone,
        limit=limit
    )
    interval = interval.value
    return [raw_kline_to_kline(raw_kline) for raw_kline in raw_klines]


# ========== 24hr Ticker Statistics ==========


async def get_ticker_24hr_stats(
    *,
    symbol: str = None,
    pair: str = None,
    type: str = None
) -> list[Ticker24HrStats]:
    """Get 24hr ticker statistics for CM Futures.
    
    Args:
        symbol: Trading symbol
        pair: Trading pair
        type: FULL or MINI
    
    Returns:
        List of 24hr ticker statistics
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/ticker/24hr", params=locals())


async def get_ticker_24hr_stats_list() -> list[Ticker24HrStats]:
    """Get 24hr ticker statistics for all CM Futures symbols.
    
    Returns:
        List of 24hr ticker statistics
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/ticker/24hr")


async def get_ticker_price(
    *,
    symbol: str = None,
    pair: str = None
) -> list[TickerPrice]:
    """Get ticker price for CM Futures.
    
    Args:
        symbol: Trading symbol
        pair: Trading pair
    
    Returns:
        List of ticker prices
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/ticker/price", params=locals())


async def get_ticker_price_list() -> list[TickerPrice]:
    """Get ticker prices for all CM Futures symbols.
    
    Returns:
        List of ticker prices
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/ticker/price")


async def get_order_book_ticker(
    *,
    symbol: str = None,
    pair: str = None
) -> list[OrderBookTicker]:
    """Get order book ticker for CM Futures.
    
    Args:
        symbol: Trading symbol
        pair: Trading pair
    
    Returns:
        List of order book tickers
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/ticker/bookTicker", params=locals())


# ========== Open Interest ==========


async def get_open_interest(*, symbol: str) -> OpenInterest:
    """Get open interest for CM Futures symbol.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Open interest data
    
    Raises:
        Exception: If symbol is not provided
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/openInterest", params=locals())


OpenInterestStats = TypedDict("OpenInterestStats", {
    "pair": str,
    "contractType": ContractType,
    "sumOpenInterest": str,
    "sumOpenInterestValue": str,
    "timestamp": int
})


async def get_open_interest_stats(
    *,
    pair: str,
    contractType: ContractType,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[OpenInterestStats]:
    """Get open interest statistics for CM Futures.
    
    Args:
        pair: Trading pair (required)
        contractType: Contract type (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of open interest statistics
    """
    contractType = contractType.value
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/openInterestHist", params=locals())


# ========== Long/Short Ratio ==========

LongShortRatio = TypedDict("LongShortRatio", {
    "pair": str,
    "longShortRatio": str,
    "longPosition": str,
    "shortPosition": str,
    "timestamp": int
})


async def get_top_trader_long_short_position_ratio(
    *,
    pair: str,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[LongShortRatio]:
    """Get top trader long/short position ratio for CM Futures.
    
    Args:
        pair: Trading pair (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of long/short ratios
    """
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/topLongShortPositionRatio", params=locals())


async def get_top_trader_long_short_account_ratio(
    *,
    pair: str,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[LongShortRatio]:
    """Get top trader long/short account ratio for CM Futures.
    
    Args:
        pair: Trading pair (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of long/short ratios
    """
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/topLongShortAccountRatio", params=locals())


async def get_global_long_short_account_ratio(
    *,
    pair: str,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[LongShortRatio]:
    """Get global long/short account ratio for CM Futures.
    
    Args:
        pair: Trading pair (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of long/short ratios
    """
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/globalLongShortAccountRatio", params=locals())


# ========== Taker Buy/Sell Volume ==========

TakerBuySellVolume = TypedDict("TakerBuySellVolume", {
    "pair": str,
    "contractType": ContractType,
    "takerBuyVol": str,
    "takerSellVol": str,
    "takerBuyVolValue": str,
    "takerSellVolValue": str,
    "timestamp": int
})


async def get_taker_buy_sell_volume(
    *,
    pair: str,
    contractType: ContractType,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[TakerBuySellVolume]:
    """Get taker buy/sell volume for CM Futures.
    
    Args:
        pair: Trading pair (required)
        contractType: Contract type (ALL, CURRENT_QUARTER, NEXT_QUARTER, PERPETUAL) (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of taker buy/sell volumes
    """
    contractType = contractType.value
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/takerBuySellVol", params=locals())


# ========== Basis ==========

BasisInfo = TypedDict("BasisInfo", {
    "pair": str,
    "contractType": ContractType,
    "futuresPrice": str,
    "indexPrice": str,
    "basis": str,
    "basisRate": str,
    "annualizedBasisRate": str,
    "timestamp": int
})


async def get_basis_info_list(
    *,
    pair: str,
    contractType: ContractType,
    period: str,
    limit: int = None,
    endTime: int = None,
    startTime: int = None
) -> list[BasisInfo]:
    """Get basis info list for CM Futures.
    
    Args:
        pair: Trading pair (required)
        contractType: Contract type (required)
        period: Period (5m,15m,30m,1h,2h,4h,6h,12h,1d) (required)
        limit: Limit (default 30, max 500)
        endTime: End time in ms
        startTime: Start time in ms
    
    Returns:
        List of basis information
    """
    contractType = contractType.value
    return await request(API_CM_FUTURES_ENDPOINT, FUTURES_DATA + "/basis", params=locals())


# ========== Index Price Constituents ==========


async def get_index_price_constituent_info(*, symbol: str) -> IndexPriceConstituents:
    """Get index price constituent info for CM Futures.
    
    Args:
        symbol: Trading symbol (required)
    
    Returns:
        Index price constituents
    """
    return await request(API_CM_FUTURES_ENDPOINT, DAPI_V1 + "/constituents", params=locals())
