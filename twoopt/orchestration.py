"""
API glue.

Linear solver and simulation optimizer have to be "in agreement". I.e they have
to operate upon the same ontology and data.

This module contains entities that fullfill 2 purposes.
1. They glue relevant pairs of linear programming and simulation optimizers together,
2. Complete up the optimization algorithm, ensuring data flow between the
optimizers, and checking for stop conditions.
"""

import sim_opt
import linsmat
import linsolv_planner
