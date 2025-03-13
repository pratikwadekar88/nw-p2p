# transaction.py
import uuid
from config import TRANSACTION_SIZE
class Transaction:
    def __init__(self, sender_id, receiver_id, amount):
        self.txn_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.size = TRANSACTION_SIZE  # in bytes
