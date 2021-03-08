import numpy as np
import pandas as pd

num_mgs = 3 # number of microgrids

# --- Sets ---
I = [i for i in range(3)] # CDG units
T = [t for t in range(24)] # time intervals
K = [k for k in range(num_mgs)] # microgrids

# --- Constants ---
# -- Community --
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

# -- MG --
# CDG
C_CDG = [[140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5]]
C_SU = [2, 2,  2]
P_min = [0, 0, 0]
P_max = [500, 500, 500]

# Renewable
pv_ref = 500
pv_data = pd.read_csv('miris_pv.csv').to_numpy()
pv_data = pv_data[:17280, 1] # extract 1 day data
pv_data = np.mean(pv_data.reshape(-1, 720), axis=1) # average to have 1-hour resolution
pv_data = pv_ref * pv_data / np.amax(pv_data) # normalize
P_pv = pv_data.tolist()

P_wt = [0 for t in T]

# Battery
L_B_ch = 0.03
L_B_dis = 0.03
P_B_cap = 200 
P_BTB = 200
ETA_BTB = 0.98
DELTA_B = 0.03

# Load
load_fix_ref = 2000
load_fix_data = pd.read_csv('miris_load.csv').to_numpy()
load_fix_data = load_fix_data[:17280, 1]
load_fix_data = np.mean(load_fix_data.reshape(-1, 720), axis=1) # average
load_fix_data = load_fix_ref * load_fix_data / np.amax(load_fix_data) # normalize
P_L_fix = load_fix_data.tolist()

vt_t = [[0 for tp in T] for t in T] # penalty of load shifting
IF_max = [0, 0, 0, 0, 0, 0, 0, 0, 90, 35, 0, 105, 41, 36, 51, 59, 45, 13, 0, 8, 0, 0, 0, 0]
OF_max = [0, 0, 0, 0, 0, 0, 0, 0, 410, 465, 500, 395, 459, 464, 449, 441, 455, 487, 500, 492, 0, 0, 0, 0]