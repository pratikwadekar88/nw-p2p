# visualize.py
import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from matplotlib.patches import FancyArrowPatch

class Visualizer:
    def __init__(self, peers):
        self.peers = peers

    def visualize_blockchain(self, peer_id):
        """
        Visualizes the blockchain of a specific peer.
        Blocks are colored based on miner type: Genesis (yellow), honest (lightblue), malicious (red).
        """
        peer = self.peers[peer_id]
        if not peer.blockchain:
            print(f"Peer {peer_id} has no blocks.")
            return
        G = nx.DiGraph()
        for block in peer.blockchain.values():
            block_id = block.block_id[:6]
            prev_block_id = block.prev_block_id[:6] if block.prev_block_id else None
            timestamp = f"{block.timestamp:.3f}"
            if block.miner_id == "Satoshi":
                miner_type = "genesis"
            elif block.miner_id in self.peers and self.peers[block.miner_id].is_malicious:
                miner_type = "malicious"
            else:
                miner_type = "honest"
            G.add_node(block_id, miner=block.miner_id, time=timestamp, txns=len(block.transactions), miner_type=miner_type)
            if prev_block_id:
                G.add_edge(prev_block_id, block_id)
        main_chain_blocks = [block.block_id[:6] for block in peer.current_longest_chain]
        genesis_block_id = None
        for node in G.nodes():
            if len(list(G.predecessors(node))) == 0:
                genesis_block_id = node
                break
        if genesis_block_id and genesis_block_id not in main_chain_blocks:
            main_chain_blocks.insert(0, genesis_block_id)
        pos = {}
        layer_spacing = 2
        vertical_offset = 2
        for idx, block_id in enumerate(main_chain_blocks):
            pos[block_id] = (idx * layer_spacing, 0)
        def position_forks(block_id, parent_pos, used_positions=set()):
            successors = list(G.successors(block_id))
            forks = [s for s in successors if s not in main_chain_blocks]
            for idx, fork_id in enumerate(forks):
                if fork_id not in pos:
                    y_new = parent_pos[1] - vertical_offset * (idx + 1)
                    x_new = parent_pos[0] + layer_spacing
                    while (x_new, y_new) in used_positions:
                        y_new -= vertical_offset
                    pos[fork_id] = (x_new, y_new)
                    used_positions.add((x_new, y_new))
                    position_forks(fork_id, pos[fork_id], used_positions)
            for successor in successors:
                if successor in main_chain_blocks and successor != block_id:
                    position_forks(successor, pos[successor], used_positions)
        used_positions = set(pos.values())
        for block_id in main_chain_blocks:
            position_forks(block_id, pos[block_id], used_positions)
        for block_id in G.nodes():
            if block_id not in pos:
                pos[block_id] = (0, 0)
        node_labels = {}
        for node_id in G.nodes():
            data = G.nodes[node_id]
            label = f"ID: {node_id}\nMiner: {data['miner']}\nTime: {data['time']}\nTxns: {data['txns']}"
            node_labels[node_id] = label
        node_colors = []
        for node_id in G.nodes():
            data = G.nodes[node_id]
            if data['miner_type'] == "genesis":
                node_colors.append('yellow')
            elif data['miner_type'] == "malicious":
                node_colors.append('red')
            else:
                node_colors.append('lightblue')
        num_blocks = len(main_chain_blocks)
        fig_width = max(14, num_blocks * (layer_spacing * 1.5))
        fig_height = 10
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_shape='s', node_size=5000, ax=ax)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, verticalalignment='center', ax=ax)
        for (start, end) in G.edges():
            start_pos = pos[start]
            end_pos = pos[end]
            arrow = FancyArrowPatch(start_pos, end_pos, arrowstyle='-|>', color='black',
                                    mutation_scale=20, shrinkA=0, shrinkB=10, connectionstyle='arc3,rad=0.0', lw=2)
            ax.add_patch(arrow)
        ax.set_title(f'Blockchain Tree for Peer {peer_id}')
        ax.axis('off')
        legend_elements = [
            mpatches.Patch(color='yellow', label='Genesis Block'),
            mpatches.Patch(color='lightblue', label='Honest Block'),
            mpatches.Patch(color='red', label='Malicious Block')
        ]
        ax.legend(handles=legend_elements, loc='lower left')
        save_directory = 'simOut/blockChainTrees'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, f'Peer_{peer_id}.pdf')
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        print(f'Blockchain plot saved to {save_path}')

    def visualize_network_topology(self):
        """
        Visualizes the overall network topology.
        """
        G = nx.Graph()
        for peer_id, peer in self.peers.items():
            G.add_node(peer_id, is_malicious=peer.is_malicious)
        for peer_id, peer in self.peers.items():
            for neighbor_id in peer.connections:
                G.add_edge(peer_id, neighbor_id)
        node_colors = []
        for node in G.nodes(data=True):
            if node[1]['is_malicious']:
                node_colors.append('red')
            else:
                node_colors.append('blue')
        plt.figure(figsize=(12,8))
        pos = nx.spring_layout(G, k=0.3)
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=500, font_size=8)
        plt.title('Network Topology of Peers')
        plt.axis('off')
        save_directory = 'simOut'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, 'PeerNetwork.png')
        plt.savefig(save_path)
        plt.close()
        print(f'Network topology plot saved to {save_path}')

    # def visualize_overlay_network(self, network):
    #     """
    #     Visualizes the malicious overlay network.
    #     Overlay connections are defined by the extra low propagation delays between malicious nodes.
    #     (Edges with a prop_delay between 0.001 and 0.01 seconds are assumed to be part of the overlay.)
    #     """
    #     G = nx.Graph()
    #     # Collect malicious nodes.
    #     malicious_ids = [pid for pid, p in self.peers.items() if p.is_malicious]
    #     for pid in malicious_ids:
    #         G.add_node(pid)
    #     # Add overlay edges based on latency entries.
    #     overlay_edges = []
    #     for i in range(len(malicious_ids)):
    #         for j in range(i+1, len(malicious_ids)):
    #             pid = malicious_ids[i]
    #             other = malicious_ids[j]
    #             key = (pid, other)
    #             if key in network.latencies:
    #                 delay = network.latencies[key]['prop_delay']
    #                 if 0.001 <= delay <= 0.01:
    #                     overlay_edges.append((pid, other))
    #     G.add_edges_from(overlay_edges)
    #     plt.figure(figsize=(8,6))
    #     pos = nx.spring_layout(G, k=0.5)
    #     nx.draw(G, pos, with_labels=True, node_color='red', node_size=700, font_size=10)
    #     plt.title('Malicious Overlay Network')
    #     plt.axis('off')
    #     save_directory = 'simOut'
    #     os.makedirs(save_directory, exist_ok=True)
    #     save_path = os.path.join(save_directory, 'OverlayNetwork.png')
    #     plt.savefig(save_path)
    #     plt.close()
    #     print(f'Overlay network plot saved to {save_path}')
    def visualize_overlay_network(self, network):
        """
        Visualizes the malicious overlay network.
        Overlay connections are defined by the low propagation delays (1ms to 10ms) in the overlay network.
        """
        G = nx.Graph()
        # Collect malicious node IDs.
        malicious_ids = [pid for pid, p in self.peers.items() if p.is_malicious]
        for pid in malicious_ids:
            G.add_node(pid)
        # Add overlay edges from the overlay_network dictionary in the network instance.
        for pid, overlay_peers in network.overlay_network.items():
            for other in overlay_peers:
                G.add_edge(pid, other)
        plt.figure(figsize=(8,6))
        pos = nx.spring_layout(G, k=0.5)
        nx.draw(G, pos, with_labels=True, node_color='red', node_size=700, font_size=10)
        plt.title('Malicious Overlay Network')
        plt.axis('off')
        save_directory = 'simOut'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, 'OverlayNetwork.png')
        plt.savefig(save_path)
        plt.close()
        print(f'Overlay network plot saved to {save_path}')

    def compare_peer_blockchains(self):
        """
        Compares the blockchains of all peers and generates a table.
        """
        data = []
        for peer_id, peer in self.peers.items():
            longest_chain_length = len(peer.current_longest_chain)
            numBlocksByPeerInLC = sum(1 for block in peer.current_longest_chain if block.miner_id == peer_id)
            numBlocksByPeer = sum(1 for block in peer.blockchain.values() if block.miner_id == peer_id)
            ratio = (numBlocksByPeerInLC / numBlocksByPeer) if numBlocksByPeer > 0 else 0
            ratio_blocks_in_longest_chain = f"{ratio:.5f}"
            data.append([peer_id, longest_chain_length, numBlocksByPeerInLC, numBlocksByPeer, ratio_blocks_in_longest_chain])
        df = pd.DataFrame(data, columns=[
            'Peer ID',
            'LC Length',
            'Blocks in LC by Peer',
            'Total Blocks by Peer',
            'Ratio (Blocks in LC/Total Blocks)'
        ])
        fig, ax = plt.subplots(figsize=(12,8))
        ax.axis('tight')
        ax.axis('off')
        table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_facecolor('yellow')
                cell.set_text_props(weight='bold', color='black')
            elif i % 2 == 0:
                cell.set_facecolor('#f2f2f2')
            else:
                cell.set_facecolor('white')
            cell.set_edgecolor('black')
        save_path = os.path.join('simOut', 'peerBlockchainsTable.png')
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f'Blockchain comparison table saved to {save_path}')
