from block import Block
from config import BLOCK_INTERVAL

def proof_of_work(peer):
    return Block(
        prev_hash=peer.blockchain.chain[-1].id,
        miner_id=peer.id,
        transactions=peer.select_transactions()
    )