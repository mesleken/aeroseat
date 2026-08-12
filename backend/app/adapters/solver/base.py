from abc import ABC, abstractmethod
from typing import NamedTuple, Any

class PreparedInput(NamedTuple):
    input_deck_uri: str
    input_deck_hash: str
    metadata: dict[str, Any]

class ComputeConfiguration(NamedTuple):
    num_cores: int = 16
    walltime_hours: float = 4.0
    memory_gb: int = 32

class ExternalJobRef(NamedTuple):
    job_id: str
    cluster_name: str
    working_dir: str

class SolverStatus(NamedTuple):
    status_code: str # RUNNING, COMPLETED, FAILED
    progress_pct: float
    error_message: str | None = None

class RawSimulationOutput(NamedTuple):
    d3plot_uri: str
    binout_uri: str
    output_sha256: str
    timeseries_data: dict[str, Any]

class BaseSolverAdapter(ABC):
    """Abstract Solver Adapter Interface (Contract 3).
    
    Guarantees that core application logic remains solver-agnostic.
    """
    
    @abstractmethod
    def prepare_input(self, config_data: dict) -> PreparedInput:
        """Prepares input deck files for the specific FE solver."""
        pass

    @abstractmethod
    def submit_job(self, prepared: PreparedInput, compute: ComputeConfiguration) -> ExternalJobRef:
        """Submits the job to the HPC compute node / solver execution engine."""
        pass

    @abstractmethod
    def poll_status(self, ref: ExternalJobRef) -> SolverStatus:
        """Polls execution status of the running solver job."""
        pass

    @abstractmethod
    def parse_results(self, ref: ExternalJobRef) -> RawSimulationOutput:
        """Parses binary or text output files produced by the solver into unified datastructures."""
        pass
