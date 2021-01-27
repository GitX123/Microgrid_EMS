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
C_CDG = [[140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5]]
C_SU = [2, 2,  2]
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

# --- Sets ---
model.ZeroOrOne = Set(initialize=[0, 1])

# --- Param ---
model.M = Param(initialize=1e9) # big M for indicator
 
# --- Variables ---
# CDG
# model.C_CDG = Var(I, T, within=NonNegativeReals)
model.P_CDG = Var(I, T, within=NonNegativeReals)
model.y = Var(I, T, within=model.ZeroOrOne) # start indicator
u0 = 0 # initial 
model.u = Var(I, T, within=model.ZeroOrOne, initialize=0)
# There following 2 variables are used for implementing a max function
model.i_1 = Var(I, T, within=model.ZeroOrOne)
model.i_2 = Var(I, T, within=model.ZeroOrOne)

# battery
model.P_B_ch = Var(T, within=NonNegativeReals)
model.P_B_dis = Var(T, within=NonNegativeReals)
SOC_B0 = 1 # initial SOC
model.SOC_Bp = Var(T, within=PercentFraction) # before self-discharge
model.SOC_B = Var(T, within=PercentFraction) # after self-discharge

# load
model.P_L_adj = Var(T, within=NonNegativeReals)
model.P_sh = Var(T, T, within=NonNegativeReals)

# transaction
model.P_short = Var(T, within=NonNegativeReals, initialize=0)
model.P_sur = Var(T, within=NonNegativeReals, initialize=0)

# --- Objective ---
def obj_rule(model):
    cdg_cost = 0.0
    for i in I:
        for t in T:
            cdg_cost += C_CDG[i][t] * model.P_CDG[i, t] + C_SU[i] * model.y[i, t]

    transaction_cost = 0.0
    for t in T:
        transaction_cost += PR_buy[t] * model.P_short[t] - PR_sell[t] * model.P_sur[t]

    load_shift_penalty = 0.0
    for t in T:
        for tp in T:
            if t != tp:
                load_shift_penalty += vt_t[t][tp] * model.P_sh[t, tp]

    obj = cdg_cost + transaction_cost + load_shift_penalty
    return obj
model.obj = Objective(rule=obj_rule, sense=minimize)

# --- Constraints ---
# CDG

# [ValueError]: non-fixed bound or weight, see: https://stackoverflow.com/questions/57065154/how-to-solve-non-fixed-bound-or-weight-using-pyomo-and-couenne-for-a-portfolio
# def cdg_power_limit_rule(model, i, t):
#     return (model.P_CDG[i, t] >= model.u[i, t] * P_min[i]) and (model.P_CDG[i, t] <= model.u[i, t] * P_max[i])
# model.cdg_power_limit = Constraint(I, T, rule=cdg_power_limit_rule)

# def cdg_cost_rule(model, i, t):
#     return model.C_CDG[i, t] == 0.5 * model.P_CDG[i, t] + 2.62
# model.cdg_cost = Constraint(I, T, rule=cdg_cost_rule)

def cdg_power_limit_rule1(model, i, t):
    return model.P_CDG[i, t] >= model.u[i, t] * P_min[i]
model.cdg_power_limit1 = Constraint(I, T, rule=cdg_power_limit_rule1)

def cdg_power_limit_rule2(model, i, t):
    return model.P_CDG[i, t] <= model.u[i, t] * P_max[i]
model.cdg_power_limit2 = Constraint(I, T, rule=cdg_power_limit_rule2)

# [Error] Avoid using max() (discontinuous, bad for optimizer), see: https://github.com/Pyomo/pyomo/issues/821

# def y_value_rule(model, i, t):
#     if t == 0:
#         return model.y[i, t] == max(value(model.u[i, t]) - u0, 0)
#     return model.y[i, t] == max(value(model.u[i, t]) - value(model.u[i, t-1]), 0)
# model.y_value = Constraint(I, T, rule=y_value_rule)

# [Error] Cannot select constraints based on vairables (unless only initial values are considered), see https://groups.google.com/g/pyomo-forum/c/SJpBPHZlk7Q/m/mrphT9xIZmoJ?pli=1, https://github.com/Pyomo/pyomo/issues/821
# def y_value_rule(model, i, t):
#     if t == 0:
#         if (value(model.u[i ,t]) - u0) > 0:
#             return model.y[i, t] == model.u[i ,t] - u0
#     else:
#         if (value(model.u[i, t]) - value(model.u[i, t-1])) > 0:
#             return model.y[i, t] == model.u[i, t] - model.u[i, t-1]
#     return model.y[i, t] == 0
# model.y_value = Constraint(I, T, rule=y_value_rule)

def y_value_rule1(model, i, t):
    if t == 0:
        return model.y[i, t] >= model.u[i ,t] - u0
    return model.y[i, t] >= model.u[i, t] - model.u[i, t-1]
model.y_value1 = Constraint(I, T, rule=y_value_rule1)

def y_value_rule2(model, i, t):
    return model.y[i, t] >= 0
model.y_value2 = Constraint(I, T, rule=y_value_rule2)

def y_value_rule3(model, i, t):
    if t == 0:
        return model.y[i, t] - model.M * (1 - model.i_1[i, t]) <= model.u[i, t] - u0
    return model.y[i, t] - model.M * (1 - model.i_1[i, t]) <= model.u[i, t] - model.u[i, t-1]
model.y_value3 = Constraint(I, T, rule=y_value_rule3)

def y_value_rule4(model, i, t):
    return model.y[i, t] - model.M * (1 - model.i_2[i, t]) <= 0
model.y_value4 = Constraint(I, T, rule=y_value_rule4)

def y_value_rule5(model, i, t):
    return model.i_1[i, t] + model.i_2[i, t] >= 1
model.y_value5 = Constraint(I, T, rule=y_value_rule5)

# Power

def power_balance_rule(model, t):
    return (P_pv[t] + P_wt[t] + sum(model.P_CDG[i, t] for i in I) + model.P_short[t] + model.P_B_dis[t]) \
            == (model.P_L_adj[t] + model.P_sur[t] + model.P_B_ch[t])
model.power_balance = Constraint(T, rule=power_balance_rule)

# Battery

# [WARNING] DEPRECATED: Chained inequalities are deprecated. Use the inequality()
# def charging_rule(model, t):
#     if t == 0:
#         return (model.P_B_ch[t] >= 0) and (model.P_B_ch[t] <= P_B_cap * (1 - SOC_B0) / (1 - L_B_ch) / ETA_BTB)
#     return (model.P_B_ch[t] >= 0) and (model.P_B_ch[t] <= P_B_cap * (1 - model.SOC_B[t-1]) / (1 - L_B_ch) / ETA_BTB)
# model.charging = Constraint(T, rule=charging_rule)

# [ValueError]: non-fixed bound or weight, expression cannot appear in lower or upper bounds for an inequality
# def charging_rule(model, t):
#     if t == 0:
#         return inequality(0, model.P_B_ch[t], P_B_cap * (1 - SOC_B0) / (1 - L_B_ch) / ETA_BTB)
#     return inequality(0, model.P_B_ch[t], P_B_cap * (1 - model.SOC_B[t-1]) / (1 - L_B_ch) / ETA_BTB)
# model.charging = Constraint(T, rule=charging_rule)

def charging_rule(model, t):
    if t == 0:
        return model.P_B_ch[t] <= P_B_cap * (1 - SOC_B0) / (1 - L_B_ch) / ETA_BTB
    return model.P_B_ch[t] <= P_B_cap * (1 - model.SOC_B[t-1]) / (1 - L_B_ch) / ETA_BTB
model.charging = Constraint(T, rule=charging_rule)

def discharging_rule(model, t):
    if t == 0:
        return model.P_B_dis[t] <= P_B_cap * SOC_B0 * (1 - L_B_dis) * ETA_BTB
    return model.P_B_dis[t] <= P_B_cap * model.SOC_B[t-1] * (1 - L_B_dis) * ETA_BTB
model.discharging = Constraint(T, rule=discharging_rule)

def b2b_charging_capacity_rule(model, t):
    return model.P_B_ch[t] <= P_BTB / ETA_BTB
model.b2b_charging_capacity = Constraint(T, rule=b2b_charging_capacity_rule)

def b2b_discharging_capacity_rule(model, t):
    return model.P_B_dis[t] <= P_BTB / ETA_BTB
model.b2b_discharging_capacity = Constraint(T, rule=b2b_discharging_capacity_rule)

def soc_update_rule(model, t):
    if t == 0:
        return model.SOC_B[t] == SOC_B0 - (1 / P_B_cap) * ((1 / (1 - L_B_dis) / ETA_BTB * model.P_B_dis[t]) - (model.P_B_ch[t] * (1 - L_B_ch) * ETA_BTB))
    return model.SOC_B[t] == model.SOC_B[t-1] - (1 / P_B_cap) * ((1 / (1 - L_B_dis) / ETA_BTB * model.P_B_dis[t]) - (model.P_B_ch[t] * (1 - L_B_ch) * ETA_BTB))
model.soc_update = Constraint(T, rule=soc_update_rule)

def self_dis_rule(model, t):
    return model.SOC_B[t] == (1 - DELTA_B) * model.SOC_Bp[t]
model.self_dis = Constraint(T, rule=self_dis_rule)

# Load

def load_shift_inflow_rule(model, t):
    inflow = 0.0
    for tp in T:
        if tp != t:
            inflow += model.P_sh[tp, t]
    return inflow <= IF_max[t]
model.load_shift_inflow = Constraint(T, rule=load_shift_inflow_rule)

def load_shift_outflow_rule(model, t):
    outflow = 0.0
    for tp in T:
        if tp != t:
            outflow += model.P_sh[t, tp]
    return outflow <= OF_max[t]
model.load_shift_outflow = Constraint(T, rule=load_shift_outflow_rule)

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