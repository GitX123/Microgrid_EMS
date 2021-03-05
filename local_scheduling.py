'''
Description: Local Scheduling for a Single Microgrid
MG Comonents: Load, CDG, RDG(PV + WT), Battery
Unit: kWh
Objective: Minimize 1. CDG cost +  2. transaction cost +  3. load shift cost 
Param: 
'''

from pyomo.environ import *

def create_model(data):
    model = ConcreteModel(name='(L_S)')
    # --- Sets ---
    model.ZeroOrOne = Set(initialize=[0, 1])

    # --- Param ---
    model.M = Param(initialize=1e9) # big M for indicator
    
    # --- Variables ---
    # CDG
    # model.C_CDG = Var(I, T, within=NonNegativeReals)
    model.P_CDG = Var(data.I, data.T, within=NonNegativeReals)
    model.y = Var(data.I, data.T, within=model.ZeroOrOne) # start indicator
    u0 = 0 # initial 
    model.u = Var(data.I, data.T, within=model.ZeroOrOne, initialize=0)
    # There following 2 variables are used for implementing a max function
    model.i_1 = Var(data.I, data.T, within=model.ZeroOrOne)
    model.i_2 = Var(data.I, data.T, within=model.ZeroOrOne)

    # battery
    model.P_B_ch = Var(data.T, within=NonNegativeReals)
    model.P_B_dis = Var(data.T, within=NonNegativeReals)
    SOC_B0 = 1 # initial SOC
    model.SOC_Bp = Var(data.T, within=PercentFraction) # before self-discharge
    model.SOC_B = Var(data.T, within=PercentFraction) # after self-discharge

    # load
    model.P_L_adj = Var(data.T, within=NonNegativeReals)
    model.P_sh = Var(data.T, data.T, within=NonNegativeReals)

    # transaction
    model.P_short = Var(data.T, within=NonNegativeReals, initialize=0)
    model.P_sur = Var(data.T, within=NonNegativeReals, initialize=0)

    # --- Objective ---
    def obj_rule(model):
        cdg_cost = 0.0
        for i in data.I:
            for t in data.T:
                cdg_cost += data.C_CDG[i][t] * model.P_CDG[i, t] + data.C_SU[i] * model.y[i, t]

        transaction_cost = 0.0
        for t in data.T:
            transaction_cost += data.PR_buy[t] * model.P_short[t] - data.PR_sell[t] * model.P_sur[t]

        load_shift_penalty = 0.0
        for t in data.T:
            for tp in data.T:
                if t != tp:
                    load_shift_penalty += data.vt_t[t][tp] * model.P_sh[t, tp]

        obj = cdg_cost + transaction_cost + load_shift_penalty
        return obj
    model.obj = Objective(rule=obj_rule, sense=minimize)

    # --- Constraints ---
    # CDG

    def cdg_power_limit_rule1(model, i, t):
        return model.P_CDG[i, t] >= model.u[i, t] * data.P_min[i]
    model.cdg_power_limit1 = Constraint(data.I, data.T, rule=cdg_power_limit_rule1)

    def cdg_power_limit_rule2(model, i, t):
        return model.P_CDG[i, t] <= model.u[i, t] * data.P_max[i]
    model.cdg_power_limit2 = Constraint(data.I, data.T, rule=cdg_power_limit_rule2)

    def y_value_rule1(model, i, t):
        if t == 0:
            return model.y[i, t] >= model.u[i ,t] - u0
        return model.y[i, t] >= model.u[i, t] - model.u[i, t-1]
    model.y_value1 = Constraint(data.I, data.T, rule=y_value_rule1)

    def y_value_rule2(model, i, t):
        return model.y[i, t] >= 0
    model.y_value2 = Constraint(data.I, data.T, rule=y_value_rule2)

    def y_value_rule3(model, i, t):
        if t == 0:
            return model.y[i, t] - model.M * (1 - model.i_1[i, t]) <= model.u[i, t] - u0
        return model.y[i, t] - model.M * (1 - model.i_1[i, t]) <= model.u[i, t] - model.u[i, t-1]
    model.y_value3 = Constraint(data.I, data.T, rule=y_value_rule3)

    def y_value_rule4(model, i, t):
        return model.y[i, t] - model.M * (1 - model.i_2[i, t]) <= 0
    model.y_value4 = Constraint(data.I, data.T, rule=y_value_rule4)

    def y_value_rule5(model, i, t):
        return model.i_1[i, t] + model.i_2[i, t] >= 1
    model.y_value5 = Constraint(data.I, data.T, rule=y_value_rule5)

    # Power

    def power_balance_rule(model, t):
        return (data.P_pv[t] + data.P_wt[t] + sum(model.P_CDG[i, t] for i in data.I) + model.P_short[t] + model.P_B_dis[t]) \
                == (model.P_L_adj[t] + model.P_sur[t] + model.P_B_ch[t])
    model.power_balance = Constraint(data.T, rule=power_balance_rule)

    # Battery

    def charging_rule(model, t):
        if t == 0:
            return model.P_B_ch[t] <= data.P_B_cap * (1 - SOC_B0) / (1 - data.L_B_ch) / data.ETA_BTB
        return model.P_B_ch[t] <= data.P_B_cap * (1 - model.SOC_B[t-1]) / (1 - data.L_B_ch) / data.ETA_BTB
    model.charging = Constraint(data.T, rule=charging_rule)

    def discharging_rule(model, t):
        if t == 0:
            return model.P_B_dis[t] <= data.P_B_cap * SOC_B0 * (1 - data.L_B_dis) * data.ETA_BTB
        return model.P_B_dis[t] <= data.P_B_cap * model.SOC_B[t-1] * (1 - data.L_B_dis) * data.ETA_BTB
    model.discharging = Constraint(data.T, rule=discharging_rule)

    def b2b_charging_capacity_rule(model, t):
        return model.P_B_ch[t] <= data.P_BTB / data.ETA_BTB
    model.b2b_charging_capacity = Constraint(data.T, rule=b2b_charging_capacity_rule)

    def b2b_discharging_capacity_rule(model, t):
        return model.P_B_dis[t] <= data.P_BTB / data.ETA_BTB
    model.b2b_discharging_capacity = Constraint(data.T, rule=b2b_discharging_capacity_rule)

    def soc_update_rule(model, t):
        if t == 0:
            return model.SOC_B[t] == SOC_B0 - (1 / data.P_B_cap) * ((1 / (1 - data.L_B_dis) / data.ETA_BTB * model.P_B_dis[t]) - (model.P_B_ch[t] * (1 - data.L_B_ch) * data.ETA_BTB))
        return model.SOC_B[t] == model.SOC_B[t-1] - (1 / data.P_B_cap) * ((1 / (1 - data.L_B_dis) / data.ETA_BTB * model.P_B_dis[t]) - (model.P_B_ch[t] * (1 - data.L_B_ch) * data.ETA_BTB))
    model.soc_update = Constraint(data.T, rule=soc_update_rule)

    def self_dis_rule(model, t):
        return model.SOC_B[t] == (1 - data.DELTA_B) * model.SOC_Bp[t]
    model.self_dis = Constraint(data.T, rule=self_dis_rule)

    # Load

    def load_shift_inflow_rule(model, t):
        inflow = 0.0
        for tp in data.T:
            if tp != t:
                inflow += model.P_sh[tp, t]
        return inflow <= data.IF_max[t]
    model.load_shift_inflow = Constraint(data.T, rule=load_shift_inflow_rule)

    def load_shift_outflow_rule(model, t):
        outflow = 0.0
        for tp in data.T:
            if tp != t:
                outflow += model.P_sh[t, tp]
        return outflow <= data.OF_max[t]
    model.load_shift_outflow = Constraint(data.T, rule=load_shift_outflow_rule)

    def adj_load_rule(model, t):
        inflow = 0.0
        outflow = 0.0

        for tp in data.T:
            if tp != t:
                inflow += model.P_sh[tp, t]

        for tp in data.T:
            if tp != t:
                outflow += model.P_sh[t, tp]

        return model.P_L_adj[t] == data.P_L_fix[t] + data.OF_max[t] + inflow - outflow
    model.adj_load = Constraint(data.T, rule=adj_load_rule)

    return model