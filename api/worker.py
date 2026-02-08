"""
Background Worker
==================
Processes simulation jobs from the queue.
"""

import sys
import os
import time
import threading
from typing import Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from api.job_queue import JobQueue
from api.job_models import SimulationJob, JobStatus
from simulation.config_loader import load_config_from_json, SimulationConfig
from simulation.engine import run_simulation
from simulation.output_generator import generate_outputs


class SimulationWorker:
    """
    Background worker that processes simulation jobs.
    """
    
    def __init__(self, job_queue: JobQueue, poll_interval: float = 2.0):
        self.job_queue = job_queue
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the worker in a background thread."""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[Worker] Started background worker (poll interval: {self.poll_interval}s)")
    
    def stop(self):
        """Stop the worker."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        print("[Worker] Stopped")
    
    def _run_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                job = self.job_queue.get_next_pending_job()
                if job:
                    self._process_job(job)
                else:
                    time.sleep(self.poll_interval)
            except Exception as e:
                print(f"[Worker] Error in run loop: {e}")
                time.sleep(self.poll_interval)
    
    def _process_job(self, job: SimulationJob):
        """Process a single job."""
        print(f"[Worker] Processing job {job.job_id}")
        
        # Mark as running
        job = self.job_queue.start_job(job.job_id)
        if not job:
            print(f"[Worker] Failed to start job {job.job_id}")
            return
        
        try:
            # Load config from input params
            config = load_config_from_json(job.input_params)
            config.run_id = job.job_id  # Use job ID as run ID
            
            # Run simulation
            result = run_simulation(config)
            
            if not result["success"]:
                self.job_queue.fail_job(job.job_id, str(result.get("errors", "Unknown error")))
                return
            
            # Generate output artifacts
            output_dir = self.job_queue.get_job_output_dir(job.job_id)
            artifacts = generate_outputs(result, output_dir)
            
            # Mark as completed
            self.job_queue.complete_job(job.job_id, result, artifacts)
            print(f"[Worker] Completed job {job.job_id}")
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[Worker] Job {job.job_id} failed: {error_msg}")
            self.job_queue.fail_job(job.job_id, error_msg)
    
    def process_job_sync(self, job_id: str) -> bool:
        """Process a job synchronously (for testing)."""
        job = self.job_queue.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        
        self._process_job(job)
        return True


def run_worker_standalone(runs_dir: str = "runs"):
    """Run worker as standalone process."""
    job_queue = JobQueue(runs_dir)
    worker = SimulationWorker(job_queue)
    
    print("[Worker] Starting standalone worker...")
    print(f"[Worker] Monitoring directory: {os.path.abspath(runs_dir)}")
    
    worker.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Worker] Shutting down...")
        worker.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulation Worker")
    parser.add_argument("--runs-dir", type=str, default="runs", 
                        help="Directory for job runs")
    parser.add_argument("--poll-interval", type=float, default=2.0,
                        help="Polling interval in seconds")
    
    args = parser.parse_args()
    run_worker_standalone(args.runs_dir)
