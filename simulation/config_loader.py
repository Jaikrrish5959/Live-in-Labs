"""
Simulation Configuration Loader
===============================
Loads simulation parameters from JSON input with validation and defaults.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime


@dataclass
class SimulationConfig:
    """Complete configuration for a simulation run."""
    
    # Run metadata
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    random_seed: int = 42
    
    # Simulation scope
    event_count: int = 1000
    intruder_probability: float = 0.30
    event_interval_mean: float = 8.0
    
    # Topology
    outer_ring_nodes: int = 8
    inner_ring_nodes: int = 8
    outer_ring_radius: float = 23.0
    inner_ring_radius: float = 14.0
    inner_ring_offset_deg: float = 22.5
    sensor_range: float = 15.0
    p2p_range: float = 30.0
    
    # Decision logic thresholds
    confirm_threshold: float = 0.80
    verify_threshold: float = 0.70
    verification_timeout: float = 3.0
    
    # Image confidence model
    boar_confidence_mean: float = 0.85
    boar_confidence_std: float = 0.08
    noise_confidence_mean: float = 0.35
    noise_confidence_std: float = 0.15
    
    # Communication model (abstracted, no RF)
    loss_base: float = 0.0
    loss_per_meter: float = 0.0025
    delay_base: float = 0.1
    delay_per_meter: float = 0.0001
    delay_jitter: float = 0.05
    
    # Message sizes (bytes)
    msg_size_verify_req: int = 64
    msg_size_verify_resp: int = 32
    msg_size_uplink: int = 51
    
    # Gateway availability
    gateway_up_duration_mean: float = 1800.0
    gateway_down_duration_mean: float = 300.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "random_seed": self.random_seed,
            "simulation": {
                "event_count": self.event_count,
                "intruder_probability": self.intruder_probability,
                "event_interval_mean": self.event_interval_mean
            },
            "topology": {
                "outer_ring_nodes": self.outer_ring_nodes,
                "inner_ring_nodes": self.inner_ring_nodes,
                "outer_ring_radius": self.outer_ring_radius,
                "inner_ring_radius": self.inner_ring_radius,
                "inner_ring_offset_deg": self.inner_ring_offset_deg,
                "sensor_range": self.sensor_range,
                "p2p_range": self.p2p_range
            },
            "decision_logic": {
                "confirm_threshold": self.confirm_threshold,
                "verify_threshold": self.verify_threshold,
                "verification_timeout": self.verification_timeout
            },
            "image_model": {
                "boar_confidence_mean": self.boar_confidence_mean,
                "boar_confidence_std": self.boar_confidence_std,
                "noise_confidence_mean": self.noise_confidence_mean,
                "noise_confidence_std": self.noise_confidence_std
            },
            "communication": {
                "loss_base": self.loss_base,
                "loss_per_meter": self.loss_per_meter,
                "delay_base": self.delay_base,
                "delay_per_meter": self.delay_per_meter,
                "delay_jitter": self.delay_jitter
            },
            "gateway": {
                "up_duration_mean": self.gateway_up_duration_mean,
                "down_duration_mean": self.gateway_down_duration_mean
            }
        }


def load_config_from_json(json_data: Dict[str, Any]) -> SimulationConfig:
    """
    Parse JSON input into a SimulationConfig with validation.
    
    Args:
        json_data: Dictionary parsed from JSON input
        
    Returns:
        SimulationConfig with values from JSON or defaults
    """
    config = SimulationConfig()
    
    # Set run_id if provided, otherwise generate
    if "run_id" in json_data:
        config.run_id = json_data["run_id"]
    
    if "random_seed" in json_data:
        config.random_seed = int(json_data["random_seed"])
    
    # Simulation section
    sim = json_data.get("simulation", {})
    if "event_count" in sim:
        config.event_count = int(sim["event_count"])
    if "intruder_probability" in sim:
        config.intruder_probability = float(sim["intruder_probability"])
    if "event_interval_mean" in sim:
        config.event_interval_mean = float(sim["event_interval_mean"])
    
    # Topology section
    topo = json_data.get("topology", {})
    if "outer_ring_nodes" in topo:
        config.outer_ring_nodes = int(topo["outer_ring_nodes"])
    if "inner_ring_nodes" in topo:
        config.inner_ring_nodes = int(topo["inner_ring_nodes"])
    if "outer_ring_radius" in topo:
        config.outer_ring_radius = float(topo["outer_ring_radius"])
    if "inner_ring_radius" in topo:
        config.inner_ring_radius = float(topo["inner_ring_radius"])
    if "inner_ring_offset_deg" in topo:
        config.inner_ring_offset_deg = float(topo["inner_ring_offset_deg"])
    if "sensor_range" in topo:
        config.sensor_range = float(topo["sensor_range"])
    if "p2p_range" in topo:
        config.p2p_range = float(topo["p2p_range"])
    
    # Decision logic section
    decision = json_data.get("decision_logic", {})
    if "confirm_threshold" in decision:
        config.confirm_threshold = float(decision["confirm_threshold"])
    if "verify_threshold" in decision:
        config.verify_threshold = float(decision["verify_threshold"])
    if "verification_timeout" in decision:
        config.verification_timeout = float(decision["verification_timeout"])
    
    # Image model section
    img = json_data.get("image_model", {})
    if "boar_confidence_mean" in img:
        config.boar_confidence_mean = float(img["boar_confidence_mean"])
    if "boar_confidence_std" in img:
        config.boar_confidence_std = float(img["boar_confidence_std"])
    if "noise_confidence_mean" in img:
        config.noise_confidence_mean = float(img["noise_confidence_mean"])
    if "noise_confidence_std" in img:
        config.noise_confidence_std = float(img["noise_confidence_std"])
    
    # Communication section
    comm = json_data.get("communication", {})
    if "loss_base" in comm:
        config.loss_base = float(comm["loss_base"])
    if "loss_per_meter" in comm:
        config.loss_per_meter = float(comm["loss_per_meter"])
    if "delay_base" in comm:
        config.delay_base = float(comm["delay_base"])
    if "delay_per_meter" in comm:
        config.delay_per_meter = float(comm["delay_per_meter"])
    if "delay_jitter" in comm:
        config.delay_jitter = float(comm["delay_jitter"])
    
    # Gateway section
    gw = json_data.get("gateway", {})
    if "up_duration_mean" in gw:
        config.gateway_up_duration_mean = float(gw["up_duration_mean"])
    if "down_duration_mean" in gw:
        config.gateway_down_duration_mean = float(gw["down_duration_mean"])
    
    return config


def load_config_from_file(filepath: str) -> SimulationConfig:
    """Load configuration from a JSON file."""
    with open(filepath, 'r') as f:
        return load_config_from_json(json.load(f))


def validate_config(config: SimulationConfig) -> list:
    """
    Validate configuration values.
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if config.event_count < 1:
        errors.append("event_count must be at least 1")
    if config.event_count > 100000:
        errors.append("event_count cannot exceed 100000")
    
    if not 0.0 <= config.intruder_probability <= 1.0:
        errors.append("intruder_probability must be between 0 and 1")
    
    if config.outer_ring_nodes < 1 or config.inner_ring_nodes < 1:
        errors.append("Ring nodes must be at least 1")
    
    if config.outer_ring_radius <= config.inner_ring_radius:
        errors.append("outer_ring_radius must be greater than inner_ring_radius")
    
    if not 0.0 <= config.confirm_threshold <= 1.0:
        errors.append("confirm_threshold must be between 0 and 1")
    
    if not 0.0 <= config.verify_threshold <= 1.0:
        errors.append("verify_threshold must be between 0 and 1")
    
    if config.verify_threshold > config.confirm_threshold:
        errors.append("verify_threshold should be less than confirm_threshold")
    
    return errors
