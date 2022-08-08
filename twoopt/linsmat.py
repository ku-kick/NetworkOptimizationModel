"""
The following prepares data strcutured to be passed into `scipy.optimize.linprog` routine
"""

from dataclasses import dataclass
import functools
import ut
import json
import re
import io
import os
import csv
from generic import Log


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
	data: str = None
	filename: str = None

	def __post_init__(self):
		if self.filename is not None:
			self.read(self.filename)

	def read(self, filename="schema.json"):
		with open(filename, 'r') as f:
			try:
				self.data = json.loads(f.read())
			except FileNotFoundError as e:
				Log.error(Schema, "got exception", e)
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

	def indices_dict_to_plain(self, variable, **indices):
		"""
		[VARAIBLE, {"index1": INDEX1, "index2": INDEX2}] -> [VARIABLE, INDEX1, INDEX2]
		"""
		assert type(variable) is str
		assert set(self.data["variableindices"][variable]) == set(indices.keys())
		indices_plain = tuple(map(lambda i: indices[i], self.data["variableindices"][variable]))

		return (variable,) + indices_plain

	def indices_plain_to_dict(self, variable, *indices):
		"""
		[VARIABLE, INDEX1, INDEX2] -> [VARAIBLE, {"index1": INDEX1, "index2": INDEX2}]
		"""
		assert type(variable) is str
		check_type_int = lambda i: type(i) is int
		assert all(map(check_type_int, indices))
		assert len(indices) == len(self.data["variableindices"][variable])
		indices_dict = dict(zip(self.data["variableindices"][variable], indices))

		return (variable, indices_dict)


@dataclass
class PermissiveCsvBufferedDataProvider(dict):
	"""
	Represents data in the following format
	{
		(VARAIBLE1, INDEX1, INDEX2) : VALUE,
		(VARIABLE2, INDEX1) : VALUE,
	}

	Guarantees and ensures that VARIABLE has type `str`, indices have type `int`, and VALUE has type `float`
	"""
	csv_file_name: str

	def get_plain(self, *key):
		assert key in self.keys()
		return self[key]

	def set_plain(self, *args):
		"""
		Adds a sequence of format (VAR, INDEX1, INDEX2, ..., VALUE) into the dictionary
		"""
		assert len(args) >= 2
		assert type(args[0]) is str
		assert type(args[-1]) is float
		assert all(map(lambda i: type(i) is int, args[1:-1]))

		self[tuple(args[:-1])] = args[-1]

	def _into_iter_plain(self):
		stitch = lambda k, v: k + (v,)

		return map(stitch, self.items())

	def __post_init__(self):
		"""
		Parses data from a CSV file containing sequences of the following format:
		VARIABLE   SPACE_OR_TAB   INDEX1   SPACE_OR_TAB   INDEX2   ...   SPACE_OR_TAB   VALUE

		Expects the values to be stored according to Repr. w/ use of " " space symbol as the separator
		"""
		assert os.path.exists(self.csv_file_name)

		with open(self.csv_file_name, 'r') as f:
			data = ''.join(map(lambda l: re.sub(r'( |\t)+', ' ', l), f.readlines()))  # Sanitize, replace spaces or tabs w/ single spaces
			reader = csv.reader(io.StringIO(data), delimiter=' ')
			map_cast = map(lambda l: [l[0]] + list(map(int, l[1:-1])) + [float(l[-1])], reader)

			for plain in map_cast:
				Log.debug(PermissiveCsvBufferedDataProvider, plain)
				self.set_plain(*plain)

			Log.debug(PermissiveCsvBufferedDataProvider, self.items())

	def sync(self):
		with open(self.filename, 'w') as f:
			f.writelines(list(self._into_iter_plain))


@dataclass
class DataInterface:
	provider: object  # Abstraction over storage medium
	schema: Schema

	def get(self, variable, **indices) -> float:
		plain = self.schema.indices_dict_to_plain(variable, **indices)

		return self.provider.get_plain(*plain)

	def set(self, variable, **indices) -> float:
		plain = self.schema.indices_dict_to_plain(variable, **indices)
		self.provider.set_plain(*plain)
