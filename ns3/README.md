# NS-3 LoRa Dual-Ring Simulation - Setup & Run Guide

## Prerequisites

1. **Linux Environment** (Ubuntu 20.04+ recommended, or WSL2)
2. **NS-3** (version 3.36 or later)
3. **LoRaWAN Module** from signetlabdei

## Installation Steps

### Step 1: Install NS-3

```bash
# Install dependencies
sudo apt update
sudo apt install g++ python3 python3-dev pkg-config sqlite3 libsqlite3-dev \
                 cmake qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools \
                 libgsl-dev libxml2 libxml2-dev libgtk-3-dev

# Download NS-3
cd ~
wget https://www.nsnam.org/releases/ns-allinone-3.40.tar.bz2
tar xjf ns-allinone-3.40.tar.bz2
cd ns-allinone-3.40

# Build NS-3
./build.py --enable-examples --enable-tests
```

### Step 2: Install LoRaWAN Module

```bash
cd ~/ns-allinone-3.40/ns-3.40/src
git clone https://github.com/signetlabdei/lorawan.git

# Rebuild NS-3 with the new module
cd ~/ns-allinone-3.40/ns-3.40
./ns3 configure --enable-examples
./ns3 build
```

### Step 3: Copy the Simulation Script

```bash
# Copy lora-dual-ring.cc to scratch folder
cp /path/to/lora-dual-ring.cc ~/ns-allinone-3.40/ns-3.40/scratch/
```

### Step 4: Build and Run

```bash
cd ~/ns-allinone-3.40/ns-3.40

# Build the scratch script
./ns3 build

# Run the simulation
./ns3 run scratch/lora-dual-ring
```

## Expected Output

```
=== Dual-Ring LoRa Perimeter Simulation (NS-3) ===
Running simulation...
=== SIMULATION RESULTS ===
Total Events: 1000
  Intruders: ~300
  Noise: ~700
True Positives: ~295
False Positives: ~65
P2P Messages: ~200
Mean Latency: 0.15 s
Detection Rate: ~98%
False Positive Rate: ~9%
```

## Notes

1. **Simplified P2P**: This script uses direct function calls for P2P messaging. For full RF simulation, replace with actual LoRa channel model.

2. **No Gateway Simulation**: Gateway uplinks are abstracted. Add `LoraHelper` and `NetworkServer` for full LoRaWAN simulation.

3. **Logging**: Enable verbose logging with:
   ```bash
   NS_LOG="LoraDualRingSimulation=level_all" ./ns3 run scratch/lora-dual-ring
   ```

## Extending the Simulation

To add full LoRa RF simulation:

1. Use `LoraChannel` with path loss model
2. Add `LoraPhy` to each node
3. Replace direct function calls with actual packet transmissions
4. Use `LoraNetDevice` for MAC-layer simulation

See the `lorawan` module examples in `src/lorawan/examples/` for reference implementations.
