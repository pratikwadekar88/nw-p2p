# block.py
import uuid

class Block:
    def __init__(self, miner_id, prev_block_id, transactions, timestamp):
        """
        Initialize a new Block instance.
        """
        self.block_id = str(uuid.uuid4())
        self.miner_id = miner_id
        self.prev_block_id = prev_block_id
        self.transactions = transactions  # List of Transaction objects
        self.timestamp = timestamp
        self.size = self.calculate_size()

    def calculate_size(self):
        """
        Calculate the size of the block.
        """
        transaction_sizes = sum(txn.size for txn in self.transactions)
        return transaction_sizes + (1 * 1024)  # Adding 1 KB for block header
    
    def calculate_txn_amount(self):
        """
        Calculate the total amount of all transactions in the block.
        """
        return sum(txn.amount for txn in self.transactions)
