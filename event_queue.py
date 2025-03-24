import heapq

class EventQueue:
    def __init__(self):
        self.eq = []

    def schedule_event(self, event):
        heapq.heappush(self.eq, event)

    def get_event(self):
        return heapq.heappop(self.eq)
