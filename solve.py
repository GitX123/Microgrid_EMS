from pyomo.environ import *
import data
from local_sheduling import create_model

model = create_model(data)