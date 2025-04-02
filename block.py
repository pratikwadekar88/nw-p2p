import uuid

class Block:
    def __init__(self, miner_id, prev_block_id, transactions, timestamp, is_malicious=False):
        """
        Initialize a new Block instance.

        Args:
            miner_id (str): The ID of the miner who mined the block.
            prev_block_id (str): The ID of the previous block in the chain.
            transactions (list): A list of Transaction objects included in the block.
            timestamp (int): The timestamp when the block was created.
            is_malicious (bool): Flag indicating if the block is malicious.
        """
        self.block_id = str(uuid.uuid4())
        self.miner_id = miner_id
        self.prev_block_id = prev_block_id
        self.transactions = transactions  # List of Transaction objects
        self.timestamp = timestamp
        self.size = self.calculate_size()
        # New flag: whether the block is malicious or honest.
        self.is_malicious = is_malicious

    def calculate_size(self):
        """
        Calculate the size of the block.

        Returns:
            int: The size of the block in bytes.
        """
        transaction_sizes = sum(txn.size for txn in self.transactions)
        return transaction_sizes + (1 * 1024)  # Adding 1 KB for block header
    
    def calculate_txn_amount(self):
        """
        Calculate the total amount of all transactions in the block.

        Returns:
            float: The total amount of all transactions.
        """
        return sum(txn.amount for txn in self.transactions)
    
    def compute_hash(self):
        """
        Compute the hash of the block header fields.
        (Assumed to be implemented as needed.)
        """
        # For demonstration, we use a dummy hash.
        # In a real system, you would hash the header fields.
        import hashlib
        header = f"{self.miner_id}{self.prev_block_id}{self.timestamp}{self.is_malicious}"
        return hashlib.sha256(header.encode()).hexdigest()
