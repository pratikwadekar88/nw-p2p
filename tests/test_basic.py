import pytest
from block import Blockchain, Block
from transaction import Transaction

def test_utxo_validation():
    blockchain = Blockchain()
    tx = Transaction("A", "B", 100)
    
    # Test valid transaction
    blockchain.utxo = {"A": 100}
    assert blockchain.validate_transaction(tx)
    
    # Test invalid transaction
    blockchain.utxo = {"A": 99}
    assert not blockchain.validate_transaction(tx)

def test_fork_resolution():
    blockchain = Blockchain()
    block1 = Block(blockchain.chain[-1].id, "miner1")
    block2a = Block(block1.id, "miner2")
    block2b = Block(block1.id, "miner3")
    
    blockchain.tree = {
        blockchain.chain[0].id: [block1],
        block1.id: [block2a, block2b]
    }
    
    blockchain.resolve_forks()
    assert len(blockchain.chain) == 3  # genesis + block1 + longest child