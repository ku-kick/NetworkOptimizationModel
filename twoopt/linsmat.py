"""
The following prepares data strcutured to be passed into `scipy.optimize.linprog` routine
"""

from dataclasses import dataclass
import functools


@dataclass
class RowIndex:
	"""
	In linear equation's matrices, variables are stored according to some configuration. For example, for a problem w/
	variables "x", "y", "z", a row could have the following structure:

	Xa0b0 Xa0b1 Xa1b0 Xa1b1 Ya0c0 ...

	This class is responsible for transforming human-readable indices into positions in the vector. Speaking in terms of
	positional numeral systems, the position can be represented as a tuple of mixed-radix numbers:

	Xab Xb Yac Yc

	Essentially, this class transforms a mixed-radix number into decimal, while having subject area-specific API.
	"""
	indices: dict  # Format {"index1": RANGE, "index2": RANGE, ...}.
	variables: dict  # Format {"variable1": [indices], "variable 2": indices, ...}
	from_zero = True

	def __post_init__(self):
		"""
		Example:
		indices: {j: 2, rho: 3}
		variables {x: [j, rho], y: [j]}
		radix_map: [2, 3, 2] (or [x_j_rho, x_rho, y_j])
		"""
		self.radix_map = functools.reduce(lambda a, b: a + b,
			map(lambda variable: list(map(lambda index: self.indices[index], self.variables[variable])),
			self.variables.keys()), [])
