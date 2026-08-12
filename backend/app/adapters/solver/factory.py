import os
from app.adapters.solver.base import BaseSolverAdapter
from app.adapters.solver.lsdyna import LSDynaAdapter
from app.adapters.solver.mock import MockSolverAdapter

def get_solver_adapter(solver_name: str = "LSDYNA") -> BaseSolverAdapter:
    solver_upper = solver_name.upper()
    app_env = os.getenv("APP_ENV", "development").lower()
    
    if solver_upper == "MOCK" or (app_env == "development" and solver_upper == "LSDYNA_MOCK"):
        return MockSolverAdapter(seed=42)
    elif solver_upper == "LSDYNA":
        # In development mode, use deterministic MockSolverAdapter to avoid pseudo-random non-deterministic noise
        if app_env == "development":
            return MockSolverAdapter(seed=42)
        return LSDynaAdapter()
    else:
        raise NotImplementedError(f"Solver adapter '{solver_name}' is not supported in V1.0.")
