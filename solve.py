from pyomo.environ import *
import matplotlib.pyplot as plt
import local_scheduling, global_scheduling
import data, data.mg1, data.mg2, data.mg3, data.dso 

solver = SolverFactory('glpk')
mg_data = [data.mg1, data.mg2, data.mg3]

def mg_info(models):
    P_sur, P_short = [[] for _ in range(len(models))], [[] for _ in range(len(models))]
    P_adj_min, P_adj_max = [[[] for i in data.I] for _ in range(len(models))], [[[] for i in data.I] for _ in range(len(models))]

    for t in data.T:
        for model_i, model in enumerate(models):
            generation_load_difference = sum(value(model.P_CDG[i, t]) for i in data.I) + mg_data[model_i].P_pv[t] + mg_data[model_i].P_wt[t] - value(model.P_L_adj[t])

            # surplus and shortage power
            if generation_load_difference > 0:
                P_sur[model_i].append(generation_load_difference)
                P_short[model_i].append(0.0)
            else:
                P_sur[model_i].append(0.0)
                P_short[model_i].append(-generation_load_difference)

            # adjust power range
            for i in data.I:
                if (mg_data[model_i].C_CDG[i][t] >= mg_data[model_i].PR_sell[t]) and (mg_data[model_i].C_CDG[i][t] <= mg_data[model_i].PR_buy[t]):
                    min_ = mg_data[model_i].P_min[i] - value(model.P_CDG[i, t])
                    max_ = mg_data[model_i].P_max[i] - value(model.P_CDG[i, t])
                    P_adj_min[model_i][i].append(min_)
                    P_adj_max[model_i][i].append(max_)
                else:
                    P_adj_min[model_i][i].append(0.0)
                    P_adj_max[model_i][i].append(0.0)

    return P_sur, P_short, P_adj_min, P_adj_max

# --- Scheduling ---
def run_without_rescheduling():
    # -- Local scheduling --
    model_mg1 = local_scheduling.create_model(data=data.mg1)
    solver.solve(model_mg1)
    model_mg2 = local_scheduling.create_model(data=data.mg2)
    solver.solve(model_mg2)
    model_mg3 = local_scheduling.create_model(data=data.mg3)
    solver.solve(model_mg3)
    models = [model_mg1, model_mg2, model_mg3]

    load = [[value(models[k].P_L_adj[t]) for t in data.T] for k in data.K] 
    dg = [[sum(value(models[k].P_CDG[i, t]) for i in data.I) for t in data.T] for k in data.K]
    battery = [[value(models[k].P_B_dis[t]) - value(models[k].P_B_ch[t]) for t in data.T] for k in data.K]
    utility_transaction = [[value(models[k].P_short[t]) - value(models[k].P_sur[t]) for t in data.T] for k in data.K]

    return load, dg, battery, utility_transaction

def run_with_rescheduling():
    load_rs, dg_rs, battery_rs = [[] for k in data.K], [[] for k in data.K], [[] for k in data.K]
    P_buy_rs, P_sell_rs = [[] for k in data.K], [[] for k in data.K]
    P_rec_rs, P_send_rs = [[] for k in data.K], [[] for k in data.K]
    utility_transaction_rs, mg_transaction_rs = [[] for k in data.K], [[] for k in data.K]

    for t_global in data.T:
        # -- Local scheduling --
        model_mg1 = local_scheduling.create_model(data=data.mg1)
        solver.solve(model_mg1)
        model_mg2 = local_scheduling.create_model(data=data.mg2)
        solver.solve(model_mg2)
        model_mg3 = local_scheduling.create_model(data=data.mg3)
        solver.solve(model_mg3)
        models = [model_mg1, model_mg2, model_mg3]

        # P_CDG
        P_CDG = [[[] for i in data.I] for k in data.K]
        for k in data.K:
            for i in data.I:
                for t in data.T:
                    P_CDG[k][i].append(value(models[k].P_CDG[i, t]))
            dg_rs[k].append(sum(P_CDG[k][i][t_global] for i in data.I))
        
        # P_B_ch, P_B_dis, P_L_adj
        P_B_ch, P_B_dis, P_L_adj = [[] for k in data.K], [[] for k in data.K], [[] for k in data.K]
        for k in data.K:
            for t in data.T:
                P_B_ch[k].append(value(models[k].P_B_ch[t]))
                P_B_dis[k].append(value(models[k].P_B_dis[t]))
                P_L_adj[k].append(value(models[k].P_L_adj[t]))
            battery_rs[k].append(P_B_dis[k][t_global] - P_B_ch[k][t_global])
            load_rs[k].append(P_L_adj[k][t_global])

        # -- MG info for DSO --
        P_sur, P_short, P_adj_min, P_adj_max = mg_info(models)
        print('[Surplus]')
        print(P_sur, '\n')
        print('[Shortage]')
        print(P_short, '\n')
        print('[Adjust]')
        print(P_adj_min, '\n', P_adj_max, '\n')

        # -- Global scheduling --
        model_global = global_scheduling.create_model(data=data.dso, P_sur=P_sur, P_short=P_short, P_adj_min=P_adj_min, P_adj_max=P_adj_max)
        solver.solve(model_global)

        # P_adj
        P_adj = [[[] for i in data.I] for k in data.K]
        for k in data.K:
            for i in data.I:
                for t in data.T:
                    P_adj[k][i].append(value(model_global.P_adj[k, i, t]))

        # P_buy, P_sell
        P_buy, P_sell = [[] for k in data.K], [[] for k in data.K]
        for k in data.K:
            for t in data.T:
                P_buy[k].append(value(model_global.P_buy[k, t]))
                P_sell[k].append(value(model_global.P_sell[k, t]))
            P_buy_rs[k].append(P_buy[k][t_global])
            P_sell_rs[k].append(P_sell[k][t_global])

        # -- Local rescheduling --
        model_mg1_rs = local_scheduling.create_model(data=data.mg1, rescheduling=True, P_CDG=P_CDG[0], P_adj=P_adj[0], P_B_ch=P_B_ch[0], P_B_dis=P_B_dis[0], P_L_adj=P_L_adj[0], P_buy=P_buy[0], P_sell=P_sell[0])
        solver.solve(model_mg1_rs)
        model_mg2_rs = local_scheduling.create_model(data=data.mg2, rescheduling=True, P_CDG=P_CDG[1], P_adj=P_adj[1], P_B_ch=P_B_ch[1], P_B_dis=P_B_dis[1], P_L_adj=P_L_adj[1], P_buy=P_buy[1], P_sell=P_sell[1])
        solver.solve(model_mg2_rs)
        model_mg3_rs = local_scheduling.create_model(data=data.mg3, rescheduling=True, P_CDG=P_CDG[2], P_adj=P_adj[2], P_B_ch=P_B_ch[2], P_B_dis=P_B_dis[2], P_L_adj=P_L_adj[2], P_buy=P_buy[2], P_sell=P_sell[2])
        solver.solve(model_mg3_rs)
        models_rs = [model_mg1_rs, model_mg2_rs, model_mg3_rs]

        # P_rec, P_send
        for k in data.K:
            P_rec_rs[k].append(value(models_rs[k].P_rec[t_global]))
            P_send_rs[k].append(value(models_rs[k].P_send[t_global]))

    # -- Utility transaction and MG transaction
    for k in data.K:
        for t in data.T:
            utility_transaction_rs[k].append(P_buy_rs[k][t] - P_sell_rs[k][t])
            mg_transaction_rs[k].append(P_rec_rs[k][t] - P_send_rs[k][t])

    return load_rs, dg_rs, battery_rs, utility_transaction_rs, mg_transaction_rs

if __name__ == '__main__':
    load, dg, battery, utility_transaction = run_without_rescheduling()
    load_rs, dg_rs, battery_rs, utility_transaction_rs, mg_transaction_rs = run_with_rescheduling()

    # --- Plot ---
    fig, axs = plt.subplots(2, 3)
    # -- No rescheduling --
    axs[0, 0].step(data.T, load[0], label='Load')
    axs[0, 0].step(data.T, data.mg1.P_pv, label='PV')
    axs[0, 0].step(data.T, dg[0], label='DG')
    axs[0, 0].step(data.T, battery[0], label='Battery')
    axs[0, 0].step(data.T, utility_transaction[0], label='Utility')
    axs[0, 0].set_title('MG1')
    axs[0, 0].set_xlabel('Time (hr)')
    axs[0, 0].set_ylabel('Power (kWh)')
    axs[0, 0].legend()

    axs[0, 1].step(data.T, load[1], label='Load')
    axs[0, 1].step(data.T, data.mg2.P_pv, label='PV')
    axs[0, 1].step(data.T, dg[1], label='DG')
    axs[0, 1].step(data.T, battery[1], label='Battery')
    axs[0, 1].step(data.T, utility_transaction[1], label='Utility')
    axs[0, 1].set_title('MG2')
    axs[0, 1].set_xlabel('Time (hr)')
    axs[0, 1].set_ylabel('Power (kWh)')
    axs[0, 1].legend()

    axs[0, 2].step(data.T, load[2], label='Load')
    axs[0, 2].step(data.T, data.mg3.P_pv, label='PV')
    axs[0, 2].step(data.T, dg[2], label='DG')
    axs[0, 2].step(data.T, battery[2], label='Battery')
    axs[0, 2].step(data.T, utility_transaction[2], label='Utility')
    axs[0, 2].set_title('MG3')
    axs[0, 2].set_xlabel('Time (hr)')
    axs[0, 2].set_ylabel('Power (kWh)')
    axs[0, 2].legend()

    # -- Rescheduling --
    axs[1, 0].step(data.T, load_rs[0], label='Load')
    axs[1, 0].step(data.T, data.mg1.P_pv, label='PV')
    axs[1, 0].step(data.T, dg_rs[0], label='DG')
    axs[1, 0].step(data.T, battery_rs[0], label='Battery')
    axs[1, 0].step(data.T, utility_transaction_rs[0], label='Utility')
    axs[1, 0].step(data.T, mg_transaction_rs[0], label='MG')
    axs[1, 0].set_xlabel('Time (hr)')
    axs[1, 0].set_ylabel('Power (kWh)')
    axs[1, 0].legend()

    axs[1, 1].step(data.T, load_rs[1], label='Load')
    axs[1, 1].step(data.T, data.mg2.P_pv, label='PV')
    axs[1, 1].step(data.T, dg_rs[1], label='DG')
    axs[1, 1].step(data.T, battery_rs[1], label='Battery')
    axs[1, 1].step(data.T, utility_transaction_rs[1], label='Utility')
    axs[1, 1].step(data.T, mg_transaction_rs[1], label='MG')
    axs[1, 1].set_xlabel('Time (hr)')
    axs[1, 1].set_ylabel('Power (kWh)')
    axs[1, 1].legend()

    axs[1, 2].step(data.T, load_rs[2], label='Load')
    axs[1, 2].step(data.T, data.mg3.P_pv, label='PV')
    axs[1, 2].step(data.T, dg_rs[2], label='DG')
    axs[1, 2].step(data.T, battery_rs[2], label='Battery')
    axs[1, 2].step(data.T, utility_transaction_rs[2], label='Utility')
    axs[1, 2].step(data.T, mg_transaction_rs[2], label='MG')
    axs[1, 2].set_xlabel('Time (hr)')
    axs[1, 2].set_ylabel('Power (kWh)')
    axs[1, 2].legend()

    plt.show()