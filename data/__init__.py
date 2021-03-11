import numpy as np

def add_noise(data: list):
    data = np.asarray(data)
    data += np.random.normal(0, 2, len(data))
    data = data.tolist()

num_mgs = 3 # number of microgrids

# --- Sets ---
I = [i for i in range(3)] # CDG units
T = [t for t in range(24)] # time intervals
K = [k for k in range(num_mgs)] # microgrids