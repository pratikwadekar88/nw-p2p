import time
import random
from config import GENESIS_BLOCK_ID, COINBASE_REWARD, MAX_BLOCK_SIZE_BYTES

class Block:
    """Represents a block in the blockchain."""
    def __init__(self, prev_hash, miner_id, transactions=None):
        self.timestamp = time.time()  # Block creation time
        self.prev_hash = prev_hash  # Hash of the previous block
        self.miner_id = miner_id  # ID of the miner
        self.transactions = transactions or []  # List of transactions
        self.id = f"blk{int(self.timestamp*1000)}{random.randint(1000,9999)}"  # Unique ID
        
    @property
    def size(self):
        """Calculate block size in bytes."""
        return 1024 + len(self.transactions) * 1024  # 1KB base + 1KB per tx

class Blockchain:
    """Manages the blockchain for a peer."""
    def __init__(self):
        self.chain = [self.create_genesis()]  # Start with genesis block
        self.utxo = {}  # Unspent Transaction Outputs
        self.tree = {GENESIS_BLOCK_ID: []}  # Tree structure for forks

    def create_genesis(self):
        """Create the genesis block."""
        genesis = Block("0", "system")
        genesis.id = GENESIS_BLOCK_ID
        return genesis


    def add_block(self, block):
        if self.validate_block(block):
            self.chain.append(block)
            self.tree.setdefault(block.prev_hash, []).append(block)
            self.update_utxo(block)
            self.resolve_forks()  # Resolve forks after adding block
            return True
        return False

    def validate_block(self, block):
        """Validate a block's transactions and size."""
        # Check transactions
        temp_utxo = self.utxo.copy()
        for tx in block.transactions:
            if temp_utxo.get(tx.sender, 0) < tx.amount:
                return False
            temp_utxo[tx.sender] -= tx.amount
            temp_utxo[tx.receiver] = temp_utxo.get(tx.receiver, 0) + tx.amount
        
        # Check size
        if block.size > MAX_BLOCK_SIZE_BYTES:
            return False
            
        return True

    def update_utxo(self, block):
        # Process transactions
        for tx in block.transactions:
            self.utxo[tx.sender] = self.utxo.get(tx.sender, 0) - tx.amount
            self.utxo[tx.receiver] = self.utxo.get(tx.receiver, 0) + tx.amount

       # Add mining reward (coinbase transaction)
        self.utxo[block.miner_id] = self.utxo.get(block.miner_id, 0) + COINBASE_REWARD

    def resolve_forks(self):
        """Resolve forks by selecting the longest valid chain."""
        longest_chain = []
        for branch in self._get_branches():
            if len(branch) > len(longest_chain) and self._validate_chain(branch):
                longest_chain = branch
        self.chain = longest_chain

    def _get_branches(self):
        """Get all possible branches in the blockchain tree."""
        branches = []
        stack = [(self.chain[0], [self.chain[0]])]
        while stack:
            current, path = stack.pop()
            children = self.tree.get(current.id, [])
            if not children:
                branches.append(path)
            for child in children:
                stack.append((child, path + [child]))
        return branches

    def _validate_chain(self, chain):
        """Validate a chain by checking all blocks."""
        # Implementation omitted for brevity
        return True
    
    def validate_transaction(self, tx):
        """Validate a transaction against the current UTXO set."""
        return self.utxo.get(tx.sender, 0) >= tx.amount