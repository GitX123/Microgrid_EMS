from pyomo.environ import *
import matplotlib.pyplot as plt
import local_scheduling, global_scheduling
import data, data.mg1, data.mg2, data.mg3 

solver = SolverFactory('glpk')
mg_data = [data.mg1, data.mg2, data.mg3]

# [TODO]
def mg_info(models):
    P_sur, P_short = [], []
    P_adj_min, P_adj_max = [], []

    for t in data.T:
        for model_i, model in enumerate(models):
            generation_load_difference = sum(value(model.P_CDG[i, t]) for i in data.I) + mg_data[model_i].P_pv[t] + mg_data[model_i].P_wt[t] - value(model.P_L_adj[t])

            if generation_load_difference > 0:
                pass
            else:
                pass
    
    return P_sur, P_short, P_adj_min, P_adj_max

# --- Scheduling ---
def run_scheduling():
    for t in data.T:
        # Local scheduling
        model_mg1 = local_scheduling.create_model(data.mg1)
        solver.solve(model_mg1)
        model_mg2 = local_scheduling.create_model(data.mg2)
        solver.solve(model_mg2)
        model_mg3 = local_scheduling.create_model(data.mg3)
        solver.solve(model_mg3)
        models = [model_mg1, model_mg2, model_mg3]

        # [TODO]
        # MG info
        P_sur, P_short, P_adj_min, P_adj_max = mg_info(models)

        # # Global scheduling 
        # model = global_scheduling.create_model(data, P_sur, P_short, P_adj_min, P_adj_max)
        # solver.solve(model)

        # # Local rescheduling
        

if __name__ == '__main__':
    run_scheduling()