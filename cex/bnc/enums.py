from enum import Enum


class SymbolStatus(str, Enum):
    # Common
    TRADING = "TRADING"
    
    # Spot
    END_OF_DAY = "END_OF_DAY"
    HALT = "HALT" 
    BREAK = "BREAK"
    
    # Futures
    PENDING_TRADING = "PENDING_TRADING"
    PRE_DELIVERING = "PRE_DELIVERING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    PRE_SETTLE = "PRE_SETTLE"
    SETTLING = "SETTLING"
    CLOSE = "CLOSE"


class AcctSybPermission(str, Enum):
    SPOT = "SPOT"
    MARGIN = "MARGIN"
    LEVERAGED = "LEVERAGED"
    TRD_GRP_002 = "TRD_GRP_002"
    TRD_GRP_003 = "TRD_GRP_003"
    TRD_GRP_004 = "TRD_GRP_004"
    TRD_GRP_005 = "TRD_GRP_005"
    TRD_GRP_006 = "TRD_GRP_006"
    TRD_GRP_007 = "TRD_GRP_007"
    TRD_GRP_008 = "TRD_GRP_008"
    TRD_GRP_009 = "TRD_GRP_009"
    TRD_GRP_010 = "TRD_GRP_010"
    TRD_GRP_011 = "TRD_GRP_011"
    TRD_GRP_012 = "TRD_GRP_012"
    TRD_GRP_013 = "TRD_GRP_013"
    TRD_GRP_014 = "TRD_GRP_014"
    TRD_GRP_015 = "TRD_GRP_015"
    TRD_GRP_016 = "TRD_GRP_016"
    TRD_GRP_017 = "TRD_GRP_017"
    TRD_GRP_018 = "TRD_GRP_018"
    TRD_GRP_019 = "TRD_GRP_019"
    TRD_GRP_020 = "TRD_GRP_020"
    TRD_GRP_021 = "TRD_GRP_021"
    TRD_GRP_022 = "TRD_GRP_022"
    TRD_GRP_023 = "TRD_GRP_023"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PENDING_NEW = "PENDING_NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXPIRED_IN_MATCH = "EXPIRED_IN_MATCH"


class ListStatusType(str, Enum):
    RESPONSE = "RESPONSE"
    EXEC_STARTED = "EXEC_STARTED"
    UPDATED = "UPDATED"
    ALL_DONE = "ALL_DONE"


class ListOrderStatus(str, Enum):
    EXECUTING = "EXECUTING"
    ALL_DONE = "ALL_DONE"
    REJECT = "REJECT"


class ContingencyType(str, Enum):
    OCO = "OCO"
    OTO = "OTO"


class AllocationType(str, Enum):
    SOR = "SOR"


class OrderType(str, Enum):
    # Common
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"

    # Spot
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    LIMIT_MAKER = "LIMIT_MAKER"

    # Futures
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class NewOrderRespType(str, Enum):
    # Common
    ACK = "ACK"
    RESULT = "RESULT"

    # Spot
    FULL = "FULL"


class WorkingFloor(str, Enum):
    EXCHANGE = "EXCHANGE"
    SOR = "SOR"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class RateLimitType(str, Enum):
    REQUEST_WEIGHT = "REQUEST_WEIGHT"
    ORDERS = "ORDERS"
    RAW_REQUESTS = "RAW_REQUESTS"


class RateLimiterInterval(str, Enum):
    SECOND = "SECOND"
    MINUTE = "MINUTE"
    DAY = "DAY"


class STPMode(str, Enum):
    NONE = "NONE"
    EXPIRE_MAKER = "EXPIRE_MAKER"
    EXPIRE_TAKER = "EXPIRE_TAKER"
    EXPIRE_BOTH = "EXPIRE_BOTH"
    DECREMENT = "DECREMENT"


class KlineInterval(str, Enum):
    INTERVAL_1s = "1s"
    INTERVAL_1m = "1m"
    INTERVAL_3m = "3m"
    INTERVAL_5m = "5m"
    INTERVAL_15m = "15m"
    INTERVAL_30m = "30m"
    INTERVAL_1h = "1h"
    INTERVAL_2h = "2h"
    INTERVAL_4h = "4h"
    INTERVAL_6h = "6h"
    INTERVAL_8h = "8h"
    INTERVAL_12h = "12h"
    INTERVAL_1d = "1d"
    INTERVAL_3d = "3d"
    INTERVAL_1w = "1w"
    INTERVAL_1M = "1M"

    def milliseconds(self) -> int:
        intervals = {
            "1s": 1000,
            "1m": 60000,
            "3m": 180000,
            "5m": 300000,
            "15m": 900000,
            "30m": 1800000,
            "1h": 3600000,
            "2h": 7200000,
            "4h": 14400000,
            "6h": 21600000,
            "8h": 28800000,
            "12h": 43200000,
            "1d": 86400000,
            "3d": 259200000,
            "1w": 604800000
        }
        return intervals.get(self.value, 0)

    @classmethod
    def from_milliseconds(cls, ms: int) -> 'KlineInterval':
        intervals = {
            1000: cls.INTERVAL_1s,
            60000: cls.INTERVAL_1m,
            180000: cls.INTERVAL_3m,
            300000: cls.INTERVAL_5m,
            900000: cls.INTERVAL_15m,
            1800000: cls.INTERVAL_30m,
            3600000: cls.INTERVAL_1h,
            7200000: cls.INTERVAL_2h,
            14400000: cls.INTERVAL_4h,
            21600000: cls.INTERVAL_6h,
            28800000: cls.INTERVAL_8h,
            43200000: cls.INTERVAL_12h,
            86400000: cls.INTERVAL_1d,
            259200000: cls.INTERVAL_3d,
            604800000: cls.INTERVAL_1w
        }
        return intervals.get(ms)


class SymbolType(str, Enum):
    SPOT = "SPOT"
    FUTURE = "FUTURE"


class ContractType(str, Enum):
    PERPETUAL = "PERPETUAL"
    CURRENT_MONTH = "CURRENT_MONTH"
    NEXT_MONTH = "NEXT_MONTH"
    CURRENT_QUARTER = "CURRENT_QUARTER"
    NEXT_QUARTER = "NEXT_QUARTER"
    PERPETUAL_DELIVERING = "PERPETUAL_DELIVERING"


class ContractStatus(str, Enum):
    PENDING_TRADING = "PENDING_TRADING"
    TRADING = "TRADING"
    PRE_DELIVERING = "PRE_DELIVERING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    PRE_SETTLE = "PRE_SETTLE"
    SETTLING = "SETTLING"
    CLOSE = "CLOSE"


class PositionSide(str, Enum):
    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


class WorkingType(str, Enum):
    MARK_PRICE = "MARK_PRICE"
    CONTRACT_PRICE = "CONTRACT_PRICE"


class PriceMatch(str, Enum):
    NONE = "NONE"
    OPPONENT = "OPPONENT"
    OPPONENT_5 = "OPPONENT_5"
    OPPONENT_10 = "OPPONENT_10"
    OPPONENT_20 = "OPPONENT_20"
    QUEUE = "QUEUE"
    QUEUE_5 = "QUEUE_5"
    QUEUE_10 = "QUEUE_10"
    QUEUE_20 = "QUEUE_20"


class OrderExecutionType(str, Enum):
    NEW = "NEW"
    CANCELED = "CANCELED"
    REPLACED = "REPLACED"
    REJECTED = "REJECTED"
    TRADE = "TRADE"
    EXPIRED = "EXPIRED"
    TRADE_PREVENTION = "TRADE_PREVENTION"
