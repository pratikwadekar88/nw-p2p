import os
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import matplotlib.backends.backend_pdf
from matplotlib.patches import FancyArrowPatch
from networkx.drawing.nx_agraph import graphviz_layout

class Visualizer:
    def __init__(self, peers):
        self.peers = peers


    def visualize_blockchain(self, peer_id):
        """
        Visualizes the blockchain of a specific peer.
    
        Parameters:
        peer_id (int): The ID of the peer whose blockchain is to be visualized.
    
        Returns:
        None
        """
        peer = self.peers[peer_id]
        if not peer.blockchain:
            print(f"Peer {peer_id} has no blocks in their blockchain.")
            return
    
        G = nx.DiGraph()
    
        # Add nodes and edges
        for block in peer.blockchain.values():
            block_id = block.block_id[:6]
            prev_block_id = block.prev_block_id[:6] if block.prev_block_id else None
            # Adjust timestamp to 3 decimal places
            timestamp = f"{block.timestamp:.3f}"
            G.add_node(block_id, miner=block.miner_id, time=timestamp, transactions=len(block.transactions))
            if prev_block_id:
                G.add_edge(prev_block_id, block_id)
    
        # Identify the main chain (longest valid chain), including the genesis block
        main_chain_blocks = [block.block_id[:6] for block in peer.current_longest_chain]
    
        # Ensure the genesis block is included
        genesis_block_id = None
        for node in G.nodes():
            predecessors = list(G.predecessors(node))
            if len(predecessors) == 0:
                genesis_block_id = node
                break
    
        if genesis_block_id and genesis_block_id not in main_chain_blocks:
            main_chain_blocks.insert(0, genesis_block_id)
    
        # Position nodes
        pos = {}
        layer_spacing = 2  # Horizontal spacing between blocks
        vertical_offset = 2  # Vertical offset for forks
    
        # Position the main chain in a straight horizontal line
        for idx, block_id in enumerate(main_chain_blocks):
            pos[block_id] = (idx * layer_spacing, 0)
    
        # Function to position forked blocks
        def position_forks(block_id, parent_pos, used_positions=set()):
            successors = list(G.successors(block_id))
            forks = [s for s in successors if s not in main_chain_blocks]
            for idx, fork_id in enumerate(forks):
                if fork_id not in pos:
                    # Calculate vertical position to avoid overlapping
                    y_new = parent_pos[1] - vertical_offset * (idx + 1)  # Position forked blocks below
                    x_new = parent_pos[0] + layer_spacing
                    # Ensure the position is unique
                    while (x_new, y_new) in used_positions:
                        y_new -= vertical_offset
                    pos[fork_id] = (x_new, y_new)
                    used_positions.add((x_new, y_new))
                    # Recursively position further forks
                    position_forks(fork_id, pos[fork_id], used_positions)
            # Also position forks from main chain successors
            for successor in successors:
                if successor in main_chain_blocks and successor != block_id:
                    position_forks(successor, pos[successor], used_positions)
    
        # Start positioning forks from each main chain block
        used_positions = set(pos.values())
        for block_id in main_chain_blocks:
            parent_pos = pos[block_id]
            position_forks(block_id, parent_pos, used_positions)
    
        # Handle any remaining blocks that are not connected or missed
        for block_id in G.nodes():
            if block_id not in pos:
                pos[block_id] = (0, 0)  # Position them at the origin or any default position
    
        # Prepare node labels
        node_labels = {}
        for node_id in G.nodes():
            data = G.nodes[node_id]
            label = f"Block ID: {node_id}\nMiner: {data['miner']}\nTime: {data['time']}\nTxns: {data['transactions']}"
            node_labels[node_id] = label
    
        # Prepare node colors
        node_colors = []
        for node_id in G.nodes():
            if node_id == genesis_block_id:
                node_colors.append('yellow')  # Genesis block
            elif node_id in main_chain_blocks:
                node_colors.append('lightblue')  # Main chain blocks
            else:
                node_colors.append('gray')  # Forked blocks
    
        # Calculate figure dimensions
        num_blocks = len(main_chain_blocks)
        fig_width = max(14, num_blocks * (layer_spacing * 1.5))
        fig_height = 10
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
        # Draw the graph
        nx.draw_networkx_nodes(
            G,
            pos,
            node_color=node_colors,
            node_shape='s',
            node_size=5000,
            ax=ax
        )
        nx.draw_networkx_labels(
            G,
            pos,
            labels=node_labels,
            font_size=8,
            verticalalignment='center',
            ax=ax
        )
    
        # Draw edges with FancyArrowPatch for better control over arrows
        for (start, end) in G.edges():
            start_pos = pos[start]
            end_pos = pos[end]
            arrow = FancyArrowPatch(
                start_pos,
                end_pos,
                arrowstyle='-|>',
                color='black',
                mutation_scale=20,  # Adjust arrow size
                shrinkA=0,
                shrinkB=10,  # Adjust to avoid overlap with node
                connectionstyle='arc3,rad=0.0',  # Straight lines
                lw=2,
            )
            ax.add_patch(arrow)
    
        ax.set_title(f'Blockchain Tree for Peer {peer_id}')
        ax.axis('off')
    
        # Create legend
        legend_elements = [
            mpatches.Patch(color='yellow', label='Genesis Block'),
            mpatches.Patch(color='lightblue', label='Main Chain Block'),
            mpatches.Patch(color='gray', label='Forked Block')
        ]
        ax.legend(handles=legend_elements, loc='lower left')
    
        # Specify the directory where you want to save the plot
        save_directory = 'simOut/blockChainTrees'
        os.makedirs(save_directory, exist_ok=True)
    
        # Construct the full path
        save_path = os.path.join(save_directory, f'Peer_{peer_id}.pdf')
    
        # Save the plot to the specified directory as PDF
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

        # Add nodes with attributes
        for peer_id, peer in self.peers.items():
            G.add_node(peer_id, is_slow=peer.is_slow, is_low_cpu=peer.is_low_cpu)

        # Add edges
        for peer_id, peer in self.peers.items():
            for neighbor_id in peer.connections:
                G.add_edge(peer_id, neighbor_id)

        # Node colors based on attributes
        node_colors = []
        for node in G.nodes(data=True):
            is_slow = node[1]['is_slow']
            is_low_cpu = node[1]['is_low_cpu']
            if is_slow and is_low_cpu:
                node_colors.append('red')      # Slow and low CPU
            elif is_slow and not is_low_cpu:
                node_colors.append('orange')   # Slow only
            elif not is_slow and is_low_cpu:
                node_colors.append('green')    # Low CPU only
            else:
                node_colors.append('blue')     # Fast and high CPU

        # Draw the graph
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=0.3)
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=500, font_size=8)
        plt.title('Network Topology of Peers')
        plt.axis('off')

        # Specify the directory where you want to save the plot
        save_directory = 'simOut'
        # Ensure the directory exists
        os.makedirs(save_directory, exist_ok=True)

        # Construct the full path
        save_path = os.path.join(save_directory, 'PeerNetwork.png')

        # Save the plot to the specified directory
        plt.savefig(save_path)
        plt.close()
        print(f'Plot saved to {save_path}')

    def compare_peer_blockchains(self):
        """
        Compares the blockchains of all peers and generates a table.

        Returns:
        None
        """
        # Initialize a list to store data for each peer
        data = []

        for peer_id, peer in self.peers.items():
            longest_chain_length = len(peer.current_longest_chain)
            numBlocksByPeerInLC = sum(1 for block in peer.current_longest_chain if block.miner_id == peer_id)
            numBlocksByPeer = sum(1 for block in peer.blockchain.values() if block.miner_id == peer_id)
            ratio = (numBlocksByPeerInLC / numBlocksByPeer) if numBlocksByPeer > 0 else 0
            
            # Format the ratio to 5 decimal places
            ratio_blocks_in_longest_chain = f"{ratio:.5f}"

            # Append the data for the current peer to the list
            data.append([
                peer_id,
                longest_chain_length,
                numBlocksByPeerInLC,
                numBlocksByPeer,
                ratio_blocks_in_longest_chain
            ])

        # Create a DataFrame from the data
        df = pd.DataFrame(data, columns=[
            'Peer ID',
            'LC Length',
            'Blocks in LC by Peer',
            'Total Blocks by Peer',
            'Ratio (Blocks in LC/Total Blocks)'
        ])

        # Plot the table
        fig, ax = plt.subplots(figsize=(12, 8))  # Set size frame
        ax.axis('tight')
        ax.axis('off')

        # Add the table to the axes
        table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')

        # Apply formatting
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)

        # Set column widths to be flexible
        table.auto_set_column_width(col=list(range(len(df.columns))))

        # Add color to the table
        for (i, j), cell in table.get_celld().items():
            if i == 0:  # Header row
                cell.set_facecolor('yellow')
                cell.set_text_props(weight='bold', color='black')
            elif i % 2 == 0:  # Alternate row color
                cell.set_facecolor('#f2f2f2')
            else:
                cell.set_facecolor('white')
            if i % 5 == 0 and i != 0:  # Bold line every 5th row
                cell.set_linewidth(2.0)
            cell.set_edgecolor('black')

        # Save the table as a PNG file
        save_path = os.path.join('simOut', 'peerBlockchainsTable.png')
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f'Table saved to {save_path}')
