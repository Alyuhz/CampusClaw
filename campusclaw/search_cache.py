from __future__ import annotations

import copy
import threading
import time
from collections import OrderedDict


class SearchCache:
    def __init__(self, limit: int = 256, ttl: float = 30):
        self.limit, self.ttl = limit, ttl
        self.lock = threading.Lock()
        self.entries: OrderedDict[tuple, tuple[float, list]] = OrderedDict()

    def get(self, key: tuple) -> list | None:
        with self.lock:
            value = self.entries.get(key)
            if value is None:
                return None
            if time.monotonic() - value[0] >= self.ttl:
                del self.entries[key]
                return None
            self.entries.move_to_end(key)
            return copy.deepcopy(value[1])

    def put(self, key: tuple, value: list) -> None:
        with self.lock:
            self.entries[key] = (time.monotonic(), copy.deepcopy(value))
            self.entries.move_to_end(key)
            while len(self.entries) > self.limit:
                self.entries.popitem(last=False)
