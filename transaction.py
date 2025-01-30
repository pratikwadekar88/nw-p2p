import time
import random

class Transaction:
    """Represents a cryptocurrency transaction."""
    def __init__(self, sender, receiver, amount):
        self.sender = sender  # Sender's peer ID
        self.receiver = receiver  # Receiver's peer ID
        self.amount = amount  # Amount of coins
        self.id = f"tx{int(time.time()*1000)}{random.randint(1000,9999)}"  # Unique ID
        self.size = 1024  # 1 KB transaction size

    def to_dict(self):
        """Convert transaction to dictionary for serialization."""
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount
        }