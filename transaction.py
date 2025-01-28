import time
import random

class Transaction:
    def __init__(self, sender, receiver, amount):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.id = f"tx{int(time.time()*1000)}{random.randint(1000,9999)}"
        self.size = 1024  # 1 KB

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount
        }