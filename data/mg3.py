import numpy as np
from data import add_noise
from data.mg1 import *

# CDG
C_CDG = [add_noise(C_CDG[0], 0, 4), add_noise(C_CDG[1], 0, 4), add_noise(C_CDG[2], 0, 4)]
P_max = [550.0, 550.0, 550.0]

# Renewable
P_pv = add_noise(P_pv, 0, 7)

# Battery

# Load
P_L_fix = add_noise(P_L_fix, 0, 14)