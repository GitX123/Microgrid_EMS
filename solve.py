from pyomo.environ import *
import matplotlib.pyplot as plt
import data, local_scheduling, global_scheduling

solver = SolverFactory('glpk')

# [TODO]
def mg_info():
    pass

# --- Scheduling ---
def run_scheduling():
    for t in data.T:
        # Local scheduling
        model = local_scheduling.create_model(data)
        solver.solve(model)

        # [TODO]
        # MG info

        # Global scheduling 

        # Local rescheduling

if __name__ == '__main__':
    run_scheduling()