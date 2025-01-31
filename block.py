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
    def __init__(self):
        self.chain = [self.create_genesis()]
        self.tree = {GENESIS_BLOCK_ID: []}
        self.longest_chain = [GENESIS_BLOCK_ID]
        self.utxo = {GENESIS_BLOCK_ID: INITIAL_COINS}
        self.block_times = {}

    def add_block(self, block):
        if self.validate_block(block):
            self.tree.setdefault(block.prev_hash, []).append(block)
            self.block_times[block.id] = current_time
            self.resolve_forks()
            return True
        return False

    def resolve_forks(self):
        max_length = len(self.longest_chain)
        for branch in self._get_branches():
            if len(branch) > max_length and self._validate_chain(branch):
                self.longest_chain = [b.id for b in branch]
                self.utxo = self._compute_utxo(branch)
                max_length = len(branch)

    def _compute_utxo(self, chain):
        utxo = {GENESIS_BLOCK_ID: INITIAL_COINS}
        for block in chain[1:]:
            for tx in block.transactions:
                utxo[tx.sender] = utxo.get(tx.sender, 0) - tx.amount
                utxo[tx.receiver] = utxo.get(tx.receiver, 0) + tx.amount
            utxo[block.miner_id] = utxo.get(block.miner_id, 0) + COINBASE_REWARD
        return utxo
