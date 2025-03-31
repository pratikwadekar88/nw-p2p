# block.py
import uuid
from config import EMPTY_BLOCK_SIZE  # Add this import

class Block:
    def __init__(self, miner_id, prev_block_id, transactions, timestamp):
        """
        Initialize a new Block instance.

        Args:
            miner_id (str): The ID of the miner who mined the block.
            prev_block_id (str): The ID of the previous block in the chain.
            transactions (list): A list of Transaction objects included in the block.
            timestamp (int): The timestamp when the block was created.
        """
        self.block_id = str(uuid.uuid4())
        self.miner_id = miner_id
        self.prev_block_id = prev_block_id
        self.transactions = transactions  # List of Transaction objects
        self.timestamp = timestamp
        self.size = self.calculate_size()
        self.is_malicious = False

    def calculate_size(self):
        """
        Calculate the size of the block.

        Returns:
            int: The size of the block in bytes.
        """
        transaction_sizes = sum(txn.size for txn in self.transactions)
        return transaction_sizes + EMPTY_BLOCK_SIZE  # Add header size
    
    def calculate_txn_amount(self):
        """
        Calculate the total amount of all transactions in the block.

        Returns:
            float: The total amount of all transactions.
        """
        return sum(txn.amount for txn in self.transactions)
