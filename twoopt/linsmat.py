"""
The following prepares data strcutured to be passed into `scipy.optimize.linprog` routine
"""

from dataclasses import dataclass
import functools
import ut
import json


@dataclass
class RowIndex:
	"""
	In linear equation's matrices, variables are stored according to some configuration. For example, for a problem w/
	variables "x", "y", "z", a row could have the following structure:

	Xa0b0 Xa0b1 Xa1b0 Xa1b1 Ya0c0 ...

	This class is responsible for transforming human-readable indices into positions in the vector. Speaking in terms of
	positional numeral systems, the position can be represented as a tuple of mixed-radix numbers:

	(Xab, Yac)

	Essentially, this class transforms a mixed-radix number into decimal, while having subject area-specific API.
	"""
	indices: dict  # Format {"index1": RANGE, "index2": RANGE, ...}.
	variables: dict  # Format {"variable1": [indices], "variable 2": indices, ...}
	from_zero = True

	def _check_precedence(self, var_a, var_b):
		"""
		Returns True, when var_a appears before var_b
		"""
		return list(self.variables.keys()).index(var_a) < list(self.variables.keys()).index(var_b)

	def _to_mixed_radix_number(self, var, **indices):

		return list(map(lambda index: indices[index], self.variables[var]))

	def _get_radix_map_length(self, variable):
		return len(self.radix_maps[variable])

	def get_pos(self, variable, **indices):
		"""
		Transform a mixed radix number representing the variable's position to decimal one
		"""
		if not self.from_zero:
			indices = dict(map(lambda kv: (kv[0], kv[1] - 1), indices.items()))

		assert variable in self.variables.keys()  # Check if variable exists
		assert set(indices.keys()) == set(self.variables[variable])  # Check that all indices are present
		assert all([0 <= indices[i] <= self.indices[i] for i in indices.keys()])

		radix_number = self._to_mixed_radix_number(variable, **indices)
		mult = lambda a, b: a * b

		map_var = lambda var: sum(map(lambda i: radix_number[i] * self.radix_mult_vectors[var][i],
			range(len(self.radix_maps[var])))) if var == variable else 0 if self._check_precedence(var, variable) else \
			functools.reduce(mult, self.radix_maps[var], 1)

		return sum(map(map_var, self.variables.keys()))

	def __post_init__(self):
		"""
		Forms radix map and radix scalar multiplication vector for numerical transofmations into a non-mixed radix
		number

		Example:
		indices: {j: 2, rho: 3}
		variables {x: [j, rho], y: [j]}
		radix_map: [2, 3, 2] (or [x_j_rho, x_rho, y_j])
		radix_mult_vector: [3*2*1, 2*1, 1]

		With this radix map, a mixed radix number [1, 2, 1] could be converted into a non-mixed through multiplication:

		[1, 2, 1] * radix_mult_vector
		"""
		self.radix_maps = dict(zip(self.variables.keys(), map(lambda variable: list(map(
			lambda index: self.indices[index], self.variables[variable])), self.variables.keys())))
		self.radix_mult_vectors = dict()

		for v in self.variables.keys():
			npos = len(self.radix_maps[v])
			self.radix_mult_vectors[v] = [1 for _ in range(npos)]

			if npos > 1:
				for i in reversed(range(npos - 1)):
					self.radix_mult_vectors[v][i] = self.radix_maps[v][i + 1] * self.radix_mult_vectors[v][i + 1]


@dataclass
class Schema:
	"""
	Wrapper over a dictionary containing schema information: indices, variables, boundaries
	Format example:
	{
		"indexbound": {
			"j": 3,
			"i": 2,
			"m": 4
		},
		"variableindices": {
			"x": ["j", "i"],
			"y": ["i", "j", "m"],
			"z": ["i", "m"]
		}
	}

	Bounds are counted from 0 to N: [0; N)
	"""
	data = None

	def read(self, filename="schema.json"):
		with open(filename, 'r') as f:
			try:
				self.data = json.loads(f.read())
			except FileNotFoundError as e:
				self.data = {
					"indexbound": dict(),
					"variableindices": dict(),
				}

	def write(self, filename="schema.json"):
		assert self.data is not None
		with open(filename, 'w') as f:
			f.write(self.data)

	def set_index_bound(self, index, bound):
		assert self.data is not None
		self.data["indexbound"][index] = bound

	def set_var_indices(self, var, *indices):
		assert self.data is not None
		assert len(indices) > 0
		self.data["variableindices"][var] = list(indices)

	def get_var_radix(self, var):
		assert var in self.data["variableindices"]

		return list(map(lambda i: self.data["indexbound"][i], self.data["variableindices"][var]))
