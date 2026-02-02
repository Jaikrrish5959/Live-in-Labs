# Dual-Ring LoRa Perimeter Simulation
# Configuration Parameters

import math

# --- Random Seed for Determinism ---
RANDOM_SEED = 42

# --- Simulation Time ---
SIM_DURATION = 10000  # simulation time units (seconds)
EVENT_TARGET_COUNT = 1000  # minimum events to generate

# --- Topology ---
OUTER_RING_RADIUS = 23.0  # meters
INNER_RING_RADIUS = 14.0  # meters
OUTER_RING_NODES = 8
INNER_RING_NODES = 8
OUTER_RING_SPACING_DEG = 45.0
INNER_RING_OFFSET_DEG = 22.5  # angular offset from outer ring

# --- Communication ---
P2P_RANGE = 30.0  # meters, max distance for P2P
# Packet sizes (Bytes)
MSG_SIZE_VERIFY_REQ = 64
MSG_SIZE_VERIFY_RESP = 32
MSG_SIZE_UPLINK = 51

# RF Time-on-Air & Delay Parameters (Simplified LoRa model)
# Base delay + distance factor + random jitter
DELAY_BASE = 0.1  # 100ms processing/radio prep
DELAY_PER_METER = 0.0001 # neglible propagation, mostly about slotting
DELAY_JITTER = 0.05  # +/- 50ms random jitter

# Loss Model: P(loss) = LOSS_BASE + LOSS_PER_METER * dist
# e.g., 20m -> 0.0 + 0.0025*20 = 0.05 (5%)
LOSS_BASE = 0.0
LOSS_PER_METER = 0.0025

P2P_VERIFICATION_TIMEOUT = 3.0  # seconds
SENSOR_RANGE = 15.0  # meters

# --- Gateway ---
GATEWAY_UP_DURATION_MEAN = 1800  # 30 mins
GATEWAY_DOWN_DURATION_MEAN = 300  # 5 mins (failures)

# --- Image Processing Model (Data-Driven Abstraction) ---
# Confidence distributions for Wild Boar (True) vs Non-Boar (False)
# Based on hypothetical MobileNet/YOLO performance
IMG_BOAR_MEAN = 0.85
IMG_BOAR_STD = 0.08
IMG_NON_BOAR_MEAN = 0.35
IMG_NON_BOAR_STD = 0.15

# Decision Logic Thresholds
CONFIRM_THRESHOLD = 0.80  # >= 0.80 -> Uplink
VERIFY_THRESHOLD = 0.70   # 0.70 <= x < 0.80 -> Verify

# --- Event Generation ---
INTRUDER_EVENT_PROB = 0.30  # 30% of events are true intruders
EVENT_INTERVAL_MEAN = 8.0  # mean time between events (seconds)


def compute_node_positions():
    """Compute (x, y) positions for all 16 nodes."""
    positions = {}
    # Outer ring
    for i in range(OUTER_RING_NODES):
        angle_deg = i * OUTER_RING_SPACING_DEG
        angle_rad = math.radians(angle_deg)
        x = OUTER_RING_RADIUS * math.cos(angle_rad)
        y = OUTER_RING_RADIUS * math.sin(angle_rad)
        positions[f"outer_{i}"] = (x, y, "outer")
    # Inner ring
    for i in range(INNER_RING_NODES):
        angle_deg = i * OUTER_RING_SPACING_DEG + INNER_RING_OFFSET_DEG
        angle_rad = math.radians(angle_deg)
        x = INNER_RING_RADIUS * math.cos(angle_rad)
        y = INNER_RING_RADIUS * math.sin(angle_rad)
        positions[f"inner_{i}"] = (x, y, "inner")
    return positions


def compute_neighbors(positions):
    """Compute neighbors for each node based on P2P_RANGE."""
    neighbors = {nid: [] for nid in positions}
    node_ids = list(positions.keys())
    for i, nid1 in enumerate(node_ids):
        x1, y1, _ = positions[nid1]
        for nid2 in node_ids[i + 1:]:
            x2, y2, _ = positions[nid2]
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if dist <= P2P_RANGE:
                neighbors[nid1].append(nid2)
                neighbors[nid2].append(nid1)
    return neighbors
