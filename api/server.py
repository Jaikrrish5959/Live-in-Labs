"""
REST API Server
===============
Flask-based REST API for simulation job management.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

from api.job_queue import JobQueue
from api.job_models import JobStatus
from api.worker import SimulationWorker


# Initialize Flask app
app = Flask(__name__, 
            static_folder=os.path.join(project_root, 'web_batch', 'static'),
            template_folder=os.path.join(project_root, 'web_batch', 'templates'))
CORS(app)

# Initialize job queue and worker
RUNS_DIR = os.path.join(project_root, 'runs')
job_queue = JobQueue(RUNS_DIR)
worker = SimulationWorker(job_queue)


# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """
    Submit a new simulation job.
    
    Request body: JSON with simulation parameters
    Response: Job ID and status
    """
    try:
        input_params = request.get_json() or {}
        job = job_queue.create_job(input_params)
        
        return jsonify({
            "success": True,
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Job submitted successfully"
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """
    Get status of a simulation job.
    
    Response: Job status and metadata
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        return jsonify({
            "success": False,
            "error": "Job not found"
        }), 404
    
    response = {
        "success": True,
        "job_id": job.job_id,
        "status": job.status.value,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }
    
    if job.status == JobStatus.FAILED:
        response["error"] = job.error_message
    
    if job.status == JobStatus.COMPLETED:
        response["artifacts"] = list(job.artifacts.keys())
    
    return jsonify(response)


@app.route('/api/jobs/<job_id>/results', methods=['GET'])
def get_job_results(job_id: str):
    """
    Get results of a completed simulation job.
    
    Response: Full simulation results including metrics
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        return jsonify({
            "success": False,
            "error": "Job not found"
        }), 404
    
    if job.status != JobStatus.COMPLETED:
        return jsonify({
            "success": False,
            "error": f"Job is not completed (status: {job.status.value})"
        }), 400
    
    # Load metrics and summary from disk
    output_dir = job_queue.get_job_output_dir(job_id)
    
    metrics = {}
    summary = {}
    
    metrics_path = os.path.join(output_dir, "metrics.json")
    if os.path.exists(metrics_path):
        import json
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
    
    summary_path = os.path.join(output_dir, "summary.json")
    if os.path.exists(summary_path):
        import json
        with open(summary_path, 'r') as f:
            summary = json.load(f)
    
    return jsonify({
        "success": True,
        "job_id": job.job_id,
        "status": job.status.value,
        "metrics": metrics,
        "summary": summary,
        "artifacts": list(job.artifacts.keys())
    })


@app.route('/api/jobs/<job_id>/artifacts/<filename>', methods=['GET'])
def get_artifact(job_id: str, filename: str):
    """
    Download an artifact file.
    """
    job = job_queue.get_job(job_id)
    
    if not job:
        return jsonify({
            "success": False,
            "error": "Job not found"
        }), 404
    
    output_dir = job_queue.get_job_output_dir(job_id)
    file_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(file_path):
        return jsonify({
            "success": False,
            "error": f"Artifact '{filename}' not found"
        }), 404
    
    # Determine content type
    if filename.endswith('.png'):
        mimetype = 'image/png'
    elif filename.endswith('.json'):
        mimetype = 'application/json'
    else:
        mimetype = 'application/octet-stream'
    
    return send_file(file_path, mimetype=mimetype)


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """
    List recent jobs.
    """
    limit = request.args.get('limit', 20, type=int)
    jobs = job_queue.list_jobs(limit=limit)
    
    return jsonify({
        "success": True,
        "jobs": [j.to_dict() for j in jobs]
    })


# ============================================================================
# Web UI Routes
# ============================================================================

@app.route('/')
def index():
    """Serve the main web UI."""
    from flask import render_template
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# Main
# ============================================================================

def run_server(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """Run the API server with background worker."""
    print(f"[Server] Starting API server on http://{host}:{port}")
    print(f"[Server] Runs directory: {RUNS_DIR}")
    
    # Start worker
    worker.start()
    
    # Run Flask
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulation API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    run_server(args.host, args.port, args.debug)
