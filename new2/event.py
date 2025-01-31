# event.py

from enum import Enum

class EventType(Enum):
    GENERATE_TRANSACTION = 1
    RECEIVE_TRANSACTION = 2
    START_MINING = 3
    BLOCK_MINED = 4
    RECEIVE_BLOCK = 5

class Event:
    def __init__(self, time, event_type, peer_id, **kwargs):
        self.time = time
        self.event_type = event_type
        self.peer_id = peer_id
        self.kwargs = kwargs

    def __lt__(self, other):
        return self.time < other.time
