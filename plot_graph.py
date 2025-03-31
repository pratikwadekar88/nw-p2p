# plot graph for the data
# x axis is the % of malicious nodes
# y axis is the ratio of  malicious to total blocks generated

import matplotlib.pyplot as plt
import numpy as np
from visualize import Visualizer
import os

class Graph:
    def __init__(self, peers):
        self.x = []
        self.y1 = []
        self.y2 = []
        visual = Visualizer(peers)
        for i in range(5, 101, 5):
            self.x.append(i)
#            self.y1.append(visual.ringmaster_malicious_to_total_ratio())
#            self.y2.append(visual.ringmaster_malicious_to_total_malicious_ratio())

    def plot_graph(self):
        plt.plot(self.x, self.y)
        # draw line between the points and mark the points of circle with colour yellow
        plt.plot(self.x, self.y1, 'yo-')
        plt.xlabel('Number of malicious nodes')
        plt.ylabel('Ratio of malicious to total blocks generated')
        plt.title('Graph of ratio of malicious to total blocks generated')
        plt.title('Network Topology of Peers')
        plt.axis('off')
        save_directory = 'simOut'
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, 'PeerNetwork.png')
        plt.savefig(save_path)
        plt.close()
        print(f'Plot saved to {save_path}')
