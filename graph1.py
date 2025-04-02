#graph1 

import matplotlib.pyplot as plt
import numpy as np

# Sample data (replace these with your actual simulation results)
# X-axis: Percentage of malicious nodes in the network
malicious_percentages = [5, 10, 15, 20, 25]
# Y-axis: Ratio = (Number of malicious blocks in longest chain at ringmaster) / (Total blocks in longest chain at ringmaster)
ratio_malicious_in_longest = [0.30, 0.40, 0.50, 0.55, 0.60]

n_groups = len(malicious_percentages)
index = np.arange(n_groups)
bar_width = 0.6  # Using a single bar per group

# Create the figure and axis
fig, ax = plt.subplots(figsize=(10, 6))

# Draw bars using a light pastel green color
bars = ax.bar(index, ratio_malicious_in_longest, bar_width,
              color='#ccffcc', edgecolor='white', linewidth=1.5,
              label='Malicious Ratio')

# Set axis labels and title with appropriate font sizes
ax.set_xlabel('Percentage of Malicious Nodes (%)', fontsize=12)
ax.set_ylabel('Ratio (Malicious Blocks in LC / Total Blocks in LC)', fontsize=12)
ax.set_title('Ratio of Malicious Blocks in Longest Chain at Ringmaster', fontsize=14)
ax.set_xticks(index)
ax.set_xticklabels(malicious_percentages, fontsize=12)

# Optionally, add numeric labels on top of each bar.
def autolabel(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3),  # Vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)

autolabel(bars)

plt.tight_layout()
plt.show()
