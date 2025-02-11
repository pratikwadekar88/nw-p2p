from enum import Enum


class EventType(Enum):
    GENERATE_TRANSACTION = 1
    RECEIVE_TRANSACTION = 2
    START_MINING = 3
    BLOCK_MINED = 4
    RECEIVE_BLOCK = 5


class Event:
    def __init__(self, time, event_type, peer_id, **kwargs):
        """
        Initializes an Event instance.

        Parameters:
        time (float): The time at which the event occurs.
        event_type (EventType): The type of the event.
        peer_id (int): The ID of the peer associated with the event.
        **kwargs: Additional keyword arguments for event-specific data.

        Returns:
        None
        """
        self.time = time
        self.event_type = event_type
        self.peer_id = peer_id
        self.kwargs = kwargs

    def __lt__(self, other):
        """
        Compares this event with another event based on time.

        Parameters:
        other (Event): The other event to compare with.

        Returns:
        bool: True if this event occurs before other event, False otherwise.
        """
        return self.time < other.time
