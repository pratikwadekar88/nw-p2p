# transaction.py

import uuid

class Transaction:
    def __init__(self, sender_id, receiver_id, amount):
        self.txn_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.size = 1 * 1024  # Transaction size in bytes (1 KB)
