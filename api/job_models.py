"""
Job Models
==========
Data models for simulation jobs.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid


class JobStatus(str, Enum):
    """Status of a simulation job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationJob:
    """Represents a simulation job in the queue."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Input
    input_params: Dict[str, Any] = field(default_factory=dict)
    
    # Output
    result: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, str] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "input_params": self.input_params,
            "artifacts": self.artifacts,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationJob':
        """Create job from dictionary."""
        return cls(
            job_id=data.get("job_id", str(uuid.uuid4())),
            status=JobStatus(data.get("status", "pending")),
            created_at=data.get("created_at", datetime.now().isoformat()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            input_params=data.get("input_params", {}),
            result=data.get("result"),
            artifacts=data.get("artifacts", {}),
            error_message=data.get("error_message")
        )


@dataclass
class JobSubmission:
    """Input for creating a new job."""
    simulation: Dict[str, Any] = field(default_factory=dict)
    topology: Dict[str, Any] = field(default_factory=dict)
    decision_logic: Dict[str, Any] = field(default_factory=dict)
    image_model: Dict[str, Any] = field(default_factory=dict)
    communication: Dict[str, Any] = field(default_factory=dict)
    gateway: Dict[str, Any] = field(default_factory=dict)
    random_seed: Optional[int] = None
    
    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to config dictionary for simulation engine."""
        config = {}
        
        if self.random_seed is not None:
            config["random_seed"] = self.random_seed
        
        if self.simulation:
            config["simulation"] = self.simulation
        if self.topology:
            config["topology"] = self.topology
        if self.decision_logic:
            config["decision_logic"] = self.decision_logic
        if self.image_model:
            config["image_model"] = self.image_model
        if self.communication:
            config["communication"] = self.communication
        if self.gateway:
            config["gateway"] = self.gateway
        
        return config
