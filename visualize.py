import matplotlib.pyplot as plt
import networkx as nx

def plot_blockchain(peer: Peer):
    G = nx.DiGraph()
    for block in peer.blockchain.chain:
        G.add_node(block.id)
        if block.prev_hash != "0":
            G.add_edge(block.prev_hash, block.id)
    
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=700)
    plt.show()

def plot_mining_distribution(peers):
    high_cpu = [p for p in peers if not p.is_low_cpu]
    low_cpu = [p for p in peers if p.is_low_cpu]
    
    plt.bar(["High CPU", "Low CPU"], [len(high_cpu), len(low_cpu)])
    plt.title("Mining Power Distribution")
    plt.show()