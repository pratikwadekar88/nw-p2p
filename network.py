# network.py
import networkx as nx
import random
def create_network(peers):
    """Create connected graph with 3-6 neighbors per peer"""
    while True:
        # Randomly choose degree between 3-6
        degree = random.randint(3, 6)
        G = nx.random_regular_graph(degree, len(peers))
        if nx.is_connected(G):
            break
            
    for i, j in G.edges():
        peers[i].add_neighbor(peers[j])
        peers[j].add_neighbor(peers[i])
    return G