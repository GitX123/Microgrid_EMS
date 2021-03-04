num_mgs = 3 # number of microgrids

# --- Sets ---
I = [i for i in range(3)] # CDG units
T = [t for t in range(24)] # time intervals
K = [k for k in range(num_mgs)] # microgrids

# --- Constants ---

# Costs
C_CDGP = [None for t in T]
C_CDG = [[[None for t in T] for i in I] for k in K]
PR_Buy = [None for t in T]
PR_Sell = [None for t in T]


P_CDGP_min = None
P_CDGP_max = None
P_adj_min = None
P_adj_max = None