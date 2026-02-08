# web/simulation_manager.py
import math
from config_mirror import *
from fsm import NodeFSM

class SimulationManager:
    def __init__(self, socketio):
        self.socketio = socketio
        self.nodes = {}
        self.alert_level = "NONE"
        
        # Stats
        self.stats = {
            "boar_injections": 0,
            "noise_injections": 0,
            "detected_boars": 0,
            "active_boar_detections": set(), # Track which injection id triggers alert
            "false_alerts": 0
        }
        self.current_event_id = 0
        
        self._init_nodes()

    def _init_nodes(self):
        # Create Outer Ring
        for i in range(NODE_COUNT_OUTER):
            nid = f"outer_{i}"
            self.nodes[nid] = NodeFSM(nid, "outer", self.socketio, self)
            # Assign geometric properties (for distance calc)
            angle = i * (360 / NODE_COUNT_OUTER)
            rad = math.radians(angle)
            self.nodes[nid].x = OUTER_RING_RADIUS * math.cos(rad)
            self.nodes[nid].y = OUTER_RING_RADIUS * math.sin(rad)
            self.nodes[nid].angle = angle  # Store angle for FOV

        # Create Inner Ring
        for i in range(NODE_COUNT_INNER):
            nid = f"inner_{i}"
            self.nodes[nid] = NodeFSM(nid, "inner", self.socketio, self)
            angle = i * (360 / NODE_COUNT_INNER) + INNER_RING_OFFSET
            rad = math.radians(angle)
            self.nodes[nid].x = INNER_RING_RADIUS * math.cos(rad)
            self.nodes[nid].y = INNER_RING_RADIUS * math.sin(rad)
            self.nodes[nid].angle = angle  # Store angle for FOV
            
        # Compute Neighbors (Simple distance based)
        for nid, node in self.nodes.items():
            neighbors = []
            for other_id, other in self.nodes.items():
                if nid == other_id: continue
                dist = math.sqrt((node.x - other.x)**2 + (node.y - other.y)**2)
                # Assume range covers adjacent nodes ~100px (approx 30m scaled)
                if dist < 120: 
                    neighbors.append(other)
            node.set_neighbors(neighbors)

    def inject_event(self, x, y, type):
        """Trigger nodes near the click location"""
        self.current_event_id += 1
        
        if type == 'boar':
            self.stats['boar_injections'] += 1
        else:
            self.stats['noise_injections'] += 1
            
        triggered_count = 0
        for node in self.nodes.values():
            dist = math.sqrt((node.x - x)**2 + (node.y - y)**2)
            if dist < SENSOR_RANGE: # Sensor Range
                node.trigger_event(type, self.current_event_id)
                triggered_count += 1
        return triggered_count

    def report_alert(self, type, event_id):
        """Called by NodeFSM when it alerts"""
        if type == 'boar':
            # Only count as 1 detection per injection event, even if multiple nodes alert
            if event_id not in self.stats['active_boar_detections']:
                self.stats['detected_boars'] += 1
                self.stats['active_boar_detections'].add(event_id)
        elif type == 'false_alarm':
             # For false alarms, every alert is bad, but usually we just track rate
             self.stats['false_alerts'] += 1

    def get_system_state(self):
        """Snapshot for Frontend"""
        # Check global alert level
        active_alerts = [n for n in self.nodes.values() if n.state == "ALERT"]
        if len(active_alerts) > 1:
            self.alert_level = "LEVEL_2" # Ultrasonic
        elif len(active_alerts) == 1:
            self.alert_level = "LEVEL_1" # Light/Siren
        else:
            self.alert_level = "NONE"
            
        # Calculate Rates
        dr = 0
        if self.stats['boar_injections'] > 0:
            dr = (self.stats['detected_boars'] / self.stats['boar_injections']) * 100
            
        fpr = 0
        if self.stats['noise_injections'] > 0:
            fpr = (self.stats['false_alerts'] / self.stats['noise_injections']) * 100

        return {
            "nodes": [
                {
                    "id": n.id,
                    "state": n.state,
                    "battery": round(n.battery, 1),
                    "x": n.x, 
                    "y": n.y,
                    "angle": n.angle  # For FOV rendering
                } for n in self.nodes.values()
            ],
            "alert_level": self.alert_level,
            "stats": {
                "detection_rate": round(dr, 1),
                "fp_rate": round(fpr, 1)
            }
        }
