# REFER: https://docs.python.org/3/library/heapq.html
# REFER: https://www.geeksforgeeks.org/heap-queue-or-heapq-in-python/
import heapq
from typing import List, Tuple

from event import Event


class EventQueue:
    def __init__(self):
        # Tuple -> EventCompletionTime, Event
        self.events: List[Tuple[float, Event]] = list()
        self.add_new_events: bool = True

    def push(self, new_event: Event) -> None:
        if self.add_new_events == False:
            return
        heapq.heappush(self.events, (new_event.event_completion_time, new_event))

    def pop(self) -> Event:
        return heapq.heappop(self.events)[1]

    def top(self) -> Event:
        return self.events[0][1]

    def empty(self) -> bool:
        return len(self.events) == 0

    def freeze(self) -> None:
        self.add_new_events = False