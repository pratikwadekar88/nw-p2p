# transaction.py

import uuid

class Transaction:
    """
    Represents a transaction in the network.

    Attributes:
        txn_id (str): Unique identifier for the transaction.
        sender_id (str): ID of the sender.
        receiver_id (str): ID of the receiver.
        amount (float): Amount to be transferred.
        size (int): Size of the transaction in bytes.
    """
    def __init__(self, sender_id, receiver_id, amount):
        """
        Initializes a new transaction.

        Args:
            sender_id (str): ID of the sender.
            receiver_id (str): ID of the receiver.
            amount (float): Amount to be transferred.
        """
        self.txn_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.size = 1 * 1024  # Transaction size in bytes (1 KB)
