from data import I, T, K

# Utility
PR_buy = [155 for t in T]
PR_sell = [152.5 for t in T]

# Costs
C_CDGP = [None for t in T]
C_CDG = [[[None for t in T] for i in I] for k in K]
PR_Buy = [None for t in T]
PR_Sell = [None for t in T]

P_CDGP_min = None       
P_CDGP_max = None
P_adj_min = None
P_adj_max = None