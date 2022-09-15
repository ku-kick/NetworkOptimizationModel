
"""A particular implementation of a simulation variant. It is expected to be aware of the set of variables being
used, so the structures of Schema, Simulation, and the linear programming solver must be in agreement.

A rule of thumb. If an implementation relies on any presuppositions regarding variables being used (like using
hard-coded variable names), it should be implemented here.
"""

import pathlib
import random
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sim
import linsmat
import functools


class GeneratorOp(sim.core.Op):
	"""
	Some nodes receive input information from outside. GeneratorOp models this process.
	"""

	def amount_planned(self):
		return self.sim_env.data_interface.get("x_eq", **self.op_identity.indices)

	def intensity(self):
		tl = self.sim_env.data_interface.get("tl", self.op_identity.indices.get("l"))

	def intensity_fraction(self):
		return 1

	def on_tick_before(self):
		amount = self.amount_max_available()
		self.op_state.process(amount)


class Simulation(sim.core.SimEnv):

	def __post_init__(self):
		sim.core.SimEnv.__post_init__(self)
		self.__make_input_containers()
		self.__make_process_ops()
		self.__make_transfer_ops()

		assert self.schema.get_var_indices("tl") == ["l"]

	def __make_input_containers(self):
		self.input_containers = dict()  # {(j, rho): Container}

		for j, rho, l in self.schema.radix_map_iter("j", "rho", "l"):
			self.input_containers[(j, rho, l)] = sim.core.Container()

	def _input_container(self, j, rho, l):
		return self.input_containers[(j, rho, l)]

	def _transfer_op(self, j, i, rho, l):
		return self.transfer_ops[(j, i, rho, l)]

	def _is_connected(self, j, i, rho, l):
		"""
		Checks whether the planned network topology implies a channel between two nodes. If nothing is planned to be
		transfered between two nodes, or technical limitations imply no information flow between two nodes, the channel
		is considered absent.
		"""
		psi = self.data_interface.get("psi", j=j, i=i, rho=rho, l=l)
		mm = self.data_interface.get("mm_psi", j=j, i=i, rho=rho, l=l)
		x = self.data_interface.get("x", j=j, i=i, rho=rho, l=l)
		m = self.data_interface.get("m_psi", j=j, i=i, rho=rho, l=l)

		return psi > 0 and mm > 0 and x > 0 and m > 0

	def l(self, now):
		sum = 0

		for l in range(self.schema.get_index_bound("l")):
			sum += self.data_interface.get("tl", l)

			if now < sum:
				return l

	def duration(self):
		return sum(map(lambda l: self.data_interface.get("tl", l=l), range(self.schema.get_index_bound("l"))))

	def op_check_l(self, op, l):
		"""
		Checks whether op belongs to the current stability timespan
		"""
		return op.op_identity.indices["l"] == l

	def run(self):

		prev_l = 0
		self.trace = dict()

		for t in range(self.duration()):
			l = self.l(t)
			ops = self.generator_ops.values() + random.shuffle(self.ops.values()) + self.drop_ops.values()

			# Trigger "tick_before"
			for op in ops:
				if not self.op_check_l(op, l):
					continue

				if prev_l != l:
					if op.op_identity.var_amount_planned == "y":
						ind = op.op_identity.indices.copy()
						ind["l"] = l - 1
						# Keep the amount of processed info
						op.op_state.processed_container.amount = self.ops[("y", self.schema.indices_dict_to_plain("y", **ind))].op_state.processed_container.amount

					op.register_processed()

				op.tick_before()

			# Trigger "tick"
			for op in ops:
				if self.op_check_l(op, l):
					op.tick()

			# Trigger "tick_after"
			for op in ops:
				if self.op_check_l(op, l):
					op.tick_after()

			prev_l = l

	def __make_ops(self):
		"""
		The following core is a generalized way to initialize a simulation. However, operations differ slightly,
		so there are conditional patches here and there.
		"""
		self.generator_ops = dict()
		self.ops = dict()
		self.drop_ops = dict()  # Because of the nature of the simulated process, drop ops are a sort of "tear-down" and should be triggered last

		for var_amount_planned, var_intensity, var_intensity_fraction, var_amount_processed, op_type in zip(
				["x", "y", "g", "z", "x_eq"],  # Ops will be identified using this set of variables
				["mm_psi", "mm_v", "mm_phi", "", ""],  # TODO: Handle empty variables
				["m_psi", "m_v", "m_phi", "", ""],
				["x^", "y^", "g^", "z^", "x_eq^"],
				[sim.core.TransferOp, sim.core.MemorizeOp, sim.core.ProcessOp, sim.core.DropOp, sim.core.GeneratorOp]):
			for indices in self.schema.radix_map_iter_var_dict(var_amount_planned):
				j, rho, l = (indices[ind] for ind in ["j", "rho", "l"])

				if self.var_amount_planned == "x":
					i = indices["i"]

					# Optimization to prevent exponential explosion
					if not self._is_connected(j=j, i=i, rho=rho, l=l):
						continue

				indices_plain = (var_amount_planned, *self.schema.indices_dict_to_plain(var_amount_planned, **indices))
				storage = self.ops

				if var_amount_planned == "z":
					storage = self.drop_ops
				elif var_amount_planned == "x_eq":
					storage = self.generator_ops

				storage[indices_plain] = op_type(
					sim_env=self,
					op_identity=sim.core.OpIdentity(
						indices=indices,
						var_amount_planned=var_amount_planned,
						var_intensity={k: v for k, v in indices.items() if k != "rho"},
						var_intensity_fraction=var_intensity_fraction,
						var_amount_processed=var_amount_processed,
						indices_amount_planned=indices,
						indices_intensity=indices,
						indices_intensity_fraction=indices,
						indices_amount_processed=indices
					),
					op_state = sim.core.OpState(
						input_container=self._input_container(j=j, rho=rho, l=l),
						processed_container=sim.core.Container(),
					)
				)

				if var_amount_planned == "x_eq":
					# Initialize `var_intensity` and `var_intensity_fraction` for x_eq (external information inflow)
					amount_planned = self.data_interface.get(var_amount_planned, **indices)
					l_duration = self.data_interface.get("tl", indices["l"])
					self.data_interface.set(var_intensity, amount_planned / l_duration, **indices)
					self.data_interface.set(var_intensity_fraction, 1, **indices)
					# Initialize input containers with initial values
					self.ops[indices_plain].op_state.input_container.amount = self.data_interface.get("x_eq",
						**self.ops[indices_plain].op_indentity.indices)
					self.ops[indices_plain].op_state.output_container = self._input_container(j=j, rho=rho, l=l)

				if var_amount_planned == "x":
					storage[indices_plain].op_state.output_container = self._input_container(j=indices["i"], rho=rho,
						l=l)
