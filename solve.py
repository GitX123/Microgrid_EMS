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
        P_sur, P_short, P_adj_min, P_adj_max = mg_info(model)

        # Global scheduling 
        model = global_scheduling.create_model(data, P_sur, P_short, P_adj_min, P_adj_max)
        solver.solve(model)

        # Local rescheduling
        

if __name__ == '__main__':
    run_scheduling()