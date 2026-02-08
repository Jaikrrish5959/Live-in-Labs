"""
Job Queue
=========
File-based job queue for simulation jobs.
"""

import json
import os
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime

from .job_models import SimulationJob, JobStatus


class JobQueue:
    """
    File-based job queue.
    Jobs are stored as JSON files in the runs directory.
    """
    
    def __init__(self, runs_dir: str):
        self.runs_dir = runs_dir
        self.lock = threading.Lock()
        os.makedirs(runs_dir, exist_ok=True)
    
    def _job_dir(self, job_id: str) -> str:
        """Get directory path for a job."""
        return os.path.join(self.runs_dir, job_id)
    
    def _job_file(self, job_id: str) -> str:
        """Get job metadata file path."""
        return os.path.join(self._job_dir(job_id), "job.json")
    
    def create_job(self, input_params: Dict[str, Any]) -> SimulationJob:
        """Create a new job and add to queue."""
        with self.lock:
            job = SimulationJob(input_params=input_params)
            
            # Create job directory
            job_dir = self._job_dir(job.job_id)
            os.makedirs(job_dir, exist_ok=True)
            
            # Save job metadata
            self._save_job(job)
            
            return job
    
    def _save_job(self, job: SimulationJob):
        """Save job to disk."""
        job_file = self._job_file(job.job_id)
        with open(job_file, 'w') as f:
            json.dump(job.to_dict(), f, indent=2)
    
    def get_job(self, job_id: str) -> Optional[SimulationJob]:
        """Get job by ID."""
        job_file = self._job_file(job_id)
        if not os.path.exists(job_file):
            return None
        
        with open(job_file, 'r') as f:
            data = json.load(f)
        return SimulationJob.from_dict(data)
    
    def update_job(self, job: SimulationJob):
        """Update job status."""
        with self.lock:
            self._save_job(job)
    
    def get_pending_jobs(self) -> List[SimulationJob]:
        """Get all pending jobs (oldest first)."""
        jobs = []
        
        if not os.path.exists(self.runs_dir):
            return jobs
        
        for job_id in os.listdir(self.runs_dir):
            job = self.get_job(job_id)
            if job and job.status == JobStatus.PENDING:
                jobs.append(job)
        
        # Sort by creation time (oldest first)
        jobs.sort(key=lambda j: j.created_at)
        return jobs
    
    def get_next_pending_job(self) -> Optional[SimulationJob]:
        """Get the oldest pending job."""
        pending = self.get_pending_jobs()
        return pending[0] if pending else None
    
    def start_job(self, job_id: str) -> Optional[SimulationJob]:
        """Mark job as running."""
        with self.lock:
            job = self.get_job(job_id)
            if job and job.status == JobStatus.PENDING:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now().isoformat()
                self._save_job(job)
                return job
        return None
    
    def complete_job(self, job_id: str, result: Dict[str, Any], 
                     artifacts: Dict[str, str]):
        """Mark job as completed with results."""
        with self.lock:
            job = self.get_job(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now().isoformat()
                job.result = result
                job.artifacts = artifacts
                self._save_job(job)
    
    def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed."""
        with self.lock:
            job = self.get_job(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now().isoformat()
                job.error_message = error_message
                self._save_job(job)
    
    def list_jobs(self, limit: int = 50) -> List[SimulationJob]:
        """List recent jobs."""
        jobs = []
        
        if not os.path.exists(self.runs_dir):
            return jobs
        
        for job_id in os.listdir(self.runs_dir):
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]
    
    def get_job_output_dir(self, job_id: str) -> str:
        """Get output directory for a job."""
        return self._job_dir(job_id)
