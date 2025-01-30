import random
from typing import List
from matplotlib import pyplot as plt
import networkx as nx
import numpy as np
from simulator_parameters import SimulatorParameters
from node import Node


class Network:
    def __init__(self, nodes_list: List[Node], simulator_parameters: SimulatorParameters):
        self.nodes_list = nodes_list
        self.simulator_parameters = simulator_parameters
        self.__create_connected_graph()
        pass

    def __create_connected_graph(self) -> None:
        """Point 4 of the PDF: create a connected network of nodes"""
        # REFER: https://www.scitepress.org/Papers/2014/49373/49373.pdf  
        # REFER: https://networkx.org/documentation/networkx-1.9.1/reference/generated/networkx.generators.random_graphs.barabasi_albert_graph.html
        # REFER: https://www.geeksforgeeks.org/barabasi-albert-graph-scale-free-models/
        # REFER: https://stackoverflow.com/questions/2041517/random-simple-connected-graph-generation-with-given-sparseness
        # REFER: https://stackoverflow.com/questions/6667201/how-to-define-a-two-dimensional-array

        # Total nodes in the graph
        n: int = self.simulator_parameters.n_total_nodes

        # Creating the barabasi albert graph for 'n' nodes
        g: nx.classes.graph.Graph = nx.barabasi_albert_graph(n, random.randint(1, 10 if n > 10 else max(1, n - 1)))

        # Point 5 of the PDF - latency time between sender "i" and receiver "j" for a message "m"
        #   ρ_ij is a positive minimum value corresponding to the speed of light propagation delay
        #   ρ_ij time is stored in "seconds"

        # The adjacency matrix (adj_mat) stores ρ_ij, and the matrix is NOT symmetric
        adj_mat: List[List[int]] = [[0 for i in range(n)] for j in range(n)]
        for i in range(n):
            for j in range(n):
                # Point 5 of the PDF
                adj_mat[i][j] = 0.010 + np.random.random() * (0.500 - 0.010)

        for edge in g.edges():
            node_i_id: int = edge[0]
            node_j_id: int = edge[1]

            # c_ij is the link speed between i and j
            # c_ij is in "bits per second"

            # If any of the nodes is SLOW
            c_ij = 5 * 1_000_000  # 5 Mbps

            if self.nodes_list[node_i_id].is_network_fast and self.nodes_list[node_j_id].is_network_fast:
                # If both of the nodes are FAST
                c_ij = 100 * 1_000_000  # 100 Mbps

            # Add node 'j' to the peers list of node 'i'
            self.nodes_list[node_i_id].add_new_peer(node_j_id, adj_mat[node_i_id][node_j_id], c_ij)
            # Add node 'i' to the peers list of node 'j'
            self.nodes_list[node_j_id].add_new_peer(node_i_id, adj_mat[node_j_id][node_i_id], c_ij)

        nx.draw(g, with_labels=True)
        plt.show()