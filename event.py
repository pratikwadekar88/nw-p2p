import heapq

class Event:
    def __init__(self, timestamp, event_type, callback, data=None):
        self.timestamp = timestamp
        self.event_type = event_type
        self.callback = callback
        self.data = data

    def __lt__(self, other):
        return self.timestamp < other.timestamp

class EventQueue:
    def __init__(self):
        self.queue = []
    
    def schedule(self, event):
        heapq.heappush(self.queue, (event.timestamp, event))
    
    def next_event(self):
        return heapq.heappop(self.queue)[1] if self.queue else None
    
    def peek_time(self):
        return self.queue[0][0] if self.queue else float('inf')