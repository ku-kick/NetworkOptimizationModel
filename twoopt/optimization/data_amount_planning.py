import dataclasses
import math
import numpy as np
import twoopt.data_processing
import scipy


class StubLog:

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


log = StubLog()


@dataclasses.dataclass
class LinsolvPlanner:
	"""
	Domain-aware linear equation solver.

	It is difficult to gain a comprehensive understanding of this code w/o the context. If you speak russian,
	please refer to the 2022 paper "Polymodel optimization of network configuration and informational operations
	schedule, problem statement and solving approaches"
	"""
	data_interface: object
	schema: twoopt.data_processing.vector_index.Schema

	# Mapping b/w a network config. characteristic, and the name of the variable representing its upper bound (lower
	# bounds are always 0)
	_NEQ_VAR_ORDER = ['x', 'y', 'g', 'z']
	_NEQ_VAR_ORDER_RHS = ["psi", "v", "phi"]

	def __post_init__(self):
		self.row_index = twoopt.data_processing.vector_index.RowIndex.make_from_schema(self.schema, ["y", "x", "z", "g"])
		self.validate()
		self.eq_lhs, self.eq_rhs = self.__make_eq()
		self.bnd = self.__init_bnd_matrix()
		self.obj = self.__init_obj()

	def __make_eq_lhs_rhs(self, j, rho, l):
		assert self.schema.get_index_bound("j") == self.schema.get_index_bound("i")
		vec = np.zeros(self.row_index.get_row_len())
		g_pos = self.row_index.get_pos("g", j=j, rho=rho, l=l)
		y_pos = self.row_index.get_pos("y", j=j, rho=rho, l=l)
		z_pos = self.row_index.get_pos("z", j=j, rho=rho, l=l)
		vec[g_pos] = 1
		vec[y_pos] = 1
		vec[z_pos] = 1

		if l > 0:
			y_prev_pos = self.row_index.get_pos("y", j=j, rho=rho, l=l - 1)
			vec[y_prev_pos] = -1

		for i in range(self.schema.get_index_bound("j")):
			if i != j:
				# Input: negative coefficient
				x_in_pos = self.row_index.get_pos("x", j=i, i=j, rho=rho, l=l)
				vec[x_in_pos] = -1
				# Output: positive coefficient
				x_out_pos = self.row_index.get_pos("x", j=j, i=i, rho=rho, l=l)
				vec[x_out_pos] = 1

		rhs = self.data_interface.get("x_eq", j=j, rho=rho, l=l)

		return vec, rhs

	def __make_eq(self):
		lhs = []
		rhs = []

		for indices in self.schema.index_permutations_as_dict("x_eq"):
			j = indices[1].pop("j")
			rho = indices[1].pop("rho")
			l = indices[1].pop("l")
			assert len(indices[1].items()) == 0  # There should only be "j", "rho", and "l"
			lhs_next, rhs_next = self.__make_eq_lhs_rhs(j=j, rho=rho, l=l)
			lhs.append(lhs_next)
			rhs.append(rhs_next)

		return lhs, rhs

	def validate(self):
		"""
		Ensures input data correctness
		"""
		assert self.schema.get_index_bound("i") == self.schema.get_index_bound("j")
		assert list(self.schema.variable_indices("x")) == ["j", "i", "rho", "l"]

		for var in ["x_eq", "y", "g", "z"]:
			log.debug(LinsolvPlanner, LinsolvPlanner.validate, "var", var, self.schema.variable_indices(var))
			assert list(self.schema.variable_indices(var)) == ["j", "rho", "l"]

	def __init_bnd_matrix(self):
		bnd = [[0, float("inf")] for _ in range(self.row_index.get_row_len())]

		for var, bnd_var in zip(LinsolvPlanner._NEQ_VAR_ORDER, LinsolvPlanner._NEQ_VAR_ORDER_RHS):
			# "z" upper limit is always "inf". It is not expected in input data
			if var != "z":
				assert list(self.schema.variable_indices(var)) == list(self.schema.variable_indices(bnd_var))

			for indices in ut.radix_cartesian_product(self.schema.variable_radix_base(var)):
				_, indices_dict = self.schema.indices_plain_to_dict(var, *indices)  # ETL
				pos = self.row_index.get_pos(var, **indices_dict)
				upper_bound = self.data_interface.get_plain(bnd_var, *indices)
				log.debug("var", var, "indices", indices, "upper_bound", upper_bound, "pos", pos)
				bnd[pos][1] = upper_bound

		log.debug("bnd", '\n\t' + '\n\t'.join(list(map(str, enumerate(bnd)))))
		return bnd

	def __init_obj(self):
		alpha_g = -self.data_interface.get_plain(
			"alpha_0")  # alpha_1 in the paper, inverted, because numpy can only solve minimization problems
		alpha_z = self.data_interface.get_plain(
			"alpha_1")  # alpha_2 in the paper, inverted, because numpy can only solve minimization problems
		assert not math.isclose(alpha_g, 0.0, abs_tol=1e-6)
		assert not math.isclose(alpha_z, 0.0, abs_tol=1e-6)
		stub = np.zeros(self.row_index.get_row_len())

		for j, rho, l in twoopt.data_processing.vector_index.radix_cartesian_product(self.schema.make_radix_map("j", "rho", "l")):
			pos_g = self.row_index.get_pos("g", j=j, rho=rho, l=l)
			pos_z = self.row_index.get_pos("z", j=j, rho=rho, l=l)
			stub[pos_g] = alpha_g
			stub[pos_z] = alpha_z

		return stub

	def solve(self):
		solution = scipy.optimize.linprog(c=self.obj, bounds=self.bnd, A_eq=self.eq_lhs, b_eq=self.eq_rhs)
		assert 0 == solution.status

		if 0 == solution.status:
			log.info(LinsolvPlanner.solve, "registering solution results in data interface")
			for variable in self.row_index.variables.keys():
				for indices in self.schema.index_permutations_as_dict(variable):
					log.debug(LinsolvPlanner.solve, indices)
					pos = self.row_index.get_pos(variable, **indices[1])
					self.data_interface.set(variable, solution.x[pos], **indices[1])

		return solution


class ProcessedDataAmountMaximizationDataInterface(twoopt.data_processing.data_interface.ConstrainedDataInterface):
    def __init__(self, data_interface_implementor):
        data_format = {
            # Max. available data to transfer
            "max_transferred": [
                "source_node"
                "destination_node"
                "virtualized_environment",
                "structural_stability_interval",
            ],
            "max_stored": [
                "node",
                "virtualized_environment",
                "structural_stability_interval",
            ],
            "input": [
                "node",
                "virtualized_environment"
                "structural_stability_interval",
            ]
        }
        data_format["transferred"] = data_format["max_transferred"]
        data_format["max_processed"] = data_format["max_stored"]
        data_format["processed"] = data_format["max_stored"]
        data_format["stored"] = data_format["max_stored"]
        data_format["dropped"] = data_format["max_stored"]


class ProcessedDataAmountMaximization:
    """
    Case:

    A network that uses virtualization technology.

    Ontology:

    - Types of operations:
        - Transfer
        - Load / save into memory
        - Process
        - Drop (due to channel constraints)
    - Network characteristics:
        - Maximum throughput
            - for transfer
            - for processing

    Objective:

    - Minimize the amount of dropped data
    - Maximize the amount of processed data

    Constraints:

    - Maximum transfer speed
    - Maximum processing speed
    - Maximum memory exchange speed
    """
    pass
