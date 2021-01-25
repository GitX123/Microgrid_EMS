from pyomo.environ import *
from local_scheduling import model

solver = SolverFactory('glpk')
solver.solve(model)

model.y.pprint()