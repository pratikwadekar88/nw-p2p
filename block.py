import time
import random
from config import GENESIS_BLOCK_ID, COINBASE_REWARD

class Block:
    def __init__(self, prev_hash, miner_id, transactions=None):
        self.timestamp = time.time()
        self.prev_hash = prev_hash
        self.miner_id = miner_id
        self.transactions = transactions or []
        self.id = f"blk{int(self.timestamp*1000)}{random.randint(1000,9999)}"
        
    @property
    def size(self):
        return 1024 + len(self.transactions) * 1024  # 1KB base + 1KB per tx

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis()]
        self.utxo = {}
        self.tree = {GENESIS_BLOCK_ID: []}

    def create_genesis(self):
        genesis = Block("0", "system")
        genesis.id = GENESIS_BLOCK_ID
        return genesis

    def add_block(self, block):
        if self.validate_block(block):
            self.chain.append(block)
            self.tree.setdefault(block.prev_hash, []).append(block)
            self.update_utxo(block)
            return True
        return False

    def validate_block(self, block):
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
        for tx in block.transactions:
            self.utxo[tx.sender] = self.utxo.get(tx.sender, 0) - tx.amount
            self.utxo[tx.receiver] = self.utxo.get(tx.receiver, 0) + tx.amount
        self.utxo[block.miner_id] = self.utxo.get(block.miner_id, 0) + COINBASE_REWARD

    def resolve_forks(self):
        longest = []
        for branch in self._get_branches():
            if len(branch) > len(longest) and self._validate_chain(branch):
                longest = branch
        self.chain = longest

    def _get_branches(self):
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
        # Implementation omitted for brevity
        return True