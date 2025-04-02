import matplotlib.pyplot as plt
import numpy as np

# Sample data (replace these with your actual simulation results)
malicious_percentages = [5, 10, 15, 20, 40, 50]
ratio_selfish_eclipse = [0.25, 0.35, 0.45, 0.55, 0.60]  # Selfish Mining + Eclipse Attack
ratio_selfish_only   = [0.20, 0.30, 0.40, 0.50, 0.55]  # Selfish Mining Alone

n_groups = len(malicious_percentages)
index = np.arange(n_groups)
bar_width = 0.35

# Create the plot
fig, ax = plt.subplots(figsize=(10, 6))

# Use pastel colors for the bars with white edges
bars1 = ax.bar(index, ratio_selfish_eclipse, bar_width,
               label='Selfish Mining + Eclipse Attack',
               color='#ff9999', edgecolor='white', linewidth=1.5)

bars2 = ax.bar(index + bar_width, ratio_selfish_only, bar_width,
               label='Selfish Mining Alone',
               color='#99ccff', edgecolor='white', linewidth=1.5)

# Set labels and title with increased font sizes for clarity
ax.set_xlabel('Percentage of Malicious Nodes (%)', fontsize=12)
ax.set_ylabel('Ratio (Malicious Blocks in Main Chain / Total Malicious Blocks)', fontsize=12)
ax.set_title('Comparative Analysis of Block Ratios for Different Attack Strategies\n(Timeout = X sec)', fontsize=14)
ax.set_xticks(index + bar_width / 2)
ax.set_xticklabels(malicious_percentages, fontsize=12)
ax.legend(fontsize=12)

# Function to add value labels on top of the bars
def autolabel(bars):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)

autolabel(bars1)
autolabel(bars2)

plt.tight_layout()
plt.show()
