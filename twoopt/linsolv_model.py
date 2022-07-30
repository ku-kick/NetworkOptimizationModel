# This module forms an input matrix for scipy linear solver based on the data it is provided with.
# The input data format is defined and described in `data.py`

from pandas import DataFrame
from numpy import array, vstack
from scipy.optimize import linprog
import data
import itertools as itt


class Index:
	"""
	Indexes variables regarding their positions in equality and inequality matrices and bounds.
	"""

	def __init__(self, m, k) -> None:
		"""
		m: number of nodes
		k: number of structual stability spans
		"""
		self.m = m
		self.k = k

		self.n_x_ij = self.m * (self.m - 1)  # Number of channels ij excluding (a, a)

		self.x_base = 0
		self.y_base = self.n_x_ij
		self.z_base = self.y_base + self.m
		self.g_base = self.z_base + self.m

		self.n_variables_l = self.n_x_ij + 3 * m  # Number of vars considering each l separately (those corresponding to an index l)
		self.n_variables_all = self.n_variables_l * k  # Number of vars considering all ls

	def get_offset_var_ijl(self, var, i=None, j=None, l=None):
		"""
		Gets an index of a certain variable. Equivalent to the position of a variable in the equality matrix's row.
		i, j, and l are counted from 0
		"""
		assert var in ['y', 'z', 'g', 'x']
		l = 0 if l is None else l

		# Variables form a sequence: x's ... y's... z's... g's...

		var_offset_row = {
			'x': lambda: self.get_offset_x_ij(i, j),
			'y': lambda: self.y_base + j,
			'z': lambda: self.z_base + j,
			'g': lambda: self.g_base + j,
		}

		offset = var_offset_row[var]()  # Not considering l
		offset = offset + l * self.n_variables_l  # Considering l

		return offset

	def get_offset_x_ij(self, i, j):
		"""
		Regardless of current structural stability span, it calculates a position of x_ij in a row consisting of
		permutations of i and j. For example, say we have 3 nodes. The sequence is, therefore, formed as follows:
		x12 x13 x21 x23 x31 x32. `i` and `j` are counted from 0.

		Returns an offset from position 1 for a given element. For example, for x12, the offset equals 0
		"""
		assert i >= 0 and j >= 0

		return self.x_base + i * (self.m - 1) + j - int(j > i)


class EqMatrixA(Index):
	"""
	Matrix builder for the equality constraint
	$ x_j = F(x_ij, x_ji, y_j, z_j, g_j) $

	Contains a set of useful shortcuts that interpret subject area equality-constraints pertaining to channel
	designation task into a system of equations for scipy linear solver represented in a format Ax = b.

	With considerations to structural stability spans, the matrix is formed in the following way:

	|----------------------------------------------------------|-----------------------------------------|
	|x_111 ... x_ij1 y_11 ... y_j1 z_11 ... z_j1 g_11 ... g_j1 |                                         |  |  j = 1
	|                                                          |               zeros                     |  |  j = 2
	|                    ...over j                             |                                         |  v  ... over j
	|----------------------------------------------------------|-----------------------------------------|
	|           memory remainder y_j1 and zeros                | x_112   ...   x_ij2   y_j2   z_j2   g_j2|  |  j = 1
	|                                                          |                                         |  |  j = 2
	|                                                          |             ... over j                  |  v  ... over j
	|----------------------------------------------------------|-----------------------------------------|
					  n=1                                                          n = 2
					 --------------------------------------------------------->

	Roughly speaking, the matrix is divided into quadrants, each of which corresponds to a structural stability span. A
	certain number of methods in this class refers to offsets, which are used to calculate a position of a requested
	element (a channel, i.e. x_ij, an amount of memoized info y_jl, etc.).
	"""

	def get_offset_quadrant(self, qrow, qcolumn) -> int and int:
		assert qrow >= 0 and qcolumn >= 0

		return self.quadrant_height * qrow, self.quadrant_width * qcolumn

	def __init__(self, m, k):
		"""
		m: number of nodes
		k: number of structual stability spans
		"""

		Index.__init__(self, m, k)
		self.quadrant_width = self.n_variables_l
		self.quadrant_height = self.m

		# self.matrix = [[0] * self.quadrant_width * k] * k * self.quadrant_height
		self.matrix = array([[0] * self.quadrant_width * k] * k * self.quadrant_height)

	def init_ones(self):
		"""
		Initializes positions corresponding to x_ijl, x_jil, y_jl, y_j(l-1), z_j, and g_j with 1
		"""

		val = 1

		for j in range(self.m):
			for l in range(self.k):
				self.set_val(j, self.get_offset_var_ijl('y', j=j), val, (l, l))
				self.set_val(j, self.get_offset_var_ijl('z', j=j), val, (l, l))
				self.set_val(j, self.get_offset_var_ijl('g', j=j), val, (l, l))

				if l > 0:
					self.set_val(j, self.get_offset_var_ijl('y', j=j), -val, (l, l-1))

				for i in range(self.m):
					if i != j:
						self.set_val(j, self.get_offset_var_ijl('x', j=j, i=i), val, (l, l,))
						self.set_val(j, self.get_offset_var_ijl('x', j=i, i=j), val, (l, l,))

	def set_val(self, row, col, val, quadrant:tuple = None):
		assert row >= 0 and col >= 0 and quadrant[0] >= 0 and quadrant[1] >= 0

		if quadrant is not None:
			off_row, off_col = self.get_offset_quadrant(*quadrant)
		else:
			off_row, off_col = 0, 0

		row = row + off_row
		col = col + off_col
		self.matrix[row][col] = val

	def __str__(self):
		header = [''] * self.n_variables_all

		for j in range(self.m):
			for l in range(self.k):
				for var in ['y', 'z', 'g']:
					offset = self.get_offset_var_ijl(var, j=j, l=l)
					header[offset] = f"{var}{j},{l}"

				for i in range(self.m):
					if j != i:
						header[self.get_offset_var_ijl('x', j=j, i=i, l=l)] = f"x{i},{j},{l}"

		m = vstack((header, self.matrix,))

		return str(DataFrame(m))


class EqMatrixB(Index):
	"""
	In equation Ax = b, this class is responsible for its right side. Please refer to EqMatrixA, as these two are
	complementary.
	"""

	def __init__(self, m, k) -> None:
		"""
		m: number of nodes
		k: number of structural stability spans
		"""

		Index.__init__(self, m, k)
		# self.matrix = [0] * m * k
		self.matrix = array([0.0] * m * k)

	def set_x_jl(self, j, l, val):
		"""
		x_jl = val
		"""
		assert l >= 0 and j >= 0

		self.matrix[self.m * l + j] = val


class Builder:

	def __init__(self, data) -> None:
		data = [d for d in data]

		js = set()  # Nodes indices
		ls = set()  # Structural stability spans indices

		for d in data:
			js.add(d["j"])
			ls.add(d["l"])
			alpha_1 = float(d["alpha_1"])
			alpha_2 = float(d["alpha_2"])

		m = len(js)
		k = len(ls)

		self.mat_a = Builder.build_a(m, k, data)
		self.mat_b = Builder.build_b(m, k, data)
		self.bounds = Builder.build_bounds(m, k, data)
		self.mat_max_equation = Builder.build_mat_max_equation(m, k, alpha_1, alpha_2)

	@staticmethod
	def build_mat_max_equation(m, k, alpha_1, alpha_2):
		index = Index(m, k)
		matrix = [0] * index.n_variables_all

		# The original equation is formulated as \sum_over{g} - \sum_over{z} -> max
		# But since scipy lin. solver accepts minimization equations, the inverted form is used
		for j in range(m):
			for l in range(k):
				matrix[index.get_offset_var_ijl('g', j=j, l=l)] = -alpha_1
				matrix[index.get_offset_var_ijl('z', j=j, l=l)] =  alpha_2

		return matrix

	@staticmethod
	def unwrap_row(row):
		"""
		row: row of data
		returns: object with fields j, i, l, phi_jl, psi_jil, v_j, x_jl
		"""
		class Obj(object):
			pass

		def autonum(s: str):
			try:
				return int(s)
			except:
				return float(s)

		ret = Obj()

		for k in row.keys():
			setattr(ret, k, autonum(row[k]))

		return ret

	@staticmethod
	def build_a(m, k, data):
		mat_a = EqMatrixA(m, k)
		mat_a.init_ones()

		return mat_a

	@staticmethod
	def build_b(m, k, data):
		mat_b = EqMatrixB(m, k)

		for d in data:
			d = Builder.unwrap_row(d)
			mat_b.set_x_jl(d.j, d.l, d.x_jl)

		return mat_b

	@staticmethod
	def _set_upper_bound(bounds, pos, val):
		bounds[pos][1] = val

		return bounds

	@staticmethod
	def build_bounds(m, k, data):
		index = Index(m, k)
		bounds = array([[0.0, 0.0]] * index.n_variables_all)

		for d in data:
			d = Builder.unwrap_row(d)
			bounds = Builder._set_upper_bound(bounds, index.get_offset_var_ijl('y', i=d.i, j=d.j, l=d.l), d.v_j)
			bounds = Builder._set_upper_bound(bounds, index.get_offset_var_ijl('g', i=d.i, j=d.j, l=d.l), d.phi_jl)
			bounds = Builder._set_upper_bound(bounds, index.get_offset_var_ijl('x', i=d.j, j=d.i, l=d.l), d.psi_jil)

		return bounds


class Output:

	@staticmethod
	def print_matrix(m):
		print(DataFrame(m))


def wrap_solve_csv(filename):
	builder = Builder(data.Read.readf_iter(filename))

	return linprog(
		c = builder.mat_max_equation,
		A_eq = builder.mat_a.matrix,
		b_eq = builder.mat_b.matrix,
		bounds = builder.bounds
	)


def wrap_solve_pickle_ui(filename):
	kv_data = data.UiKvData()
	kv_data.load(filename)
	generated_filename = filename + '.csv'
	data.Generation.file_generate_kv(generated_filename, kv_data, True)

	return wrap_solve_csv(generated_filename)


def _solution_pack_var(kv_data: data.KvData, solution, var, index: Index, i, j, l):
	offset = index.get_offset_var_ijl(var, i, j, l)
	value = solution[offset]

	if var in ['y', 'z', 'g']:
		kv_data.set(value, var + "_jl", j, l)
	elif var in ['x']:
		kv_data.set(value, var + "_jil", j, i, l)

	return kv_data


def solution_hr_print(solution, m, k):  # Print solution in human-readable form
	index = Index(m, k)
	kv_data = data.KvData()

	for var in ['x', 'y', 'g', 'z']:
		for j in range(index.m):
			for l in range(index.k):
				for i in range(index.m):
					kv_data = _solution_pack_var(kv_data, solution, var, index, i, j, l)

	print(kv_data)


if __name__ == "__main__":
	pass
