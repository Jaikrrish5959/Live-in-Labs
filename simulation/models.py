"""
Simulation Models (Refactored)
==============================
Node, Gateway, Network, and Environment models for headless simulation.
All parameters passed via SimulationConfig - no global state.
"""

import simpy
import random
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from .config_loader import SimulationConfig


class EventType(Enum):
    INTRUDER = "intruder"
    NOISE = "noise"


@dataclass
class SensorEvent:
    """Represents an environmental event (intruder or noise)."""
    event_id: int
    event_type: EventType
    time: float
    position: Tuple[float, float]
    duration: float


@dataclass
class DetectionRecord:
    """Record of a detection by the system."""
    event_id: int
    node_id: str
    detection_time: float
    confirmed: bool
    used_p2p: bool
    p2p_messages_sent: int
    gateway_was_up: bool
    latency: float
    is_true_positive: bool
    confidence: float


@dataclass
class ImageAnalysisResult:
    """Output from the abstracted Image Processing Module."""
    classification: str  # "wild_boar" or "other"
    confidence: float
    timestamp: float


class ImageConfidenceGenerator:
    """Abstracts the Image Processing / CNN module."""
    
    def __init__(self, config: SimulationConfig):
        self.boar_mean = config.boar_confidence_mean
        self.boar_std = config.boar_confidence_std
        self.noise_mean = config.noise_confidence_mean
        self.noise_std = config.noise_confidence_std
    
    def analyze(self, event_type: EventType) -> ImageAnalysisResult:
        """Generate a confidence score based on empirical distributions."""
        if event_type == EventType.INTRUDER:
            conf = random.gauss(self.boar_mean, self.boar_std)
            cls = "wild_boar"
        else:
            conf = random.gauss(self.noise_mean, self.noise_std)
            cls = "other"
        
        # Clamp to [0.0, 1.0]
        conf = max(0.0, min(1.0, conf))
        return ImageAnalysisResult(classification=cls, confidence=conf, timestamp=0.0)


class Gateway:
    """Gateway abstraction: tracks availability and receives uplinks."""

    def __init__(self, env: simpy.Environment, config: SimulationConfig):
        self.env = env
        self.config = config
        self.is_up = True
        self.uplinks_received: List[Dict[str, Any]] = []
        self.env.process(self._availability_process())

    def _availability_process(self):
        """Alternates gateway between up and down states."""
        while True:
            # Up phase
            up_duration = random.expovariate(1.0 / self.config.gateway_up_duration_mean)
            yield self.env.timeout(up_duration)
            self.is_up = False
            # Down phase
            down_duration = random.expovariate(1.0 / self.config.gateway_down_duration_mean)
            yield self.env.timeout(down_duration)
            self.is_up = True

    def receive_uplink(self, node_id: str, event_id: int, time: float) -> bool:
        """Receive an uplink from a node (if gateway is up)."""
        delivered = self.is_up
        self.uplinks_received.append({
            "node_id": node_id,
            "event_id": event_id,
            "time": time,
            "delivered": delivered
        })
        return delivered


class Network:
    """Wireless Networking Simulator (Abstracted - no RF physics)."""

    def __init__(self, env: simpy.Environment, gateway: Gateway, config: SimulationConfig):
        self.env = env
        self.gateway = gateway
        self.config = config
        self.nodes: Dict[str, 'Node'] = {}
        self.all_detections: List[DetectionRecord] = []
        
        # Simple collision tracking
        self.active_transmissions = 0

    def add_node(self, node: 'Node'):
        self.nodes[node.node_id] = node

    def set_neighbors(self, neighbors_map: Dict[str, List[str]]):
        for node_id, neighbor_ids in neighbors_map.items():
            if node_id in self.nodes:
                self.nodes[node_id].neighbors = neighbor_ids

    def p2p_broadcast(self, sender_id: str, message_type: str, payload: Any):
        """Simulate P2P multicast to neighbors with abstracted delays."""
        sender = self.nodes[sender_id]
        neighbors = sender.neighbors
        
        # Determine message size for delay calculation
        if message_type == "VERIFY_REQ":
            size = self.config.msg_size_verify_req
        elif message_type == "VERIFY_RESP":
            size = self.config.msg_size_verify_resp
        else:
            size = 32
        
        # Collision penalty (abstracted)
        collision_penalty = 0.20 if self.active_transmissions > 0 else 0.0
        
        self.active_transmissions += 1
        
        # Transmission duration (abstracted)
        toa = size * 0.002  # ~2ms per byte
        yield self.env.timeout(toa)
        
        self.active_transmissions -= 1

        for nid in neighbors:
            if nid not in self.nodes:
                continue
            receiver = self.nodes[nid]
            
            # Distance calculation
            sx, sy = sender.position
            rx, ry = receiver.position
            dist = math.sqrt((sx - rx)**2 + (sy - ry)**2)
            
            # Loss model (probability-based)
            p_loss = self.config.loss_base + (self.config.loss_per_meter * dist) + collision_penalty
            if random.random() < p_loss:
                continue  # Packet lost
            
            # Delay model
            delay = self.config.delay_base + (self.config.delay_per_meter * dist) + \
                    random.uniform(-self.config.delay_jitter, self.config.delay_jitter)
            delay = max(0.01, delay)
            
            # Schedule delivery
            self.env.process(self._deliver_p2p(receiver, message_type, payload, delay))

    def _deliver_p2p(self, receiver: 'Node', msg_type: str, payload: Any, delay: float):
        yield self.env.timeout(delay)
        receiver.receive_p2p_message(msg_type, payload)

    def dispatch_event_to_nodes(self, event: SensorEvent):
        """Dispatch event to nodes within sensor range."""
        ex, ey = event.position
        for node in self.nodes.values():
            nx, ny = node.position
            dist = math.sqrt((ex - nx) ** 2 + (ey - ny) ** 2)
            if dist <= self.config.sensor_range:
                node.handle_sensor_event(event)

    def report_detection(self, record: DetectionRecord):
        self.all_detections.append(record)


class Node:
    """Perimeter Node Agent with 3-Tier Decision Logic."""

    def __init__(self, env: simpy.Environment, node_id: str, ring_type: str,
                 position: Tuple[float, float], gateway: Gateway, network: 'Network',
                 config: SimulationConfig, img_analyzer: ImageConfidenceGenerator):
        self.env = env
        self.node_id = node_id
        self.ring_type = ring_type
        self.position = position
        self.gateway = gateway
        self.network = network
        self.config = config
        self.img_analyzer = img_analyzer
        self.neighbors: List[str] = []
        
        # Verification state
        self.verification_event: Optional[simpy.Event] = None
        self.pending_confirmations = 0

    def handle_sensor_event(self, event: SensorEvent):
        """Process an event: Camera Capture -> Decision Logic."""
        self.env.process(self._process_logic(event))

    def _process_logic(self, event: SensorEvent):
        # 1. Image Processing Abstraction
        result = self.img_analyzer.analyze(event.event_type)
        confidence = result.confidence
        
        # 2. Decision Policy
        # Tier 1: High Confidence -> Immediate Uplink
        if confidence >= self.config.confirm_threshold:
            self._send_uplink(event, confidence, used_p2p=False, p2p_msgs=0)
            
        # Tier 2: Medium Confidence -> P2P Verification
        elif confidence >= self.config.verify_threshold:
            yield from self._run_verification_protocol(event, confidence)
            
        # Tier 3: Low Confidence -> Ignore
        else:
            return

    def _run_verification_protocol(self, event: SensorEvent, confidence: float):
        """Execute P2P verification (Tier 2)."""
        # Broadcast VERIFY_REQ
        yield from self.network.p2p_broadcast(self.node_id, "VERIFY_REQ", event)
        
        # Wait for responses
        self.pending_confirmations = 0
        self.verification_event = self.env.event()
        
        try:
            yield self.verification_event | self.env.timeout(self.config.verification_timeout)
            
            if self.verification_event.triggered:
                # Confirmed! Escalate
                self._send_uplink(event, confidence, used_p2p=True, p2p_msgs=1)
        except simpy.Interrupt:
            pass

    def receive_p2p_message(self, msg_type: str, payload: Any):
        """Handle incoming P2P messages."""
        if msg_type == "VERIFY_REQ":
            event = payload
            # Check my own camera/sensor
            my_reading = self.img_analyzer.analyze(event.event_type)
            if my_reading.confidence >= self.config.confirm_threshold:
                # Send VERIFY_RESP
                self.env.process(
                    self.network.p2p_broadcast(self.node_id, "VERIFY_RESP", payload)
                )
        
        elif msg_type == "VERIFY_RESP":
            # Someone confirmed my request
            if self.verification_event and not self.verification_event.triggered:
                self.pending_confirmations += 1
                self.verification_event.succeed()

    def _send_uplink(self, event: SensorEvent, confidence: float, used_p2p: bool, p2p_msgs: int):
        """Send final confirmation to Gateway."""
        detection_time = self.env.now
        
        # Gateway availability check
        gw_success = self.gateway.receive_uplink(self.node_id, event.event_id, detection_time)
        
        record = DetectionRecord(
            event_id=event.event_id,
            node_id=self.node_id,
            detection_time=detection_time,
            confirmed=True,
            used_p2p=used_p2p,
            p2p_messages_sent=p2p_msgs,
            gateway_was_up=gw_success,
            latency=detection_time - event.time,
            is_true_positive=(event.event_type == EventType.INTRUDER),
            confidence=confidence
        )
        self.network.report_detection(record)


class SimulationEnvironment:
    """Simulation environment: generates events."""

    def __init__(self, env: simpy.Environment, network: Network, config: SimulationConfig):
        self.env = env
        self.network = network
        self.config = config
        self.events: List[SensorEvent] = []
        self.event_counter = 0

    def generate_events(self, count: int):
        self.env.process(self._event_generator(count))

    def _event_generator(self, count: int):
        # Generate events within perimeter area (based on outer ring radius)
        max_radius = self.config.outer_ring_radius + 5  # Slightly beyond outer ring
        
        for _ in range(count):
            interval = random.expovariate(1.0 / self.config.event_interval_mean)
            yield self.env.timeout(interval)

            is_intruder = random.random() < self.config.intruder_probability
            event_type = EventType.INTRUDER if is_intruder else EventType.NOISE
            
            # Random position within perimeter
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, max_radius)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            event = SensorEvent(
                event_id=self.event_counter,
                event_type=event_type,
                time=self.env.now,
                position=(x, y),
                duration=random.uniform(1, 5)
            )
            self.events.append(event)
            self.event_counter += 1
            self.network.dispatch_event_to_nodes(event)
