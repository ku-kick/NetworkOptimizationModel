"""
Generates schedule for an information process based on technical limitations of a network. As the work progresses, this
module will extend with other versions of linear programming solvers.
"""

import linsmat
from dataclasses import dataclass
import numpy as np
import ut
from generic import Log
import scipy


@dataclass
class LinsolvPlanner:
	"""
	Domain-aware linear equation solver.

	It is difficult to gain a comprehensive understanding of this code w/o the context. If you speak russian,
	please refer to the 2022 paper "Polymodel optimization of network configuration and informational operations
	schedule, problem statement and solving approaches"
	"""
	data_interface: object
	schema: linsmat.Schema

	# Mapping b/w a network config. characteristic, and the name of the variable representing its upper bound (lower
	# bounds are always 0)
	_NEQ_VAR_ORDER = ['x', 'y', 'g', 'z']
	_NEQ_VAR_ORDER_RHS = ["psi", "v", "phi"]

	def __post_init__(self):
		self.row_index = linsmat.RowIndex.make_from_schema(self.schema, ["x", "y", "z", "g"])
		self.validate()
		self.eq_lhs = self.__init_eq_lhs_matrix()
		self.eq_rhs = self.__init_eq_rhs_matrix()
		self.bnd = self.__init_bnd_matrix()
		self.obj = self.__init_obj()

	def validate(self):
		"""
		Ensures input data correctness
		"""
		assert self.schema.get_index_bound("i") == self.schema.get_index_bound("j")
		assert list(self.schema.get_var_indices("x")) == ["j", "i", "rho", "l"]

		for var in ["x_eq", "y", "g", "z"]:
			Log.debug(LinsolvPlanner, LinsolvPlanner.validate, "var", var, self.schema.get_var_indices(var))
			assert list(self.schema.get_var_indices(var)) == ["j", "rho", "l"]

	def __make_eq_lhs_vector(self, j, rho, l):
		"""
		Left side equality constraint, one row.
		"""
		log_context = (LinsolvPlanner.__make_eq_lhs_vector,)
		Log.debug(*log_context, "j", "rho", "l", j, rho, l)
		stub = np.zeros(self.row_index.get_row_len())
		y_pos = self.row_index.get_pos('y', j=j, l=l, rho=rho)
		stub[y_pos] = 1
		z_pos = self.row_index.get_pos('z', j=j, l=l, rho=rho)
		stub[z_pos] = -1
		g_pos = self.row_index.get_pos('g', j=j, l=l, rho=rho)
		stub[g_pos] = 1

		if l != 0:
			stub[self.row_index.get_pos('y', j=j, l=l-1, rho=rho)] = -1

		for i in range(self.schema.get_index_bound("i")):
			if i != j:
				x_pos = self.row_index.get_pos('x', i=i, j=j, rho=rho, l=l)
				stub[self.row_index.get_pos('x', i=i, j=j, rho=rho, l=l)] = -1
				x_pos = self.row_index.get_pos('x', i=j, j=i, rho=rho, l=l)
				stub[x_pos] = 1

		return stub

	def __init_eq_lhs_matrix(self):
		"""
		Left side equality constraint, entire matrix.
		"""
		make_vector = lambda j, rho, l: self.__make_eq_lhs_vector(j=j, l=l, rho=rho)
		map_vectors = map(lambda i: make_vector(*i), self.__x_eq_constraint_indices_iter())
		arr = np.array(list(map_vectors))

		return arr

	def __x_eq_constraint_indices_iter(self):
		radix_map = self.schema.get_var_radix("x_eq")

		for indices in ut.radix_cartesian_product(radix_map):
			try:
				self.data_interface.get_plain("x_eq", *indices)

				yield indices
			except AssertionError:
				continue

	def __init_eq_rhs_matrix(self):
		"""
		Right side equality constraint, entire matrix
		"""
		radix_map = self.schema.get_var_radix("x_eq")
		map_get_x_eq_from_data = map(lambda indices: self.data_interface.get_plain("x_eq", *indices),
			self.__x_eq_constraint_indices_iter())
		Log.debug(self.schema.get_var_indices("x_eq"), list(self.__x_eq_constraint_indices_iter()))
		arr = np.array(list(map_get_x_eq_from_data))

		return arr

	def __init_bnd_matrix(self):
		bnd = [[0, float("inf")] for _ in range(self.row_index.get_row_len())]

		for var, bnd_var in zip(LinsolvPlanner._NEQ_VAR_ORDER, LinsolvPlanner._NEQ_VAR_ORDER_RHS):
			# "z" upper limit is always "inf". It is not expected in input data
			if var != "z":
				assert list(self.schema.get_var_indices(var)) == list(self.schema.get_var_indices(bnd_var))

			for indices in ut.radix_cartesian_product(self.schema.get_var_radix(var)):
				_, indices_dict = self.schema.indices_plain_to_dict(var, *indices)  # ETL
				pos = self.row_index.get_pos(var, **indices_dict)
				upper_bound = self.data_interface.get_plain(bnd_var, *indices)
				bnd[pos][1] = upper_bound
				Log.debug(LinsolvPlanner, LinsolvPlanner.__init_bnd_matrix, "variable", var, "indices",
					self.schema.get_var_indices(var), *indices, "bounds", bnd[pos], "pos", pos)

		return bnd

	def __init_obj(self):
		alpha_g = -self.data_interface.get_plain("alpha_0")  # alpha_1 in the paper, inverted, because numpy can only solve minimization problems
		alpha_z = self.data_interface.get_plain("alpha_1")  # alpha_2 in the paper, inverted, because numpy can only solve minimization problems
		stub = np.ones(self.row_index.get_row_len())

		for j, rho, l in ut.radix_cartesian_product(self.schema.make_radix_map("j", "rho", "l")):
			pos_g = self.row_index.get_pos("g", j=j, rho=rho, l=l)
			pos_z = self.row_index.get_pos("z", j=j, rho=rho, l=l)
			stub[pos_g] = alpha_g
			stub[pos_z] = alpha_z

		return stub

	def solve(self):
		return scipy.optimize.linprog(c=self.obj, bounds=self.bnd, A_eq=self.eq_lhs, b_eq=self.eq_rhs)


class InfluxConstraintLp(LinsolvPlanner):
	"""
	Differs from `LinsolvPlanner` in that it explicitly states the fact that information influx precedes any other
	operation

	Equation:

	\sum_{o=0}^{l}{g_{j \rho o}}
		+ y_{j \rho l} - y_{j rho 0}
		+ \sum_{o=0}^{l}{z_{j \rho o}}
		- \sum_{o=0}^{l}{\sum_{i}{x_{i j \rho o}}}
		<= 0
	"""
	def __post_init__(self):
		LinsolvPlanner.__post_init__(self)
		self.le_lhs, self.le_rhs = self.__init_ge()

	def __init_ge_iter(self):
		for j, rho, l_bound in range(self.schema.get_radix_map('g')):  # j, rho, l
			arr = [0 for _ in range(self.row_index.get_row_len())]
			arr = linsmat.arr_set(arr, self.row_index, 1, 'y', j=j, rho=rho, l=l_bound)
			arr = linsmat.arr_set(arr, self.row_index, -1, 'y', j=j, rho=rho, l=0)

			for l in range(l_bound):
				arr = linsmat.arr_set(arr, self.row_index, 1, 'g', j=j, rho=rho, l=l)
				arr = linsmat.arr_set(arr, self.row_index, 1, 'z', j=j, rho=rho, l=l)

				for i in range(self.row_index.get_index_bound('j')):
					arr = linsmat.arr_set(arr, self.row_index, -1, 'x', j=i, i=j, rho=rho, l=l)

			yield (arr, 0)

	def __init_ge(self):
		lhs = []
		rhs = []

		for l, r in self.__init_ge_iter():
			lhs.append(l)
			rhs.append(r)

	def solve(self):
		return scipy.optimize.linprog(c=self.obj, bounds=self.bnd, A_eq=self.eq_lhs,
			b_eq=self.eq_rhs, A_ub=self.le_lhs, b_ub=self.le_rhs)
