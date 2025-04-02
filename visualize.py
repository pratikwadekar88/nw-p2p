import os
from types import NoneType
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
        peer = self.peers[peer_id]
        if not peer.blockchain:
            print(f"Peer {peer_id} has no blocks in their blockchain.")
            return

        G = nx.DiGraph()
        # Create graph nodes from all blocks in the peer's blockchain.
        for block in peer.blockchain.values():
            # Use full block_id if possible—but for display we shorten it.
            block_id = block.block_id[:6]
            prev_block_id = block.prev_block_id[:6] if block.prev_block_id else None
            timestamp = f"{block.timestamp:.3f}"
            # Save miner info in node attributes.
            G.add_node(block_id, miner=block.miner_id, time=timestamp, transactions=len(block.transactions))
            if prev_block_id:
                G.add_edge(prev_block_id, block_id)

        # Get the main chain (as short IDs) from the peer.
        main_chain_blocks = [block.block_id[:6] for block in peer.current_longest_chain]

        # Determine genesis block: node with no predecessors.
        genesis_block_id = None
        for node in G.nodes():
            if len(list(G.predecessors(node))) == 0:
                genesis_block_id = node
                break
        if genesis_block_id and genesis_block_id not in main_chain_blocks:
            main_chain_blocks.insert(0, genesis_block_id)

        # Position the main chain nodes in a horizontal line.
        pos = {}
        layer_spacing = 2
        vertical_offset = 2
        for idx, block_id in enumerate(main_chain_blocks):
            pos[block_id] = (idx * layer_spacing, 0)

        # Position the fork nodes recursively.
        def position_forks(block_id, parent_pos, used_positions):
            successors = list(G.successors(block_id))
            forks = [s for s in successors if s not in main_chain_blocks]
            for idx, fork_id in enumerate(forks):
                if fork_id not in pos:
                    y_new = parent_pos[1] - vertical_offset * (idx + 1)
                    x_new = parent_pos[0] + layer_spacing
                    # Avoid collisions.
                    while (x_new, y_new) in used_positions:
                        y_new -= vertical_offset
                    pos[fork_id] = (x_new, y_new)
                    used_positions.add((x_new, y_new))
                    position_forks(fork_id, pos[fork_id], used_positions)
            # Also ensure that any main chain successor gets its relative positions.
            for successor in successors:
                if successor in main_chain_blocks and successor != block_id:
                    position_forks(successor, pos[successor], used_positions)

        used_positions = set(pos.values())
        for block_id in main_chain_blocks:
            position_forks(block_id, pos[block_id], used_positions)

        # Fallback: for any block not yet assigned a position, try to position it relative
        # to one of its predecessors. This prevents unpositioned nodes (which would otherwise default to (0,0)).
        for block_id in G.nodes():
            if block_id not in pos:
                preds = list(G.predecessors(block_id))
                placed = False
                for p in preds:
                    if p in pos:
                        pos[block_id] = (pos[p][0] + layer_spacing, pos[p][1] - vertical_offset)
                        placed = True
                        break
                if not placed:
                    # If no predecessor is placed (should not happen in a valid blockchain), use (0,0).
                    pos[block_id] = (0, 0)

        # Prepare node labels.
        node_labels = {
            node_id: f"Block ID: {node_id}\nMiner: {data['miner']}\nTime: {data['time']}\nTxns: {data['transactions']}"
            for node_id, data in G.nodes(data=True)
        }

        # Node coloring based on roles.
        node_colors = []
        for node_id, data in G.nodes(data=True):
            if node_id == genesis_block_id:
                node_colors.append('yellow')
            elif node_id in main_chain_blocks:
                # Main chain: red if malicious, light blue if honest.
                miner_id = data.get("miner")
                if miner_id == 'Satoshi':  # Genesis fallback
                    node_colors.append('yellow')
                elif miner_id in self.peers and self.peers[miner_id].is_malicious:
                    node_colors.append('red')
                else:
                    node_colors.append('lightblue')
            else:
                # Forked block: orange if malicious, gray if honest.
                miner_id = data.get("miner")
                if miner_id != 'Satoshi' and miner_id in self.peers and self.peers[miner_id].is_malicious:
                    node_colors.append('orange')
                else:
                    node_colors.append('gray')

        # Draw nodes, labels, and edges.
        num_blocks = len(main_chain_blocks)
        fig_width = max(14, num_blocks * (layer_spacing * 1.5))
        fig, ax = plt.subplots(figsize=(fig_width, 10))
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_shape='s', node_size=5000, ax=ax)
        nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, verticalalignment='center', ax=ax)
        for (start, end) in G.edges():
            start_pos, end_pos = pos[start], pos[end]
            arrow = FancyArrowPatch(
                start_pos, end_pos,
                arrowstyle='-|>', color='black', mutation_scale=20,
                shrinkA=0, shrinkB=10, connectionstyle='arc3,rad=0.0', lw=2
            )
            ax.add_patch(arrow)
        ax.set_title(f'Blockchain Tree for Peer {peer_id}', fontsize=16)
        ax.axis('off')
        # Legend for node colors.
        legend_elements = [
            mpatches.Patch(color='yellow', label='Genesis Block'),
            mpatches.Patch(color='lightblue', label='Honest Main Chain Block'),
            mpatches.Patch(color='red', label='Malicious Main Chain Block'),
            mpatches.Patch(color='gray', label='Honest Forked Block'),
            mpatches.Patch(color='orange', label='Malicious Forked Block')
        ]
        ax.legend(handles=legend_elements, loc='lower left')
        save_directory = 'simOut/blockChainTrees'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, f'Peer_{peer_id}.pdf')
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        print(f'Plot saved to {save_path}')

    def visualize_network_topology(self):
        G = nx.Graph()
        for peer_id, peer in self.peers.items():
            G.add_node(peer_id, is_slow=peer.is_slow)
        for peer_id, peer in self.peers.items():
            for neighbor_id in peer.connections:
                G.add_edge(peer_id, neighbor_id)
        node_colors = [
            'red' if data['is_slow']
            else 'green'
            for _, data in G.nodes(data=True)
        ]
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
        data = []
        for peer_id, peer in self.peers.items():
            longest_chain_length = len(peer.current_longest_chain)
            malicious_blocks_in_lc = sum(1 for block in peer.current_longest_chain if block.is_malicious)
            ringmaster_id = None
            for peer in self.peers.values():
                if peer.is_ringmaster:
                    ringmaster_id = peer.peer_id
                    break
            total_blocks_by_malicious = self.peers[ringmaster_id].blocks_mined
            ratio1 = (malicious_blocks_in_lc / max(1, longest_chain_length))
            ratio1 = f"{ratio1:.5f}"
            ratio2 = (malicious_blocks_in_lc / max(1, total_blocks_by_malicious))
            ratio2 = f"{ratio2:.5f}"
            data.append([peer_id, longest_chain_length, malicious_blocks_in_lc, total_blocks_by_malicious, ratio1, ratio2])
        df = pd.DataFrame(data, columns=['Peer ID', 'LC Length', 'Malicious Blocks in LC', 'Total Blocks by Malicious', 'Ratio (Malicious Blocks/LC Length)', 'Ratio (Malicious Blocks/Total Blocks by Malicious Nodes)'])

        # Find the row index (in the DataFrame) for the ringmaster.
        ringmaster_index = df.index[df['Peer ID'] == ringmaster_id].tolist()[0] if ringmaster_id is not None else None
        # Table row index: header is row 0, then DataFrame row i appears at table row i+1.
        highlight_row = ringmaster_index + 1 if ringmaster_index is not None else None

        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('tight')
        ax.axis('off')
        table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)
        table.auto_set_column_width(col=list(range(len(df.columns))))
        for (i, j), cell in table.get_celld().items():
            if i == 0:
                cell.set_facecolor('yellow')
                cell.set_text_props(weight='bold', color='black')
            elif highlight_row is not None and i == highlight_row:
                # Highlight entire row of ringmaster.
                cell.set_facecolor('lightgreen')
                cell.set_text_props(weight='bold', color='black')
            elif i % 2 == 0:
                cell.set_facecolor('#f2f2f2')
            else:
                cell.set_facecolor('white')
            if i % 5 == 0 and i != 0:
                cell.set_linewidth(2.0)
            cell.set_edgecolor('black')
        save_path = os.path.join('simOut', 'peerBlockchainsTable.png')
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        plt.close()
        print(f'Table saved to {save_path}')
