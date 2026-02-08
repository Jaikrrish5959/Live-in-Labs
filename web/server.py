# web/server.py
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import eventlet
import os

# Initialize Flask + SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Initialize Simulation Manager
from simulation_manager import SimulationManager
sim_manager = SimulationManager(socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/api/stats')
def get_stats():
    """API endpoint for current simulation statistics"""
    state = sim_manager.get_system_state()
    return {
        "detection_rate": state["stats"]["detection_rate"],
        "false_positive_rate": state["stats"]["fp_rate"],
        "boar_injections": sim_manager.stats["boar_injections"],
        "noise_injections": sim_manager.stats["noise_injections"],
        "detected_boars": sim_manager.stats["detected_boars"],
        "false_alerts": sim_manager.stats["false_alerts"],
        "alert_level": state["alert_level"]
    }

@app.route('/data/log')
def get_log():
    return send_from_directory('static/data', 'simulation_log.json')

# --- SocketIO Events ---

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send initial state
    emit('state_update', sim_manager.get_system_state())

@socketio.on('inject_event')
def handle_injection(data):
    print(f"Injection received: {data}")
    # data = {x: float, y: float, type: 'boar'|'false_alarm'}
    triggered = sim_manager.inject_event(data['x'], data['y'], data['type'])
    emit('log_message', {'msg': f"Event Injected: {data['type']} (Triggered {triggered} nodes)"})

# --- Background Loop ---
def background_loop():
    while True:
        socketio.sleep(0.1) # 10Hz update rate
        state = sim_manager.get_system_state()
        socketio.emit('state_update', state)

if __name__ == '__main__':
    print("Starting Interactive Simulator on http://localhost:5000")
    socketio.start_background_task(background_loop)
    socketio.run(app, debug=True, port=5000)
