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
from dataclasses import dataclass, field
from sim import core
from generic import Log
import ut


@dataclass
class GeneratorOp:
	sim_env: core.SimEnv
	op_identity: core.OpIdentity
	op_state: core.OpState

	def amount_planned(self):
		return self.sim_env.data_interface.get("x_eq", **self.op_identity.indices)

	def intensity(self):
		tl = self.sim_env.data_interface.get("tl", l=self.op_identity.indices.get("l"))
		amount = self.sim_env.data_interface.get(self.op_identity.var_amount_planned, **self.op_identity.indices)

		return amount / tl

	intensity_neg = intensity

	def intensity_fraction(self):
		return 1

	intensity_fraction_neg = intensity_fraction

	def on_tick_before(self):
		amount = self.amount_max_available()
		self.op_state.process(amount)

	def noise(self):
		return 0.0

	noise_neg = noise

	def on_tick(self):
		pass

	def on_tick_after(self):
		pass

	def register_processed(self):
		self.sim_env.data_interface.set(self.op_identity.var_amount_processed, self.op_state.processed_container.amount,
			**self.op_identity.indices)


	def amount_max_available(self):
		"""
		:return: Max. amount of information available for processing on this tick. Adjusted for noise, plan, and
		technical capabilities of the modeled node
		"""
		res = min(
			self.amount_planned() - self.op_state.processed_container.amount,
			self.op_state.input_container.amount,
		)
		intensity_adjusted = (self.intensity() * self.intensity_fraction() + self.noise()) * self.sim_env.dt()
		intensity_adjusted_neg = (self.intensity_neg() * self.intensity_fraction_neg() + self.noise_neg()) \
			* self.sim_env.dt()
		res = ut.clamp(res, -intensity_adjusted_neg, intensity_adjusted)

		return res


class Simulation(core.SimEnv):

	@staticmethod
	def make_from_file(*args, **kwargs):
		env = core.SimEnv.make_from_file(*args, **kwargs)

		return Simulation(row_index=env.row_index, schema=env.schema, data_interface=env.data_interface)

	@dataclass
	class Trace:
		"""
		Accumulated history of ticks
		"""

		schema: object
		state: dict = field(default_factory=dict)

		def add_point(self, op):
			index = self.schema.indices_dict_to_plain(op.op_identity.var_amount_processed,
				**op.op_identity.indices_amount_processed)
			index = tuple(index)

			if index not in self.state:
				self.state[index] = list()

			self.state[index].append(op.op_state.processed_container.amount)


	def _ops_all(self):
		generic_ops = list(self.ops.values())
		random.shuffle(generic_ops)
		return list(self.generator_ops.values()) + generic_ops + list(self.drop_ops.values())

	def __post_init__(self):
		sim.core.SimEnv.__post_init__(self)
		self.reset()

	def reset(self):
		self.__make_input_containers()
		self.__make_ops()
		self._trace = self.Trace(self.schema)  # Accumulated time series for each node

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
		mm = self.data_interface.get("mm_psi", j=j, i=i, l=l)
		x = self.data_interface.get("x", j=j, i=i, rho=rho, l=l)
		m = self.data_interface.get("m_psi", j=j, i=i, rho=rho, l=l)

		return psi > 0 and mm > 0 and x > 0 and m > 0

	def l(self, now):
		sum = 0

		for l in range(self.schema.get_index_bound("l")):
			sum += self.data_interface.get("tl", l=l)

			if now < sum:
				return l

	def duration(self):
		return sum(map(lambda l: self.data_interface.get("tl", l=l), range(self.schema.get_index_bound("l"))))

	def op_check_l(self, op, l):
		"""
		Checks whether op belongs to the current stability timespan
		"""
		return op.op_identity.indices["l"] == l

	def trace(self):
		return self._trace.state.items()

	def _t_iter(self):
		return ut.frange(0, self.duration(), self.dt())

	def run(self):

		prev_l = 0
		self._trace = self.Trace(self.schema)

		for t in self._t_iter():
			Log.debug(Simulation.run, "current time", t)
			l = self.l(t)
			ops = self._ops_all()

			# Trigger "tick_before"
			for op in ops:
				self._trace.add_point(op)  # Place a new tick in the history

				if not self.op_check_l(op, l):
					continue

				if prev_l != l:
					if op.op_identity.var_amount_planned == "y":
						ind = op.op_identity.indices.copy()
						ind["l"] = l - 1
						# Keep the amount of processed info
						op.op_state.processed_container.amount = self.ops[self.schema.indices_dict_to_plain("y", **ind)].op_state.processed_container.amount

					op.register_processed()

				op.on_tick_before()

			# Trigger "tick"
			for op in ops:
				if self.op_check_l(op, l):
					op.on_tick()

			# Trigger "tick_after"
			for op in ops:
				if self.op_check_l(op, l):
					op.on_tick_after()

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
				["mm_psi", "mm_v", "mm_phi", "", "mm_x_eq"],  # TODO: Handle empty variables
				["m_psi", "m_v", "m_phi", "", ""],
				["x^", "y^", "g^", "z^", "x_eq^"],
				[sim.core.TransferOp, sim.core.MemorizeOp, sim.core.ProcessOp, sim.core.DropOp, GeneratorOp]):
			for indices in self.schema.radix_map_iter_var_dict(var_amount_planned):
				j, rho, l = [indices[1][ind] for ind in ["j", "rho", "l"]]

				if var_amount_planned == "x":
					i = indices[1]["i"]

					# Optimization to prevent exponential explosion
					if not self._is_connected(j=j, i=i, rho=rho, l=l):
						continue

				indices_plain = self.schema.indices_dict_to_plain(var_amount_planned, **indices[1])
				storage = self.ops

				if var_amount_planned == "z":
					storage = self.drop_ops
				elif var_amount_planned == "x_eq":
					storage = self.generator_ops

				storage[indices_plain] = op_type(
					sim_env=self,
					op_identity=sim.core.OpIdentity(
						indices=indices[1],
						var_amount_planned=var_amount_planned,
						var_intensity=var_intensity,
						var_intensity_fraction=var_intensity_fraction,
						var_amount_processed=var_amount_processed,
						indices_amount_planned=indices[1],
						indices_intensity=dict(filter(lambda d: d[0] != "rho", indices[1].items())),
						indices_intensity_fraction=indices[1],
						indices_amount_processed=indices[1]
					),
					op_state = sim.core.OpState(
						input_container=self._input_container(j=j, rho=rho, l=l),
						processed_container=sim.core.Container(),
					)
				)

				if var_amount_planned == "x_eq":
					# Initialize input containers with initial values
					storage[indices_plain].op_state.input_container.amount = self.data_interface.get("x_eq",
						**storage[indices_plain].op_identity.indices)
					storage[indices_plain].op_state.output_container = self._input_container(j=j, rho=rho, l=l)

				if var_amount_planned == "x":
					storage[indices_plain].op_state.output_container = self._input_container(j=indices[1]["i"], rho=rho,
						l=l)
