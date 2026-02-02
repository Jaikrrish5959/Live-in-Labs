# Dual-Ring LoRa Perimeter Simulation
# Analysis: Metrics computation and plotting

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict, Any
from collections import defaultdict

from models import DetectionRecord, SensorEvent, EventType


def compute_metrics(
    events: List[SensorEvent],
    detections: List[DetectionRecord]
) -> Dict[str, Any]:
    """Compute all simulation metrics."""
    
    # Ground truth counts
    total_intruders = sum(1 for e in events if e.event_type == EventType.INTRUDER)
    total_noise = len(events) - total_intruders

    # Detections analysis
    true_positives = [d for d in detections if d.is_true_positive]
    false_positives = [d for d in detections if not d.is_true_positive]

    # Unique event detection (first detection per event only)
    detected_event_ids = set()
    unique_detections = []
    for d in sorted(detections, key=lambda x: x.detection_time):
        if d.event_id not in detected_event_ids:
            detected_event_ids.add(d.event_id)
            unique_detections.append(d)

    tp_unique = [d for d in unique_detections if d.is_true_positive]
    fp_unique = [d for d in unique_detections if not d.is_true_positive]

    # False Positive Rate = FP / (FP + TN) = FP / total_noise
    fpr = len(fp_unique) / total_noise if total_noise > 0 else 0.0

    # Detection Rate (Sensitivity) = TP / total_intruders
    detection_rate = len(tp_unique) / total_intruders if total_intruders > 0 else 0.0

    # Latency stats
    latencies = [d.latency for d in unique_detections]
    mean_latency = np.mean(latencies) if latencies else 0.0
    max_latency = np.max(latencies) if latencies else 0.0

    # P2P message stats
    p2p_messages_per_event = [d.p2p_messages_sent for d in unique_detections if d.used_p2p]
    mean_p2p = np.mean(p2p_messages_per_event) if p2p_messages_per_event else 0.0
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
        "false_positive_rate": fpr,
        "detection_rate": detection_rate,
        "mean_latency": mean_latency,
        "max_latency": max_latency,
        "mean_p2p_messages": mean_p2p,
        "total_p2p_messages": total_p2p,
        "detections_during_outage": len(detections_during_outage),
        "outage_detection_rate": outage_rate,
        "latencies": latencies,
        "p2p_messages_list": p2p_messages_per_event
    }


def compute_pir_only_baseline(events: List[SensorEvent]) -> Dict[str, Any]:
    """Simulate naive baseline: alert on any sensor trigger (no AI thresholds, no verification).
    
    Uses the Image Confidence model, but alerts if confidence > 0.5 (any trigger).
    This represents a system without smart AI filtering or cross-verification.
    """
    import random
    import config

    NAIVE_THRESHOLD = 0.50  # Naive system: alert on any moderate signal
    
    detections = []
    for event in events:
        is_intruder = event.event_type == EventType.INTRUDER
        # Use the same image confidence model
        if is_intruder:
            conf = random.gauss(config.IMG_BOAR_MEAN, config.IMG_BOAR_STD)
        else:
            conf = random.gauss(config.IMG_NON_BOAR_MEAN, config.IMG_NON_BOAR_STD)
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
        "detection_rate": tp / total_intruders if total_intruders > 0 else 0.0,
        "false_positive_rate": fp / total_noise if total_noise > 0 else 0.0,
        "total_detections": len(detections)
    }


def print_summary(metrics: Dict[str, Any], baseline: Dict[str, Any]):
    """Print summary statistics."""
    print("=" * 60)
    print("SIMULATION RESULTS SUMMARY")
    print("=" * 60)
    print(f"\n--- Event Statistics ---")
    print(f"Total Events:          {metrics['total_events']}")
    print(f"  Intruder Events:     {metrics['total_intruders']}")
    print(f"  Noise Events:        {metrics['total_noise']}")

    print(f"\n--- Detection Performance (Cascaded + Cross-Verification) ---")
    print(f"Unique Detections:     {metrics['unique_detections']}")
    print(f"  True Positives:      {metrics['true_positives']}")
    print(f"  False Positives:     {metrics['false_positives']}")
    print(f"Detection Rate:        {metrics['detection_rate']:.2%}")
    print(f"False Positive Rate:   {metrics['false_positive_rate']:.2%}")

    print(f"\n--- Latency ---")
    print(f"Mean Latency:          {metrics['mean_latency']:.3f} s")
    print(f"Max Latency:           {metrics['max_latency']:.3f} s")

    print(f"\n--- P2P Messaging ---")
    print(f"Total P2P Messages:    {metrics['total_p2p_messages']}")
    print(f"Mean P2P per Event:    {metrics['mean_p2p_messages']:.2f}")

    print(f"\n--- Gateway Outage ---")
    print(f"Detections During Outage: {metrics['detections_during_outage']}")
    print(f"Outage Detection Rate: {metrics['outage_detection_rate']:.2%}")

    print(f"\n--- PIR-Only Baseline Comparison ---")
    print(f"Baseline Detection Rate:     {baseline['detection_rate']:.2%}")
    print(f"Baseline False Positive Rate: {baseline['false_positive_rate']:.2%}")

    print(f"\n--- Improvement ---")
    fpr_reduction = baseline['false_positive_rate'] - metrics['false_positive_rate']
    print(f"FPR Reduction:         {fpr_reduction:.2%} (absolute)")
    print("=" * 60)


def generate_plots(metrics: Dict[str, Any], output_dir: str = "."):
    """Generate visualization plots."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    # 1. Latency CDF
    plt.figure(figsize=(8, 5))
    latencies = sorted(metrics['latencies'])
    if latencies:
        cdf = np.arange(1, len(latencies) + 1) / len(latencies)
        plt.plot(latencies, cdf, linewidth=2)
        plt.xlabel("Latency (seconds)")
        plt.ylabel("CDF")
        plt.title("Detection Latency CDF")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_dir, "latency_cdf.png"), dpi=150)
        plt.close()

    # 2. P2P Message Overhead Histogram
    plt.figure(figsize=(8, 5))
    p2p_list = metrics['p2p_messages_list']
    if p2p_list:
        plt.hist(p2p_list, bins=range(0, max(p2p_list) + 2), edgecolor='black', alpha=0.7)
        plt.xlabel("P2P Messages per Event")
        plt.ylabel("Frequency")
        plt.title("P2P Message Overhead per Event")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_dir, "p2p_overhead.png"), dpi=150)
        plt.close()

    # 3. Detection Comparison Bar Chart
    plt.figure(figsize=(8, 5))
    categories = ['Detection Rate', 'False Positive Rate']
    cascaded_values = [metrics['detection_rate'], metrics['false_positive_rate']]
    # We'll need baseline passed in for full comparison, using placeholder
    x = np.arange(len(categories))
    width = 0.35
    plt.bar(x, cascaded_values, width, label='Cascaded + Verification', color='steelblue')
    plt.ylabel('Rate')
    plt.title('Detection Performance')
    plt.xticks(x, categories)
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.savefig(os.path.join(output_dir, "detection_comparison.png"), dpi=150)
    plt.close()

    print(f"Plots saved to {output_dir}/")
