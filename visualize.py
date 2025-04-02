import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from networkx.drawing.nx_agraph import graphviz_layout

class Visualizer:
    def __init__(self, peers):
        self.peers = peers

    def visualize_blockchain(self, peer_id):
        """
        Visualizes the blockchain of a specific peer.
    
        Parameters:
            peer_id (int or str): The ID of the peer whose blockchain is to be visualized.
    
        Returns:
            None
        """
        peer = self.peers[peer_id]
        if not peer.blockchain:
            print(f"Peer {peer_id} has no blocks in their blockchain.")
            return
    
        G = nx.DiGraph()
    
        # Add nodes and edges for each block in the peer's blockchain.
        for block in peer.blockchain.values():
            block_id = block.block_id[:6]
            prev_block_id = block.prev_block_id[:6] if block.prev_block_id else None
            # Format timestamp to 3 decimal places.
            timestamp = f"{block.timestamp:.3f}"
            # Save block attributes, including malicious flag.
            G.add_node(
                block_id,
                miner=block.miner_id,
                time=timestamp,
                transactions=len(block.transactions),
                is_malicious=block.is_malicious
            )
            if prev_block_id:
                G.add_edge(prev_block_id, block_id)
    
        # Identify the main chain (the longest valid chain), ensuring genesis is included.
        main_chain_blocks = [block.block_id[:6] for block in peer.current_longest_chain]
        genesis_block_id = None
        for node in G.nodes():
            if len(list(G.predecessors(node))) == 0:
                genesis_block_id = node
                break
        if genesis_block_id and genesis_block_id not in main_chain_blocks:
            main_chain_blocks.insert(0, genesis_block_id)
    
        # Position nodes: main chain in a straight horizontal line.
        pos = {}
        layer_spacing = 2  # Horizontal spacing between blocks.
        vertical_offset = 2  # Vertical offset for forks.
    
        for idx, block_id in enumerate(main_chain_blocks):
            pos[block_id] = (idx * layer_spacing, 0)
    
        # Function to recursively position forked blocks.
        def position_forks(block_id, parent_pos, used_positions):
            successors = list(G.successors(block_id))
            forks = [s for s in successors if s not in main_chain_blocks]
            for idx, fork_id in enumerate(forks):
                if fork_id not in pos:
                    y_new = parent_pos[1] - vertical_offset * (idx + 1)
                    x_new = parent_pos[0] + layer_spacing
                    # Ensure the position is unique.
                    while (x_new, y_new) in used_positions:
                        y_new -= vertical_offset
                    pos[fork_id] = (x_new, y_new)
                    used_positions.add((x_new, y_new))
                    position_forks(fork_id, pos[fork_id], used_positions)
            # Also ensure that any successor that is in the main chain has its forks positioned.
            for successor in successors:
                if successor in main_chain_blocks:
                    position_forks(successor, pos[successor], used_positions)
    
        used_positions = set(pos.values())
        for block_id in main_chain_blocks:
            position_forks(block_id, pos[block_id], used_positions)
    
        # For any remaining nodes, assign a default position.
        for block_id in G.nodes():
            if block_id not in pos:
                pos[block_id] = (0, 0)
    
        # Prepare node labels with block details.
        node_labels = {}
        for node_id in G.nodes():
            data = G.nodes[node_id]
            label = f"Block ID: {node_id}\nMiner: {data['miner']}\nTime: {data['time']}\nTxns: {data['transactions']}"
            node_labels[node_id] = label
    
        # Set node colors based on role and malicious status.
        node_colors = []
        for node_id in G.nodes():
            data = G.nodes[node_id]
            if data.get("is_malicious", False):
                node_colors.append("red")            # Malicious blocks.
            elif node_id == genesis_block_id:
                node_colors.append("yellow")         # Genesis block.
            elif node_id in main_chain_blocks:
                node_colors.append("lightblue")      # Main chain blocks.
            else:
                node_colors.append("gray")           # Forked blocks.
    
        # Calculate figure dimensions based on the number of main chain blocks.
        num_blocks = len(main_chain_blocks)
        fig_width = max(14, num_blocks * (layer_spacing * 1.5))
        fig_height = 10
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
        # Draw nodes and labels.
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_shape='s', node_size=5000, ax=ax)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, verticalalignment='center', ax=ax)
    
        # Draw edges with arrows for clarity.
        for (start, end) in G.edges():
            arrow = FancyArrowPatch(
                pos[start],
                pos[end],
                arrowstyle='-|>',
                color='black',
                mutation_scale=20,
                shrinkA=0,
                shrinkB=10,
                connectionstyle='arc3,rad=0.0',
                lw=2,
            )
            ax.add_patch(arrow)
    
        ax.set_title(f'Blockchain Tree for Peer {peer_id}')
        ax.axis('off')
    
        # Create legend.
        legend_elements = [
            mpatches.Patch(color='yellow', label='Genesis Block'),
            mpatches.Patch(color='lightblue', label='Main Chain Block'),
            mpatches.Patch(color='gray', label='Forked Block'),
            mpatches.Patch(color='red', label='Malicious Block')
        ]
        ax.legend(handles=legend_elements, loc='lower left')
    
        # Save the plot as a PDF in the simOut/blockChainTrees folder.
        save_directory = 'simOut/blockChainTrees'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, f'Peer_{peer_id}.pdf')
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        print(f'Plot saved to {save_path}')

    def visualize_network_topology(self):
        """
        Visualizes the network topology of all peers.
    
        Returns:
            None
        """
        G = nx.Graph()
    
        # Add nodes with attributes. Use default values if an attribute is missing.
        for peer_id, peer in self.peers.items():
            is_low_cpu = getattr(peer, 'is_low_cpu', False)
            G.add_node(peer_id, is_slow=peer.is_slow, is_low_cpu=is_low_cpu)
    
        # Add edges based on connections.
        for peer_id, peer in self.peers.items():
            for neighbor_id in peer.connections:
                G.add_edge(peer_id, neighbor_id)
    
        # Determine node colors based on attributes.
        node_colors = []
        for node in G.nodes(data=True):
            is_slow = node[1].get('is_slow', False)
            is_low_cpu = node[1].get('is_low_cpu', False)
            if is_slow and is_low_cpu:
                node_colors.append('red')      # Slow and low CPU.
            elif is_slow and not is_low_cpu:
                node_colors.append('orange')   # Slow only.
            elif not is_slow and is_low_cpu:
                node_colors.append('green')    # Low CPU only.
            else:
                node_colors.append('blue')     # Fast and high CPU.
    
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=0.3)
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=500, font_size=8)
        plt.title('Network Topology of Peers')
        plt.axis('off')
    
        save_directory = 'simOut'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, 'PeerNetwork.png')
        plt.savefig(save_path)
        plt.close()
        print(f'Plot saved to {save_path}')

    def compare_peer_blockchains(self):
        """
        Compares the blockchains of all peers and generates a summary table.
    
        Returns:
            None
        """
        data = []
        for peer_id, peer in self.peers.items():
            longest_chain_length = len(peer.current_longest_chain)
            numBlocksByPeerInLC = sum(1 for block in peer.current_longest_chain if block.miner_id == peer_id)
            numBlocksByPeer = sum(1 for block in peer.blockchain.values() if block.miner_id == peer_id)
            ratio = (numBlocksByPeerInLC / numBlocksByPeer) if numBlocksByPeer > 0 else 0
            ratio_blocks_in_longest_chain = f"{ratio:.5f}"
            data.append([
                peer_id,
                longest_chain_length,
                numBlocksByPeerInLC,
                numBlocksByPeer,
                ratio_blocks_in_longest_chain
            ])
    
        df = pd.DataFrame(data, columns=[
            'Peer ID',
            'LC Length',
            'Blocks in LC by Peer',
            'Total Blocks by Peer',
            'Ratio (Blocks in LC/Total Blocks)'
        ])
    
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('tight')
        ax.axis('off')
        table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)
        table.auto_set_column_width(col=list(range(len(df.columns))))
    
        # Format table cells.
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
        print(f'Table saved to {save_path}')

