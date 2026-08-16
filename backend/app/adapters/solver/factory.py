import os
from app.adapters.solver.base import BaseSolverAdapter
from app.adapters.solver.lsdyna import LSDynaAdapter
from app.adapters.solver.mock import MockSolverAdapter
from app.adapters.solver.physics_solver import PhysicsSolverAdapter

def get_solver_adapter(solver_name: str = "PHYSICS_LUMPED_MASS") -> BaseSolverAdapter:
    solver_upper = (solver_name or "PHYSICS_LUMPED_MASS").upper()
    
    if solver_upper == "MOCK":
        return MockSolverAdapter(seed=42)
    elif solver_upper == "LSDYNA":
        lsdyna_exec = os.getenv("LSDYNA_EXEC_PATH")
        if lsdyna_exec and os.path.exists(lsdyna_exec):
            return LSDynaAdapter()
        # Fallback to multi-DOF explicit physics crash solver in local environment
        return PhysicsSolverAdapter(seed=42)
    else:
        return PhysicsSolverAdapter(seed=42)
