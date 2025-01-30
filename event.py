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
        """Add an event to the queue."""
        heapq.heappush(self.queue, (event.timestamp, event))
        # print(f"[DEBUG] Scheduled event {event.event_type} at time {event.timestamp}") 
    def next_event(self):
        """Get the next event from the queue."""
        # print(f"[DEBUG] Executing event {event.event_type} at time {event.timestamp}")
        return heapq.heappop(self.queue)[1] if self.queue else None
    
    def peek_time(self):
        """Get the timestamp of the next event."""
        return self.queue[0][0] if self.queue else float('inf')