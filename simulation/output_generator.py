"""
Output Generator
================
Generates simulation artifacts: metrics.json, summary.json, and PNG plots.
"""

import json
import os
from typing import Dict, Any
from datetime import datetime

import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
import numpy as np


def generate_outputs(result: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Generate all output artifacts from simulation results.
    
    Args:
        result: Dictionary from run_simulation()
        output_dir: Directory to save artifacts
        
    Returns:
        Dictionary mapping artifact names to file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    artifacts = {}
    
    # 1. Save input configuration
    input_path = os.path.join(output_dir, "input.json")
    with open(input_path, 'w') as f:
        json.dump(result.get("config", {}), f, indent=2)
    artifacts["input.json"] = input_path
    
    # 2. Generate metrics.json
    metrics_path = os.path.join(output_dir, "metrics.json")
    metrics_data = {
        "run_id": result["run_id"],
        "timestamp": datetime.now().isoformat(),
        "execution_time_seconds": result.get("execution_time_seconds", 0),
        **{k: v for k, v in result["metrics"].items() 
           if k not in ["latencies", "p2p_messages_list"]}
    }
    with open(metrics_path, 'w') as f:
        json.dump(metrics_data, f, indent=2)
    artifacts["metrics.json"] = metrics_path
    
    # 3. Generate summary.json
    summary_path = os.path.join(output_dir, "summary.json")
    summary_data = generate_summary(result)
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    artifacts["summary.json"] = summary_path
    
    # 4. Generate plots
    plot_artifacts = generate_plots(result["metrics"], result.get("baseline", {}), output_dir)
    artifacts.update(plot_artifacts)
    
    return artifacts


def generate_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate human-readable summary."""
    metrics = result["metrics"]
    baseline = result.get("baseline", {})
    
    # Calculate improvements
    fpr_reduction = baseline.get("false_positive_rate", 0) - metrics["false_positive_rate"]
    dr_diff = metrics["detection_rate"] - baseline.get("detection_rate", 0)
    
    return {
        "run_id": result["run_id"],
        "status": "completed",
        "event_summary": {
            "total_events": metrics["total_events"],
            "intruder_events": metrics["total_intruders"],
            "noise_events": metrics["total_noise"]
        },
        "detection_performance": {
            "detection_rate": f"{metrics['detection_rate']:.2%}",
            "false_positive_rate": f"{metrics['false_positive_rate']:.2%}",
            "true_positives": metrics["true_positives"],
            "false_positives": metrics["false_positives"]
        },
        "latency_performance": {
            "mean_latency": f"{metrics['mean_latency_seconds']:.3f}s",
            "max_latency": f"{metrics['max_latency_seconds']:.3f}s",
            "p95_latency": f"{metrics['p95_latency_seconds']:.3f}s"
        },
        "communication_overhead": {
            "total_p2p_messages": metrics["total_p2p_messages"],
            "mean_p2p_per_event": f"{metrics['mean_p2p_messages']:.2f}"
        },
        "gateway_reliability": {
            "detections_during_outage": metrics["detections_during_outage"],
            "outage_rate": f"{metrics['outage_detection_rate']:.2%}"
        },
        "comparison_to_baseline": {
            "baseline_detection_rate": f"{baseline.get('detection_rate', 0):.2%}",
            "baseline_fpr": f"{baseline.get('false_positive_rate', 0):.2%}",
            "fpr_reduction": f"{fpr_reduction:.2%}",
            "detection_rate_change": f"{dr_diff:+.2%}"
        },
        "conclusion": _generate_conclusion(metrics, baseline)
    }


def _generate_conclusion(metrics: Dict[str, Any], baseline: Dict[str, Any]) -> str:
    """Generate a textual conclusion for the simulation."""
    dr = metrics["detection_rate"]
    fpr = metrics["false_positive_rate"]
    base_fpr = baseline.get("false_positive_rate", 0)
    
    if dr >= 0.90 and fpr <= 0.05:
        quality = "excellent"
    elif dr >= 0.80 and fpr <= 0.10:
        quality = "good"
    elif dr >= 0.70:
        quality = "acceptable"
    else:
        quality = "needs improvement"
    
    fpr_improvement = ((base_fpr - fpr) / base_fpr * 100) if base_fpr > 0 else 0
    
    return (
        f"The cascaded detection system achieved {quality} performance with "
        f"{dr:.1%} detection rate and {fpr:.1%} false positive rate. "
        f"Compared to the PIR-only baseline, false positives were reduced by "
        f"{fpr_improvement:.0f}%."
    )


def generate_plots(metrics: Dict[str, Any], baseline: Dict[str, Any], 
                   output_dir: str) -> Dict[str, str]:
    """Generate all visualization plots."""
    artifacts = {}
    
    # Set modern style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Latency CDF
    latencies = metrics.get("latencies", [])
    if latencies:
        fig, ax = plt.subplots(figsize=(8, 5))
        sorted_lat = sorted(latencies)
        cdf = np.arange(1, len(sorted_lat) + 1) / len(sorted_lat)
        ax.plot(sorted_lat, cdf, linewidth=2, color='#2ecc71')
        ax.fill_between(sorted_lat, cdf, alpha=0.3, color='#2ecc71')
        ax.set_xlabel("Latency (seconds)", fontsize=12)
        ax.set_ylabel("CDF", fontsize=12)
        ax.set_title("Detection Latency Distribution", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add percentile markers
        p50 = np.percentile(sorted_lat, 50)
        p95 = np.percentile(sorted_lat, 95)
        ax.axvline(p50, color='#3498db', linestyle='--', label=f'Median: {p50:.2f}s')
        ax.axvline(p95, color='#e74c3c', linestyle='--', label=f'P95: {p95:.2f}s')
        ax.legend()
        
        path = os.path.join(output_dir, "latency_cdf.png")
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        artifacts["latency_cdf.png"] = path
    
    # 2. P2P Message Histogram
    p2p_list = metrics.get("p2p_messages_list", [])
    if p2p_list:
        fig, ax = plt.subplots(figsize=(8, 5))
        bins = range(0, max(p2p_list) + 2)
        ax.hist(p2p_list, bins=bins, edgecolor='white', color='#9b59b6', alpha=0.8)
        ax.set_xlabel("P2P Messages per Verification", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title("P2P Verification Overhead", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add mean line
        mean_val = np.mean(p2p_list)
        ax.axvline(mean_val, color='#e74c3c', linestyle='--', linewidth=2,
                   label=f'Mean: {mean_val:.1f}')
        ax.legend()
        
        path = os.path.join(output_dir, "p2p_overhead.png")
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        artifacts["p2p_overhead.png"] = path
    
    # 3. Detection Comparison Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    
    categories = ['Detection Rate', 'False Positive Rate']
    cascaded = [metrics["detection_rate"], metrics["false_positive_rate"]]
    baseline_vals = [baseline.get("detection_rate", 0), baseline.get("false_positive_rate", 0)]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, cascaded, width, label='Cascaded + P2P Verification',
                   color='#3498db', edgecolor='white')
    bars2 = ax.bar(x + width/2, baseline_vals, width, label='PIR-Only Baseline',
                   color='#95a5a6', edgecolor='white')
    
    ax.set_ylabel('Rate', fontsize=12)
    ax.set_title('Detection Performance Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1%}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1%}', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10)
    
    path = os.path.join(output_dir, "detection_comparison.png")
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    artifacts["detection_comparison.png"] = path
    
    # 4. Topology Visualization (optional but useful)
    # This would show node positions - skipping for now
    
    return artifacts


def cleanup_old_runs(runs_dir: str, max_runs: int = 50):
    """Clean up old simulation runs, keeping only the most recent."""
    if not os.path.exists(runs_dir):
        return
    
    runs = []
    for run_id in os.listdir(runs_dir):
        run_path = os.path.join(runs_dir, run_id)
        if os.path.isdir(run_path):
            mtime = os.path.getmtime(run_path)
            runs.append((run_id, mtime))
    
    # Sort by modification time (newest first)
    runs.sort(key=lambda x: x[1], reverse=True)
    
    # Remove old runs
    for run_id, _ in runs[max_runs:]:
        import shutil
        shutil.rmtree(os.path.join(runs_dir, run_id))
