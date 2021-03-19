'''
Description: Global scheduling operated by DSO

'''

from pyomo.environ import *

def create_model(data, P_sur, P_short, P_adj_min, P_adj_max):
    # --- Model --- 
    model = ConcreteModel(name='(G_S)')

    # --- Variable ---
    # CDG
    model.P_CDGP = Var(data.T, within=NonNegativeReals)
    model.P_adj = Var(data.K, data.I, data.T, within=NonNegativeReals)

    # transaction
    model.P_buy = Var(data.K, data.T, within=NonNegativeReals)
    model.P_sell = Var(data.K, data.T, within=NonNegativeReals)

    # CBESS
    model.P_CB_ch = Var(data.T, within=NonNegativeReals)
    model.P_CB_dis = Var(data.T, within=NonNegativeReals)
    model.SOC_CB = Var(data.T, within=PercentFraction)
    model.SOC_CBp = Var(data.T, within=PercentFraction)

    # --- Objective ---
    def obj_rule(model):
        cdgp_cost = 0.0
        for t in data.T:
            cdgp_cost += data.C_CDGP[t] * model.P_CDGP[t]
        
        power_adjust_cost = 0.0
        for k in data.K:
            for i in data.I:
                for t in data.T:
                    power_adjust_cost += data.C_CDG[k][i][t] * model.P_adj[k, i, t]
        
        transaction_cost = 0.0
        for k in data.K:
            for t in data.T:
                transaction_cost += data.PR_buy[t] * model.P_buy[k, t] - data.PR_sell[t] * model.P_sell[k, t]

        obj = cdgp_cost + power_adjust_cost + transaction_cost
        return obj
    model.obj = Objective(rule=obj_rule, sense=minimize)

    # --- Constraints ---
    # CDGP
    def cdgp_power_limit_rule(model, t):
        return data.P_CDGP_min <= model.P_CDGP[t] <= data.P_CDGP_max
    model.cdgp_power_limit = Constraint(data.T, rule=cdgp_power_limit_rule)

    # power adjustment
    def power_adjust_limit_rule(model, k, i, t):
        return P_adj_min[k][i][t] <= model.P_adj[k, i, t] <= P_adj_max[k][i][t]
    model.power_adjust_limit = Constraint(data.K, data.I, data.T, rule=power_adjust_limit_rule)

    # power balance
    def power_balance_rule(model, t):
        return (model.P_CDGP[t] + sum(model.P_buy[k ,t] for k in data.K) + sum(model.P_adj[k, i, t] for k in data.K for i in data.I) + sum(P_sur[k][t] for k in data.K) + model.P_CB_dis[t]) \
            == (sum(P_short[k][t] for k in data.K) + model.P_CB_ch[t] + sum(model.P_sell[k, t] for k in data.K))
    model.power_balance = Constraint(data.T, rule=power_balance_rule)

    # -- CBESS --
    # charging rule
    def charging_rule(model, t):
        if t == 0:
            return model.P_CB_ch[t] <= data.P_CB_cap * (1 - data.SOC_CB_0) / (1 - data.L_CB_ch) / data.ETA_BTB
        return model.P_CB_ch[t] <= data.P_CB_cap * (1 - model.SOC_CB[t-1]) / (1 - data.L_CB_ch) / data.ETA_BTB
    model.charging = Constraint(data.T, rule=charging_rule)

    # discharging rule
    def discharging_rule(model, t):
        if t == 0:
            return model.P_CB_dis[t] <= data.P_CB_cap * data.SOC_CB_0 * (1 - data.L_CB_dis) / data.ETA_BTB
        return model.P_CB_dis[t] <= data.P_CB_cap * model.SOC_CB[t-1] * (1 - data.L_CB_dis) / data.ETA_BTB
    model.discharging = Constraint(data.T, rule=discharging_rule)

    # BTB charging capacity rule
    def btb_charging_capacity_rule(model, t):
        return model.P_CB_ch[t] <= data.P_BTB / data.ETA_BTB
    model.btb_charging_capacity = Constraint(data.T, rule=btb_charging_capacity_rule)

    # BTB discharging capacity rule
    def btb_discharging_capacity_rule(model, t):
        return model.P_CB_dis[t] <= data.P_BTB / data.ETA_BTB
    model.btb_discharging_capacity = Constraint(data.T, rule=btb_discharging_capacity_rule)

    # SOC update rule
    def SOC_update_rule(model, t):
        if t == 0:
            return model.SOC_CB[t] == data.SOC_CB_0 - 1 / data.P_CB_cap * (1 / (1 - data.L_CB_dis) / data.ETA_BTB * model.P_CB_dis[t] - model.P_CB_ch[t] * (1 - data.L_CB_ch) * data.ETA_BTB)
        return model.SOC_CB[t] == model.SOC_CB[t-1] - 1 / data.P_CB_cap * (1 / (1 - data.L_CB_dis) / data.ETA_BTB * model.P_CB_dis[t] - model.P_CB_ch[t] * (1 - data.L_CB_ch) * data.ETA_BTB)
    model.SOC_update = Constraint(data.T, rule=SOC_update_rule)

    # self discharge rule
    def self_dis_rule(model, t):
        return model.SOC_CB[t] == (1 - data.DELTA_CB) * model.SOC_CBp[t]
    model.self_dis = Constraint(data.T, rule=self_dis_rule)

    return model