from ast import TypeVar
from dataclasses import dataclass
from time import time_ns
from typing import Generic
from ..cex_name import CexName
from ..symbol import SymbolType
from copy import deepcopy

@dataclass(frozen=True)
class PQ:
    p: float = None
    q: float = None

    def price(self) -> float:
        if self.p is None:
            raise ValueError("Price is not set")
        return self.p

    def qty(self) -> float:
        if self.q is None:
            raise ValueError("Quantity is not set")
        return self.q
    

ObNote = TypeVar("ObNote")


@dataclass
class Orderbook(Generic[ObNote]):
    cex: CexName
    type: SymbolType
    symbol: str
    version: str

    # Time is the cex event time
    time: int
    # UpdateTime is the time of the latest data update in nanoseconds
    update_time: int
    
    asks: list[PQ]
    bids: list[PQ]
    
    # Note is the note of the data
    note: ObNote = None
    
    error: Exception = None
    
    def copy(self) -> 'Orderbook[ObNote]':
        """Returns a deep copy of the orderbook."""
        return deepcopy(self)

    def empty(self) -> bool:
        """Returns True if the orderbook has no asks and bids."""
        return len(self.asks) == 0 and len(self.bids) == 0

    def set_error(self, err: Exception) -> None:
        """Sets an error on the orderbook and clears the books."""
        self.asks = []
        self.bids = []
        self.error = err
        self.update_time = time_ns()

    def set_book(self, is_ask: bool, book: list[PQ], version: str) -> None:
        """Sets either ask or bid book."""
        if is_ask:
            self.set_ask_book(book, version)
        else:
            self.set_bid_book(book, version)

    def set_ask_book(self, ask_book: list[PQ], version: str) -> None:
        """Sets the ask book."""
        self.asks = ask_book
        self.version = version
        self.update_time = time_ns()

    def set_bid_book(self, bid_book: list[PQ], version: str) -> None:
        """Sets the bid book."""
        self.bids = bid_book
        self.version = version
        self.update_time = time_ns()

    def update_deltas(self, is_ask: bool, delta: list[PQ], version: str) -> None:
        """Updates either ask or bid deltas."""
        if is_ask:
            self.update_ask_deltas(delta, version)
        else:
            self.update_bid_deltas(delta, version)

    def update_ask_deltas(self, delta: list[PQ], version: str) -> None:
        """Updates ask deltas."""
        self._update_deltas(delta, True, version)

    def update_bid_deltas(self, delta: list[PQ], version: str) -> None:
        """Updates bid deltas."""
        self._update_deltas(delta, False, version)

    def _update_deltas(self, new_data: list[PQ], is_ask: bool, version: str) -> None:
        """Internal method to update deltas."""
        for pq in new_data:
            price = pq.price()
            qty = pq.qty()
            
            if price == 0:
                continue
                
            if price < 0:
                raise ValueError(f"cex: ob price {price} < 0")
                
            if qty < 0:
                raise ValueError(f"cex: ob qty {qty} < 0")

            book = self.asks if is_ask else self.bids
            book = update_one_book_delta(price, qty, book, is_ask)
            
            if is_ask:
                self.asks = book
            else:
                self.bids = book

        self.version = version
        self.update_time = time_ns()

    def __str__(self) -> str:
        """Returns string representation of the orderbook."""
        return f"ob-{self.cex}-{self.type}-{self.symbol}"
    

def update_one_book_delta(price: float, qty: float, old_book: list[PQ], is_ask: bool) -> list[PQ]:
    """Updates a single price level in the orderbook.
    
    Args:
        price: The price level to update
        qty: The new quantity (0 to remove the level)
        old_book: The list of price/quantity pairs to update
        is_ask: True if updating asks, False if updating bids
        
    Returns:
        Updated list of price/quantity pairs
    """
    updated = False
    
    for i, pq in enumerate(old_book):
        old_price = pq.price()
        if price == old_price:
            if qty > 0:
                old_book[i] = PQ(p=price, q=qty)
            else:
                old_book = old_book[:i] + old_book[i+1:]
            updated = True
            break
            
        if (is_ask and price < old_price) or (not is_ask and price > old_price):
            if qty > 0:
                new_pq = PQ(p=price, q=qty)
                old_book = old_book[:i] + [new_pq] + old_book[i:]
            updated = True
            break
            
    if not updated and qty > 0:
        old_book.append(PQ(p=price, q=qty))
        
    return old_book

