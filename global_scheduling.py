from pyomo.environ import *

def create_model(data):
    # --- Model --- 
    model = ConcreteModel(name='(G_S)')

    # --- Variable ---
    model.P_CDGP = Var(data.T)
    model.P_adj = Var(data.K, data.I, data.T)

    # transaction
    model.P_buy = Var(data.K, data.T)
    model.P_sell = Var(data.K, data.T)

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
                transaction_cost += data.PR_Buy[t] * model.P_buy[k, t] - data.PR_Sell[t] * model.P_sell[k, t]

        obj = cdgp_cost + power_adjust_cost + transaction_cost
        return obj
    model.obj = Objective(rule=obj_rule, sense=minimize)

    # --- Constraints ---
    # CDGP
    def cdgp_power_limit_rule(model, t):
        return data.P_CDGP_min <= model.P_CDGP[t] <= data.P_CDGP_max
    model.cdgp_power_limit = Constraint(data.T, rule=cdgp_power_limit_rule)

    # [TODO]
    # power adjustment
    # power balance

    # -- CBESS --
    # charging rule
    # discharging rule
    # SOC update rule
    # SOC range rule
    # self discharge rule
