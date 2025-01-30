import matplotlib.pyplot as plt
import networkx as nx

def plot_blockchain(peer):
    """Visualize the blockchain tree for a peer."""
    G = nx.DiGraph()
    for block in peer.blockchain.chain:
        G.add_node(block.id)
        if block.prev_hash != "0":
            G.add_edge(block.prev_hash, block.id)
    
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=700)
    plt.title(f"Blockchain for {peer.id}")
    plt.show()

def plot_mining_distribution(peers):
    """Visualize the distribution of mined blocks."""
    miners = {}
    for peer in peers:
        for block in peer.blockchain.chain[1:]:  # Skip genesis
            miners[block.miner_id] = miners.get(block.miner_id, 0) + 1
    
    plt.bar(miners.keys(), miners.values())
    plt.title("Mining Distribution")
    plt.xticks(rotation=45)
    plt.show()