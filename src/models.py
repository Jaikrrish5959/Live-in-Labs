# Dual-Ring LoRa Perimeter Simulation
# Models: Node, Gateway, Environment, Network (Refactored for Networking Focus)

import simpy
import random
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

import config


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
    
    @staticmethod
    def analyze(event_type: EventType) -> ImageAnalysisResult:
        """Generate a confidence score based on empirical distributions."""
        timestamp = 0.0 # Placeholder, set by caller if needed
        
        if event_type == EventType.INTRUDER:
            # True Wild Boar: High confidence distribution
            conf = random.gauss(config.IMG_BOAR_MEAN, config.IMG_BOAR_STD)
            cls = "wild_boar"
        else:
            # Non-Boar (Noise/Confuser): Low confidence distribution
            conf = random.gauss(config.IMG_NON_BOAR_MEAN, config.IMG_NON_BOAR_STD)
            cls = "other"
            
        # Clamp to [0.0, 1.0]
        conf = max(0.0, min(1.0, conf))
        return ImageAnalysisResult(classification=cls, confidence=conf, timestamp=timestamp)


class Gateway:
    """Gateway abstraction: tracks availability and receives uplinks."""

    def __init__(self, env: simpy.Environment):
        self.env = env
        self.is_up = True
        self.uplinks_received: List[Dict[str, Any]] = []
        self.env.process(self._availability_process())

    def _availability_process(self):
        """Alternates gateway between up and down states."""
        while True:
            # Up phase
            yield self.env.timeout(random.expovariate(1.0 / config.GATEWAY_UP_DURATION_MEAN))
            self.is_up = False
            # Down phase
            yield self.env.timeout(random.expovariate(1.0 / config.GATEWAY_DOWN_DURATION_MEAN))
            self.is_up = True

    def receive_uplink(self, node_id: str, event_id: int, time: float):
        """Receive an uplink from a node (if gateway is up)."""
        if self.is_up:
            self.uplinks_received.append({
                "node_id": node_id,
                "event_id": event_id,
                "time": time,
                "delivered": True
            })
            return True
        else:
            self.uplinks_received.append({
                "node_id": node_id,
                "event_id": event_id,
                "time": time,
                "delivered": False
            })
            return False


class Network:
    """Wireless Networking Simulator (The Main Focus)."""

    def __init__(self, env: simpy.Environment, gateway: Gateway):
        self.env = env
        self.gateway = gateway
        self.nodes: Dict[str, 'Node'] = {}
        self.all_detections: List[DetectionRecord] = []
        
        # Collision Tracking
        self.active_transmissions = 0
        self.collision_window_end = 0.0

    def add_node(self, node: 'Node'):
        self.nodes[node.node_id] = node

    def set_neighbors(self, neighbors_map: Dict[str, List[str]]):
        for node_id, neighbor_ids in neighbors_map.items():
            if node_id in self.nodes:
                self.nodes[node_id].neighbors = neighbor_ids

    def p2p_broadcast(self, sender_id: str, message_type: str, payload: Any):
        """Simulate P2P multicast to neighbors with realistic RF effects."""
        sender = self.nodes[sender_id]
        neighbors = sender.neighbors
        
        # Determine message size for delay calculation
        if message_type == "VERIFY_REQ":
            size = config.MSG_SIZE_VERIFY_REQ
        elif message_type == "VERIFY_RESP":
            size = config.MSG_SIZE_VERIFY_RESP
        else:
            size = 32
            
        # Collision Check (Abstracted)
        # If channel is busy, we might drop or delay. Simplified: increased loss prob during collisions.
        collision_penalty = 0.0
        if self.active_transmissions > 0:
            collision_penalty = 0.20 # 20% extra loss if colliding
            
        self.active_transmissions += 1
        
        # Transmission duration (Time on Air)
        # Simplified: size * constant factor (e.g. at SF7 ~ 50-100ms)
        toa = size * 0.002 # approx 2ms per byte airtime
        yield self.env.timeout(toa) 
        
        self.active_transmissions -= 1

        for nid in neighbors:
            receiver = self.nodes[nid]
            
            # Distance Calculation
            sx, sy = sender.position
            rx, ry = receiver.position
            dist = math.sqrt((sx - rx)**2 + (sy - ry)**2)
            
            # Loss Model
            p_loss = config.LOSS_BASE + (config.LOSS_PER_METER * dist) + collision_penalty
            if random.random() < p_loss:
                continue # Packet Lost
                
            # Delay Model
            delay = config.DELAY_BASE + (config.DELAY_PER_METER * dist) + \
                    random.uniform(-config.DELAY_JITTER, config.DELAY_JITTER)
            if delay < 0: delay = 0.01
            
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
            if dist <= config.SENSOR_RANGE:
                node.handle_sensor_event(event)

    def report_detection(self, record: DetectionRecord):
        self.all_detections.append(record)


class Node:
    """Perimeter Node Agent with 3-Tier Decision Logic."""

    def __init__(self, env: simpy.Environment, node_id: str, ring_type: str,
                 position: Tuple[float, float], gateway: Gateway, network: Network):
        self.env = env
        self.node_id = node_id
        self.position = position
        self.gateway = gateway
        self.network = network
        self.neighbors: List[str] = []
        
        # Verification State
        self.verification_event: Optional[simpy.Event] = None
        self.pending_confirmations = 0

    def handle_sensor_event(self, event: SensorEvent):
        """Process an event: Camera Capture -> Decision Logic."""
        self.env.process(self._process_logic(event))

    def _process_logic(self, event: SensorEvent):
        # 1. Image Processing Abstraction
        result = ImageConfidenceGenerator.analyze(event.event_type)
        confidence = result.confidence
        
        # 2. Decision Policy
        # Tier 1: High Confidence -> Immediate Uplink
        if confidence >= config.CONFIRM_THRESHOLD:
            self._send_uplink(event, confidence, used_p2p=False, p2p_msgs=0)
            
        # Tier 2: Medium Confidence -> P2P Verification
        elif confidence >= config.VERIFY_THRESHOLD:
            yield from self._run_verification_protocol(event, confidence)
            
        # Tier 3: Low Confidence -> Ignore
        else:
            return # Ignore
            
    def _run_verification_protocol(self, event: SensorEvent, confidence: float):
        """Execute P2P verification (Tier 2)."""
        # Broadcast VERIFY_REQ
        yield from self.network.p2p_broadcast(self.node_id, "VERIFY_REQ", event)
        
        # Wait for responses
        self.pending_confirmations = 0
        self.verification_event = self.env.event()
        
        # Wait until timeout OR sufficient confirmations
        try:
             # Wait for 1 confirmation is enough to escalate in this logic
            yield self.verification_event | self.env.timeout(config.P2P_VERIFICATION_TIMEOUT)
            
            if self.verification_event.triggered:
                # Confirmed! Escalate
                # (1 broadcast + 1 response = 2 messages minimum tracked here, simplified)
                self._send_uplink(event, confidence, used_p2p=True, p2p_msgs=1) 
        except simpy.Interrupt:
            pass

    def receive_p2p_message(self, msg_type: str, payload: Any):
        """Handle incoming P2P messages."""
        if msg_type == "VERIFY_REQ":
            event = payload
            # Neighbor asking for help. Check my own camera/sensor.
            # I confirm IF I also see it with high confidence
            my_reading = ImageConfidenceGenerator.analyze(event.event_type)
            if my_reading.confidence >= config.CONFIRM_THRESHOLD:
                 # Send VERIFY_RESP
                 self.env.process(
                     self.network.p2p_broadcast(self.node_id, "VERIFY_RESP", payload)
                 )
        
        elif msg_type == "VERIFY_RESP":
            # Someone confirmed my request!
            if self.verification_event and not self.verification_event.triggered:
                self.pending_confirmations += 1
                self.verification_event.succeed() # Trigger the wait to end

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
            p2p_messages_sent=p2p_msgs, # Captures only this node's contribution
            gateway_was_up=gw_success,
            latency=detection_time - event.time,
            is_true_positive=(event.event_type == EventType.INTRUDER),
            confidence=confidence
        )
        self.network.report_detection(record)


class Environment:
    """Simulation environment: generates events."""

    def __init__(self, env: simpy.Environment, network: Network):
        self.env = env
        self.network = network
        self.events: List[SensorEvent] = []
        self.event_counter = 0

    def generate_events(self, count: int):
        self.env.process(self._event_generator(count))

    def _event_generator(self, count: int):
        for _ in range(count):
            interval = random.expovariate(1.0 / config.EVENT_INTERVAL_MEAN)
            yield self.env.timeout(interval)

            is_intruder = random.random() < config.INTRUDER_EVENT_PROB
            event_type = EventType.INTRUDER if is_intruder else EventType.NOISE
            
            event = SensorEvent(
                event_id=self.event_counter,
                event_type=event_type,
                time=self.env.now,
                position=(random.uniform(-25, 25), random.uniform(-25, 25)),
                duration=random.uniform(1, 5)
            )
            self.events.append(event)
            self.event_counter += 1
            self.network.dispatch_event_to_nodes(event)
