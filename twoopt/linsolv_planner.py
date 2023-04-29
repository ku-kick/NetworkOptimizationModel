"""
Generates schedule for an information process based on technical limitations of a network. As the work progresses, this
module will extend with other versions of linear programming solvers.
"""

import math
import twoopt.linsmat as linsmat
from dataclasses import dataclass
import numpy as np
import twoopt.ut as ut
from twoopt.generic import Log
import scipy
from twoopt.optimization.data_amount_planning import LinsolvPlanner

log = ut.Log(file=__file__, level=ut.Log.LEVEL_INFO)
