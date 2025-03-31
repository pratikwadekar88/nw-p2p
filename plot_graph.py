# plot graph for the data
# x axis is the % of malicious nodes
# y axis is the ratio of  malicious to total blocks generated

import matplotlib.pyplot as plt
import numpy as np
from visualize import Visualizer

class Graph:
    def __init__(self, peers):
        self.x = []
        self.y1 = []
        self.y2 = []
        visual = Visualizer(peers)
        for i in range(5, 101, 5):
            self.x.append(i)
            self.y1.append(visual.ringmaster_malicious_to_total_ratio())
            self.y2.append(visual.ringmaster_malicious_to_total_malicious_ratio())

    def plot_graph(self):
        plt.plot(self.x, self.y)
        plt.xlabel('Number of malicious nodes')
        plt.ylabel('Ratio of malicious to total blocks generated')
        plt.title('Graph of ratio of malicious to total blocks generated')
        plt.show()
