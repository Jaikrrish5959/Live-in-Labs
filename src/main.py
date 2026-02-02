#!/usr/bin/env python3
"""
Dual-Ring LoRa Perimeter Simulation
====================================
Agent-based discrete-event simulation for validating a dual-ring
LoRa perimeter sensing network.

Author: Simulation Engineer
"""

import simpy
import random
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from models import Gateway, Node, Network, Environment
from analysis import compute_metrics, compute_pir_only_baseline, print_summary, generate_plots


import argparse

def main():
    parser = argparse.ArgumentParser(description="Dual-Ring LoRa Simulation")
    parser.add_argument("--experiment", type=str, default="default", 
                        choices=["default", "fpr", "latency", "gateway", "density"],
                        help="Experiment mode to run")
    parser.add_argument("--nodes", type=int, default=16, help="Total number of nodes (Density exp)")
    parser.add_argument("--loss", type=float, default=config.LOSS_BASE, help="Base packet loss prob")
    parser.add_argument("--timeout", type=float, default=config.P2P_VERIFICATION_TIMEOUT, help="P2P timeout")
    parser.add_argument("--gateway_down", action="store_true", help="Force gateway down")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"DUAL-RING LoRa SIMULATION - Mode: {args.experiment.upper()}")
    print("=" * 60)

    # Apply Overrides based on arguments
    config.LOSS_BASE = args.loss
    config.P2P_VERIFICATION_TIMEOUT = args.timeout
    if args.gateway_down:
        config.GATEWAY_UP_DURATION_MEAN = 1  # almost zero
        config.GATEWAY_DOWN_DURATION_MEAN = 999999
    
    # Set random seed
    random.seed(config.RANDOM_SEED)

    # Initialize SimPy environment
    env = simpy.Environment()

    # Create gateway
    gateway = Gateway(env)

    # Create network
    network = Network(env, gateway)

    # Topology Generation (Support Density Experiment)
    # Default 16 nodes (8+8). If changed, scale proportionally.
    n_outer = args.nodes // 2
    n_inner = args.nodes - n_outer
    
    positions = {}
    # Outer ring
    for i in range(n_outer):
        angle = math.radians(i * (360/n_outer))
        positions[f"outer_{i}"] = (config.OUTER_RING_RADIUS * math.cos(angle), 
                                   config.OUTER_RING_RADIUS * math.sin(angle), "outer")
    # Inner ring
    for i in range(n_inner):
        angle = math.radians(i * (360/n_inner) + config.INNER_RING_OFFSET_DEG)
        positions[f"inner_{i}"] = (config.INNER_RING_OFFSET_DEG * math.cos(angle), # Bug fixed in logic below
                                   config.INNER_RING_RADIUS * math.sin(angle), "inner")
        # Fix: Logic for inner ring position was using OFFSET_DEG as radius by mistake in previous thought, 
        # correcting to use config.INNER_RING_RADIUS
        positions[f"inner_{i}"] = (config.INNER_RING_RADIUS * math.cos(angle), 
                                   config.INNER_RING_RADIUS * math.sin(angle), "inner")

    neighbors = config.compute_neighbors(positions)
    print(f"Topology: {len(positions)} nodes (Outer: {n_outer}, Inner: {n_inner})")

    # Create nodes
    for node_id, (x, y, ring_type) in positions.items():
        node = Node(env, node_id, ring_type, (x, y), gateway, network)
        network.add_node(node)

    # Set neighbors
    network.set_neighbors(neighbors)

    # Create environment
    sim_env = Environment(env, network)
    sim_env.generate_events(config.EVENT_TARGET_COUNT)

    # Run simulation
    print(f"Running simulation ({config.EVENT_TARGET_COUNT} events)...")
    sim_duration = config.EVENT_TARGET_COUNT * config.EVENT_INTERVAL_MEAN + 200
    env.run(until=sim_duration)
    
    # Compute metrics
    metrics = compute_metrics(sim_env.events, network.all_detections)
    
    # Run Baseline for comparison (only needed for default/FPR)
    random.seed(config.RANDOM_SEED)
    baseline = compute_pir_only_baseline(sim_env.events)

    print_summary(metrics, baseline)
    
    # Auto-generate plots
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
    generate_plots(metrics, output_dir)
    
    print("\nSimulation Finished.")
    return 0

if __name__ == "__main__":
    import math # Ensure math is imported
    sys.exit(main())
