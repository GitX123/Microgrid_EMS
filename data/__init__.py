import numpy as np

num_mgs = 3 # number of microgrids

# --- Sets ---
I = [i for i in range(3)] # CDG units
T = [t for t in range(24)] # time intervals
K = [k for k in range(num_mgs)] # microgrids

def add_noise(data: list, mean, std):
    data = np.asarray(data, 'float64')
    data += np.random.normal(mean, std, len(data))
    data = data.tolist()
    return data