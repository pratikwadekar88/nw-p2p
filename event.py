import heapq

class Event:
    """Represents a simulation event with a timestamp and callback."""
    def __init__(self, timestamp, event_type, callback, data=None):
        self.timestamp = timestamp  # When the event occurs
        self.event_type = event_type  # Type of event (e.g., "tx_propagate")
        self.callback = callback  # Function to call when event occurs
        self.data = data  # Additional data for the event

    def __lt__(self, other):
        """Compare events by timestamp for priority queue."""
        return self.timestamp < other.timestamp

class EventQueue:
    """Priority queue for managing simulation events."""
    def __init__(self):
        self.queue = []  # Min-heap for events
    
    def schedule(self, event):
        heapq.heappush(self.queue, (event.timestamp, event))
        
    def next_event(self):
        if not self.queue:
            return None
        _, event = heapq.heappop(self.queue)
        return event
    
    def peek_time(self):
        """Get the timestamp of the next event."""
        return self.queue[0][0] if self.queue else float('inf')