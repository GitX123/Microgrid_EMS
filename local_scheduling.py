'''
Description: Local Scheduling for a Single Microgrid
MG Comonents: Load, CDG, RDG(PV + WT), Battery
Unit: kWh
Objective: Minimize 1. CDG cost +  2. transaction cost +  3. load shift cost 
'''

from pyomo.environ import *
import numpy as np
import pandas as pd

# --- Model ---
model = ConcreteModel(name='(L_S)')

# --- Data ---
# Index
I = [i for i in range(3)] # CDG units
T = [t for t in range(24)] # time horizon

# CDG
C_CDG = [155, 155, 155]
C_SU = [200, 200,  200]
P_min = [0, 0, 0]
P_max = [500, 500, 500]

# buying & selling price
PR_buy = [155 for t in T]
PR_sell = [152.5 for t in T]

# renewable (forecasted output)
pv_ref = 500
pv_data = pd.read_csv('miris_pv.csv').to_numpy()
pv_data = pv_data[:17280, 1] # extract 1 day data
pv_data = np.mean(pv_data.reshape(-1, 720), axis=1) # average to have 1-hour resolution
pv_data = pv_ref * pv_data / np.amax(pv_data) # normalize
P_pv = pv_data.tolist()

P_wt = [0 for t in T]

# load
load_fix_ref = 2000
load_fix_data = pd.read_csv('miris_load.csv').to_numpy()
load_fix_data = load_fix_data[:17280, 1]
load_fix_data = np.mean(load_fix_data.reshape(-1, 720), axis=1) # average
load_fix_data = load_fix_ref * load_fix_data / np.amax(load_fix_data) # normalize
P_L_fix = load_fix_data.tolist()

vt_t = [[0 for tp in T] for t in T] # penalty of load shifting
IF_max = [0, 0, 0, 0, 0, 0, 0, 0, 90, 35, 0, 105, 41, 36, 51, 59, 45, 13, 0, 8, 0, 0, 0, 0]
OF_max = [0, 0, 0, 0, 0, 0, 0, 0, 410, 465, 500, 395, 459, 464, 449, 441, 455, 487, 500, 492, 0, 0, 0, 0]

# battery
L_B_ch = 0.03
L_B_dis = 0.03
P_B_cap = 200 
P_BTB = 200
ETA_BTB = 0.98
DELTA_B = 0.03
 
# --- Variables ---
# CDG
model.P_CDG = Var(I, T)
model.y = Var(I, T)
model.u = Var(I, T, within=[0, 1])

# battery
model.P_B_ch = Var(T)
model.P_B_dis = Var(T)
model.SOC_Bp = Var(T) # before self-discharge
model.SOC_B = Var(T, within=NonNegativeReals, bounds=(0, 1)) # after self-discharge

# load
model.P_L_adj = Var(T)
model.P_sh = Var(T, T)

# transaction
model.P_short = Var(T)
model.P_sur = Var(T)

# --- Objective ---
def obj_rule(model):
    penalty_load_shift = 0.0
    for t in T:
        for tp in T:
            if t != tp:
                penalty_load_shift += vt_t[t, tp] * model.P_sh[t, tp]
    obj = sum(sum(C_CDG[i] * model.P_CDG[i, t] + C_SU[i] * model.y[i, t] for i in I for t in T) + sum(PR_buy[t] * model.P_short[t] - PR_sell[t] * model.P_sur[t] for t in T) + penalty_load_shift)
    return obj
model.obj = Objective(rule=obj_rule)

# --- Constraints ---
# CDG
def cdg_power_limit_rule(model, i, t):
    return (model.P_CDG[i, t] >= model.u[i, t] * P_min[i]) and (model.P_CDG[i, t] <= model.u[i, t] * P_max[i])
model.cdg_power_limit = Constraint(I, T, rule=cdg_power_limit_rule)

def y_value_rule(model, i, t):
    return model.y[i, t] == max(model.u[i, t] - model.u[i, t-1], 0)
model.y_value = Constraint(I, T, rule=y_value_rule)

def power_balance_rule(model, t):
    return (P_pv[t] + P_wt[t] + sum(model.P_CDG[i, t] for i in I) + model.P_short[t] + model.P_B_dis[t]) \
            == (model.P_L_adj[t] + model.P_sur[t] + model.P_B_ch[t])
model.power_balance = Constraint(T, rule=power_balance_rule)

# Battery
def charging_rule(model, t):
    return (model.P_B_ch[t] >= 0) and (model.P_B_ch[t] <= P_B_cap * (1 - model.SOC_B[t-1]) / (1 - L_B_ch) / ETA_BTB)
model.charging = Constraint(T, rule=charging_rule)

def discharging_rule(model, t):
    return (model.P_B_dis[t] >= 0) and (model.P_B_dis[t] <= P_B_cap * model.SOC_B[t-1] * (1 - L_B_dis) * ETA_BTB)
model.discharging = Constraint(T, rule=discharging_rule)

def b2b_capacity_rule(model, t):
    return (model.P_B_ch[t] <= P_BTB / ETA_BTB) and (model.P_B_dis[t] <= P_BTB / ETA_BTB)
model.b2b_capacity = Constraint(T, rule=b2b_capacity_rule)

def soc_update_rule(model, t):
    return model.SOC_B[t] == model.SOC_B[t - 1] - (1 / P_B_cap) * ((1 / (1 - L_B_dis) / ETA_BTB * model.P_B_dis[t]) - (model.P_B_ch[t] * (1 - L_B_ch) * ETA_BTB))
model.soc_update = Constraint(T, rule=soc_update_rule)

def self_dis_rule(model, t):
    return model.SOC_B[t] == (1 - DELTA_B) * model.SOC_Bp[t]
model.self_dis = Constraint(T, rule=self_dis_rule)

# Load
def load_shift_capacity_rule(model, t):
    inflow = 0.0
    outflow = 0.0

    for tp in T:
        if tp != t:
            inflow += model.P_sh[tp, t]

    for tp in T:
        if tp != t:
            outflow += model.P_sh[t, tp]
    
    return (inflow <= IF_max) and (outflow <= OF_max)
model.load_shift = Constraint(T, rule=load_shift_capacity_rule)

def adj_load_rule(model, t):
    inflow = 0.0
    outflow = 0.0

    for tp in T:
        if tp != t:
            inflow += model.P_sh[tp, t]

    for tp in T:
        if tp != t:
            outflow += model.P_sh[t, tp]

    return model.P_L_adj[t] == P_L_fix[t] + OF_max[t] + inflow - outflow
model.adj_load = Constraint(T, rule=adj_load_rule)