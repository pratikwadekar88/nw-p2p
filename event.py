from enum import Enum

class EventType(Enum):
    GENERATE_TRANSACTION = 1
    RECEIVE_TRANSACTION = 2
    BLOCK_MINED = 3
    RECEIVE_BLOCK = 4
    RECEIVE_BLOCK_HASH = 5
    GET_BLOCK_REQUEST = 6
    GET_BLOCK_RESPONSE = 7
    RINGMASTER_BROADCAST = 8  # NEW event type for strategic release

class Event:
    def __init__(self, time, event_type, peer_id, **kwargs):
        self.time = time
        self.event_type = event_type
        self.peer_id = peer_id
        self.kwargs = kwargs

    def __lt__(self, other):
        return self.time < other.time
