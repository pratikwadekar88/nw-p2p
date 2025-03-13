# config.py

# Simulation parameters
NUM_PEERS = 20                 # Total number of peers
PERCENT_SLOW = 0.5             # Percentage of slow (honest) nodes
PERCENT_LOW_CPU = 0.5          # Percentage of low-CPU nodes
MEAN_TX_INTERVAL = 5           # Mean time between transactions (seconds)
MEAN_BLOCK_INTERVAL = 20       # Mean block interval for mining (seconds)
SIMULATION_TIME = 3000         # Total simulation time (seconds)

# Network topology parameters
MIN_CONNECTIONS = 3
MAX_CONNECTIONS = 6

# Propagation delay parameters (seconds)
MALICIOUS_MIN_PROP_DELAY = 0.001  # 1 ms
MALICIOUS_MAX_PROP_DELAY = 0.01   # 10 ms
MIN_PROP_DELAY = 0.01             # 10 ms
MAX_PROP_DELAY = 0.5              # 500 ms


# Link speeds (bits per second)
FAST_LINK_SPEED = 100e6        # 100 Mbps
SLOW_LINK_SPEED = 5e6          # 5 Mbps

# Message sizes (in bytes)
TRANSACTION_SIZE = 1 * 1024    # 1 KB
MAX_BLOCK_SIZE = 1 * 1024 * 1024   # 1 MB
EMPTY_BLOCK_SIZE = 1 * 1024         # 1 KB (block header size)
HASH_SIZE = 64                 # 64 bytes for block hash

# Financial parameters
COINBASE_AMOUNT = 50           # Mining reward
INITIAL_BALANCE = 1000         # Starting balance for each peer

# Malicious node parameters
MALICIOUS_PERCENT = 0.2        # Percentage of nodes that are malicious
