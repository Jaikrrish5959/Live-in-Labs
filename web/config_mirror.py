# web/config_mirror.py

# --- Deployment Settings ---
NODE_COUNT_OUTER = 8
NODE_COUNT_INNER = 8

# --- Geometry (Scaled: 1 meter = 10 pixels) ---
SCALE = 10  # pixels per meter
OUTER_RING_RADIUS = 23 * SCALE  # 23m -> 230px
INNER_RING_RADIUS = 14 * SCALE  # 14m -> 140px
INNER_RING_OFFSET = 22.5 # Degrees

# PIR Sensor Field of View
SENSOR_FOV_DEGREES = 120  # Horizontal field of view (degrees) - Increased for overlap
SENSOR_DEPTH = 10 * SCALE  # Detection depth/range (10 meters -> 100px)

# --- Sensor Delays (Seconds) ---
PIR_DELAY = 1.0        # Time to wake up
THERMAL_DELAY = 0.5    # Time to verify heat signature
CAMERA_DELAY = 0.8     # Time to capture & classify
VOTING_TIMEOUT = 3.0   # Time to wait for neighbors

# --- Ranges (Pixels) ---
SENSOR_RANGE = 100      # Visual/Logic range for detection (Matched to DEPTH)

# --- Battery Consumption (Percentage Drops) ---
BATTERY_DRAIN_IDLE = 0.001
BATTERY_DRAIN_PIR = 0.05
BATTERY_DRAIN_THERMAL = 0.1
BATTERY_DRAIN_CAMERA = 0.5
BATTERY_DRAIN_RADIO = 0.2

# --- Logic Thresholds ---
VOTE_CONFIRM_THRESHOLD = 2  # Min votes to trigger alert
