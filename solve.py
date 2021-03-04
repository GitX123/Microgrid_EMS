from pyomo.environ import *
import matplotlib.pyplot as plt
from local_scheduling import model, I, T, P_pv

solver = SolverFactory('glpk')
solver.solve(model)

# --- Plot ---
# Power
load = [value(model.P_L_adj[t]) for t in T]
dg = [3 * value(model.P_CDG[0, t]) for t in T]
battery = [value(model.P_B_dis[t]) - value(model.P_B_ch[t]) for t in T]
grid = [value(model.P_short[t]) - value(model.P_sur[t]) for t in T]

plt.title('Load, PV, DG, Battery, Grid (Power)')
plt.xlabel('Time (hr)')
plt.ylabel('Power (kWh)')
plt.step(T, load, label='Load')
plt.step(T, P_pv, label='PV')
plt.step(T, dg, label='DG')
plt.step(T, battery, label='Battery')
plt.step(T, grid, label='Grid')
plt.legend()
plt.show()

print(value(model.obj))