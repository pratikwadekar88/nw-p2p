import networkx as nx

def create_network(peers):
    while True:
        G = nx.random_regular_graph(3, len(peers))
        if nx.is_connected(G):
            break
            
    for i, j in G.edges():
        peers[i].add_neighbor(peers[j])
        peers[j].add_neighbor(peers[i])
        print(f"[DEBUG] Connected Peer {peers[i].id} to Peer {peers[j].id}")
    
    return G