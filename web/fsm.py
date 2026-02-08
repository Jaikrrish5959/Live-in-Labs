# web/fsm.py
import random
import time
import eventlet
from config_mirror import *

class NodeFSM:
    def __init__(self, node_id, ring_type, socketio, manager):
        self.id = node_id
        self.ring_type = ring_type
        self.socketio = socketio
        self.manager = manager
        
        # State
        self.state = "IDLE"  # IDLE, PIR, THERMAL, CAMERA, VOTING, ALERT
        self.battery = 100.0
        self.last_update = time.time()
        
        # Simulation Flags
        self.active_intrusion_type = None  # 'boar' or 'false_alarm'
        self.current_event_id = None
        self.votes_received = 0
        self.neighbors = []

    def set_neighbors(self, neighbors):
        self.neighbors = neighbors

    def trigger_event(self, intrusion_type, event_id):
        """External trigger (e.g., mouse click)"""
        if self.state != "IDLE":
            return # Busy
        
        self.active_intrusion_type = intrusion_type
        self.current_event_id = event_id
        self.transition_to("PIR")
        
        # Start async FSM loop
        eventlet.spawn(self._run_fsm_cycle)

    def transition_to(self, new_state):
        self.state = new_state
        self._consume_battery(new_state)
        self._emit_update()

    def _consume_battery(self, state):
        cost = {
            "IDLE": BATTERY_DRAIN_IDLE,
            "PIR": BATTERY_DRAIN_PIR,
            "THERMAL": BATTERY_DRAIN_THERMAL,
            "CAMERA": BATTERY_DRAIN_CAMERA,
            "VOTING": BATTERY_DRAIN_RADIO,
            "ALERT": BATTERY_DRAIN_RADIO
        }.get(state, 0)
        self.battery = max(0, self.battery - cost)

    def _emit_update(self):
        # We don't emit individually to avoid flooding;
        # The SimulationManager will gather states.
        pass

    def _run_fsm_cycle(self):
        """Async Logic Flow"""
        
        # 1. PIR Stage
        eventlet.sleep(PIR_DELAY)
        
        # False Alarm Check (PIR is sensitive, triggers often)
        # Proceed to Thermal
        self.transition_to("THERMAL")
        eventlet.sleep(THERMAL_DELAY)
        
        # 2. Thermal Stage
        if self.active_intrusion_type == 'false_alarm':
            # 50% chance to fail here (e.g., wind has no heat)
            if random.random() < 0.5:
                self._reset()
                return
        
        self.transition_to("CAMERA")
        eventlet.sleep(CAMERA_DELAY)
        
        # 3. Camera Stage
        if self.active_intrusion_type == 'false_alarm':
            # 90% chance to fail here (AI sees no boar)
            if random.random() < 0.9:
                self._reset()
                return

        # 4. Voting Stage
        self.transition_to("VOTING")
        self.request_votes()
        
        # Wait for votes
        eventlet.sleep(VOTING_TIMEOUT)
        
        # Final Decision
        if self.votes_received >= VOTE_CONFIRM_THRESHOLD:
            self.transition_to("ALERT")
            self.manager.report_alert(self.active_intrusion_type, self.current_event_id)
            eventlet.sleep(5.0) # Stay alerting for 5s
        
        self._reset()

    def request_votes(self):
        """Simulate P2P Voting"""
        # In a real sim, we'd ask neighbors. 
        # Here, we 'simulate' their response based on their proximity to the event
        # For simplicity in this demo: If neighbor is also PIR/THERMAL/CAMERA/VOTING, they vote YES
        
        # Notify SimulationManager to draw lines
        self.socketio.emit('visualize_voting', {'source': self.id, 'targets': [n.id for n in self.neighbors]})
        
        votes = 0
        for neighbor in self.neighbors:
            if neighbor.state in ["PIR", "THERMAL", "CAMERA", "VOTING", "ALERT"]:
                votes += 1
        
        self.votes_received = votes

    def _reset(self):
        self.state = "IDLE"
        self.active_intrusion_type = None
        self.votes_received = 0
        self._emit_update()

