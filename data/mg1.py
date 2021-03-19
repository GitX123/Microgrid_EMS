import numpy as np
import pandas as pd
from data import I, T, K, PR_buy, PR_sell, PR_rec, PR_send

# CDG
C_CDG = [[140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5], 
        [140, 135, 137.5, 135, 132.5, 140, 147.5, 152.5, 155, 160, 165, 170, 172.5, 170, 167.5, 165, 165, 162.5, 160, 157.5, 155, 142.5, 140, 137.5]]
C_SU = [200.0, 200.0,  200.0]
P_min = [0.0, 0.0, 0.0]
P_max = [500.0, 500.0, 500.0]

# Renewable
pv_ref = 500.0
pv_data = pd.read_csv('./data/miris_pv.csv').to_numpy()
pv_data = pv_data[:17280, 1] # extract 1 day data
pv_data = np.mean(pv_data.reshape(-1, 720), axis=1) # average to have 1-hour resolution
pv_data = pv_ref * pv_data / np.amax(pv_data) # normalize
P_pv = pv_data.tolist()

P_wt = [0 for t in T]

# Battery
L_B_ch = 0.03
L_B_dis = 0.03
P_B_cap = 200.0 
P_BTB = 200.0
ETA_BTB = 0.98
DELTA_B = 0.03

# Load
load_fix_ref = 2000.0
load_fix_data = pd.read_csv('./data/miris_load.csv').to_numpy()
load_fix_data = load_fix_data[:17280, 1]
load_fix_data = np.mean(load_fix_data.reshape(-1, 720), axis=1) # average
load_fix_data = load_fix_ref * load_fix_data / np.amax(load_fix_data) # normalize
P_L_fix = load_fix_data.tolist()

vt_t = [[0.0 for tp in T] for t in T] # penalty of load shifting
IF_max = [200.0 for t in T]
OF_max = [200.0 for t in T]