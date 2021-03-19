from data import I, T, K
import data.mg1, data.mg2, data.mg3

# Utility
PR_buy = [155 for t in T]
PR_sell = [152.5 for t in T]

# Costs
C_CDGP = [152.0 for t in T]
C_CDG = [data.mg1.C_CDG, data.mg2.C_CDG, data.mg3.C_CDG]

P_CDGP_min = 0.0       
P_CDGP_max = 1800.0

# CBESS
P_CB_cap = 3500.0
P_BTB = 600.0
SOC_CB_0 = 0.285
L_CB_ch = 0.03
L_CB_dis = 0.03
ETA_BTB = 0.98
DELTA_CB = 0.03