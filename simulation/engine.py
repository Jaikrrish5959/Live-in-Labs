"""
Simulation Engine
=================
Headless SimPy simulation runner with JSON input/output.
"""

import simpy
import random
import math
import os
from typing import Dict, Any, Tuple, List
from datetime import datetime

from .config_loader import SimulationConfig, validate_config
from .models import (
    Gateway, Network, Node, SimulationEnvironment,
    ImageConfidenceGenerator, EventType, DetectionRecord, SensorEvent
)


def compute_node_positions(config: SimulationConfig) -> Dict[str, Tuple[float, float, str]]:
    """Compute (x, y) positions for all nodes."""
    positions = {}
    
    # Outer ring
    for i in range(config.outer_ring_nodes):
        angle_deg = i * (360.0 / config.outer_ring_nodes)
        angle_rad = math.radians(angle_deg)
        x = config.outer_ring_radius * math.cos(angle_rad)
        y = config.outer_ring_radius * math.sin(angle_rad)
        positions[f"outer_{i}"] = (x, y, "outer")
    
    # Inner ring
    for i in range(config.inner_ring_nodes):
        angle_deg = i * (360.0 / config.inner_ring_nodes) + config.inner_ring_offset_deg
        angle_rad = math.radians(angle_deg)
        x = config.inner_ring_radius * math.cos(angle_rad)
        y = config.inner_ring_radius * math.sin(angle_rad)
        positions[f"inner_{i}"] = (x, y, "inner")
    
    return positions


def compute_neighbors(positions: Dict[str, Tuple[float, float, str]], 
                      p2p_range: float) -> Dict[str, List[str]]:
    """Compute neighbors for each node based on P2P range."""
    neighbors = {nid: [] for nid in positions}
    node_ids = list(positions.keys())
    
    for i, nid1 in enumerate(node_ids):
        x1, y1, _ = positions[nid1]
        for nid2 in node_ids[i + 1:]:
            x2, y2, _ = positions[nid2]
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if dist <= p2p_range:
                neighbors[nid1].append(nid2)
                neighbors[nid2].append(nid1)
    
    return neighbors


def run_simulation(config: SimulationConfig) -> Dict[str, Any]:
    """
    Execute a complete simulation run.
    
    Args:
        config: SimulationConfig with all parameters
        
    Returns:
        Dictionary with simulation results
    """
    # Validate config
    errors = validate_config(config)
    if errors:
        return {
            "success": False,
            "errors": errors,
            "run_id": config.run_id
        }
    
    # Set random seed for reproducibility
    random.seed(config.random_seed)
    
    # Initialize SimPy environment
    env = simpy.Environment()
    
    # Create gateway
    gateway = Gateway(env, config)
    
    # Create network
    network = Network(env, gateway, config)
    
    # Create image analyzer
    img_analyzer = ImageConfidenceGenerator(config)
    
    # Compute topology
    positions = compute_node_positions(config)
    neighbors = compute_neighbors(positions, config.p2p_range)
    
    # Create nodes
    for node_id, (x, y, ring_type) in positions.items():
        node = Node(
            env=env,
            node_id=node_id,
            ring_type=ring_type,
            position=(x, y),
            gateway=gateway,
            network=network,
            config=config,
            img_analyzer=img_analyzer
        )
        network.add_node(node)
    
    # Set neighbors
    network.set_neighbors(neighbors)
    
    # Create simulation environment
    sim_env = SimulationEnvironment(env, network, config)
    sim_env.generate_events(config.event_count)
    
    # Calculate simulation duration
    sim_duration = config.event_count * config.event_interval_mean + 200
    
    # Run simulation
    start_time = datetime.now()
    env.run(until=sim_duration)
    end_time = datetime.now()
    
    # Compute metrics
    metrics = compute_metrics(sim_env.events, network.all_detections)
    
    # Compute baseline for comparison
    random.seed(config.random_seed)  # Reset seed for reproducible baseline
    baseline = compute_baseline(sim_env.events, config)
    
    return {
        "success": True,
        "run_id": config.run_id,
        "config": config.to_dict(),
        "execution_time_seconds": (end_time - start_time).total_seconds(),
        "metrics": metrics,
        "baseline": baseline,
        "topology": {
            "total_nodes": len(positions),
            "outer_nodes": config.outer_ring_nodes,
            "inner_nodes": config.inner_ring_nodes
        }
    }


def compute_metrics(events: List[SensorEvent], 
                    detections: List[DetectionRecord]) -> Dict[str, Any]:
    """Compute all simulation metrics."""
    import numpy as np
    
    # Ground truth counts
    total_intruders = sum(1 for e in events if e.event_type == EventType.INTRUDER)
    total_noise = len(events) - total_intruders

    # Unique event detection (first detection per event only)
    detected_event_ids = set()
    unique_detections = []
    for d in sorted(detections, key=lambda x: x.detection_time):
        if d.event_id not in detected_event_ids:
            detected_event_ids.add(d.event_id)
            unique_detections.append(d)

    tp_unique = [d for d in unique_detections if d.is_true_positive]
    fp_unique = [d for d in unique_detections if not d.is_true_positive]

    # Metrics
    fpr = len(fp_unique) / total_noise if total_noise > 0 else 0.0
    detection_rate = len(tp_unique) / total_intruders if total_intruders > 0 else 0.0

    # Latency stats
    latencies = [d.latency for d in unique_detections]
    mean_latency = float(np.mean(latencies)) if latencies else 0.0
    max_latency = float(np.max(latencies)) if latencies else 0.0
    p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0

    # P2P message stats
    p2p_messages_per_event = [d.p2p_messages_sent for d in unique_detections if d.used_p2p]
    mean_p2p = float(np.mean(p2p_messages_per_event)) if p2p_messages_per_event else 0.0
    total_p2p = sum(d.p2p_messages_sent for d in unique_detections)

    # Gateway outage analysis
    detections_during_outage = [d for d in unique_detections if not d.gateway_was_up]
    outage_rate = len(detections_during_outage) / len(unique_detections) if unique_detections else 0.0

    return {
        "total_events": len(events),
        "total_intruders": total_intruders,
        "total_noise": total_noise,
        "total_detections": len(detections),
        "unique_detections": len(unique_detections),
        "true_positives": len(tp_unique),
        "false_positives": len(fp_unique),
        "false_positive_rate": round(fpr, 4),
        "detection_rate": round(detection_rate, 4),
        "mean_latency_seconds": round(mean_latency, 4),
        "max_latency_seconds": round(max_latency, 4),
        "p95_latency_seconds": round(p95_latency, 4),
        "mean_p2p_messages": round(mean_p2p, 2),
        "total_p2p_messages": total_p2p,
        "detections_during_outage": len(detections_during_outage),
        "outage_detection_rate": round(outage_rate, 4),
        "latencies": latencies,
        "p2p_messages_list": p2p_messages_per_event
    }


def compute_baseline(events: List[SensorEvent], config: SimulationConfig) -> Dict[str, Any]:
    """
    Compute PIR-only baseline (naive system without AI thresholds).
    """
    NAIVE_THRESHOLD = 0.50
    
    detections = []
    for event in events:
        is_intruder = event.event_type == EventType.INTRUDER
        if is_intruder:
            conf = random.gauss(config.boar_confidence_mean, config.boar_confidence_std)
        else:
            conf = random.gauss(config.noise_confidence_mean, config.noise_confidence_std)
        conf = max(0.0, min(1.0, conf))
        
        if conf > NAIVE_THRESHOLD:
            detections.append({
                "event_id": event.event_id,
                "is_true_positive": is_intruder
            })

    total_intruders = sum(1 for e in events if e.event_type == EventType.INTRUDER)
    total_noise = len(events) - total_intruders
    tp = sum(1 for d in detections if d["is_true_positive"])
    fp = len(detections) - tp

    return {
        "detection_rate": round(tp / total_intruders, 4) if total_intruders > 0 else 0.0,
        "false_positive_rate": round(fp / total_noise, 4) if total_noise > 0 else 0.0,
        "total_detections": len(detections)
    }


if __name__ == "__main__":
    # CLI entry point for testing
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Run Wildlife Intrusion Simulation")
    parser.add_argument("--config", type=str, help="Path to JSON config file")
    parser.add_argument("--events", type=int, default=100, help="Number of events")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, help="Output directory")
    
    args = parser.parse_args()
    
    if args.config:
        from .config_loader import load_config_from_file
        config = load_config_from_file(args.config)
    else:
        config = SimulationConfig(
            event_count=args.events,
            random_seed=args.seed
        )
    
    result = run_simulation(config)
    
    if result["success"]:
        print(f"Simulation completed: {result['run_id']}")
        print(f"Detection Rate: {result['metrics']['detection_rate']:.2%}")
        print(f"False Positive Rate: {result['metrics']['false_positive_rate']:.2%}")
        print(f"Mean Latency: {result['metrics']['mean_latency_seconds']:.3f}s")
    else:
        print(f"Simulation failed: {result['errors']}")
