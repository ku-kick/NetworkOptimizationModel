from dataclasses import dataclass, field
from math import log

import linsmat
import ut
import random
import generic
import math
import functools

log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


@dataclass
class SimGlobal:
	helper_virt: linsmat.HelperVirt = None
	dt: float = 1.0
	t: float = 0.0
	l: int = 0
	__new_l: bool = False

	def t_inc(self):
		self.new_l = False
		self.t += self.dt

		while self.t >= self.helper_virt.tl(self.l):
			self.l += 1
			log.info(SimGlobal, "updated l. New l: ", self.l)
			self.__new_l = True

	def is_new_l(self):
		return self.new_l


@dataclass
class Container:
	amount: float = 0.0


@dataclass
class Operation:
	sim_global: SimGlobal
	indices_planned_plain: dict  # For identification
	val_l: float
	amount_planned: float
	proc_intensity_fraction: float
	proc_intensity_upper: float
	proc_intensity_lower: float = None
	proc_noise_type: bool = None  # None, "gauss"
	amount_processed: float = 0.0
	container_input: Container = field(default_factory=Container)

	def is_current_l(self):
		return self.sim_global.l == self.val_l

	def reset(self):
		self.container_input.amount = 0.0
		self.amount_processed = 0.0

	def as_str_short(self):
		return '_'.join(map(str, self.indices_planned_plain))

	id_tuple = as_str_short  # Compatibility

	def amount_input(self):
		return self.container_input.amount

	def __post_init__(self):
		if self.proc_intensity_lower is None:
			self.proc_intensity_lower = 0

	def amount_stash(self):
		return 0

	def amount_diff_planned(self):
		return self.amount_planned - self.amount_processed

	def set_container_input(self, c: Container):
		self.container_input = c

	def noise(self):
		if self.proc_noise_type is None:
			return 0.0
		elif self.proc_noise_type is "gauss":
			diff_planned = self.amount_diff_planned()

			if diff_planned > 0:
				return random.gauss(0, self.proc_intensity_upper / 4)
			else:
				return random.gauss(0, self.proc_intensity_lower / 4)

	def amount_processed_add(self, diff):
		self.amount_processed += diff

	def amount_input_add(self, diff):
		self.container_input.amount += diff

	def amount_proc_available(self):
		""" How much to process during this step """
		diff_planned = self.amount_diff_planned()

		if self.proc_intensity_lower == 0.0:
			amount_step_lower = 0.0
		else:
			amount_step_lower = (self.proc_intensity_lower * self.proc_intensity_fraction + self.noise())\
								* self.sim_global.dt

		amount_step_upper = (self.proc_intensity_upper * self.proc_intensity_fraction + self.noise())\
							* self.sim_global.dt
		amount_step = ut.clamp(diff_planned, amount_step_lower, amount_step_upper)  # What is available due to technical limitations
		amount_step = ut.clamp(amount_step, -self.amount_stash(), self.amount_input())  # What is available according to the amount of stashed / received

		return amount_step


class TransferOp(Operation):

	def __init__(self, *args, **kwargs):
		self.container_output = kwargs.pop("container_output", None)
		Operation.__init__(self, *args, **kwargs)

	def __post_init__(self):
		log.verbose("created TranferOp", str(self))
		Operation.__post_init__(self)

		if math.isclose(0.0, self.amount_planned, abs_tol=0.001):
			log.warning("created TransferOp", self.as_str_short(), "with the planned amount being equal zero")

	def set_container_output(self, c: Container):
		self.container_output = c

	def step(self):
		assert self.container_output is not None
		self._proc_step = self.amount_proc_available()
		self.amount_input_add(-self._proc_step)

	def step_teardown(self):
		""" Flush out the stashed `_proc_step into the output container """
		self.amount_processed_add(self._proc_step)
		self.container_output.amount = self._proc_step
		self._proc_step = 0.0


class StoreOp(Operation):

	def __init__(self, *args, **kwargs):
		self.container_processed: Container = kwargs.pop("container_processed")
		Operation.__init__(self, *args, **kwargs)

	def amount_stash(self):
		return self.amount_processed

	def step(self):
		self.amount_processed = self.container_processed.amount  # Ensures connectedness b/w ops on different structural stability spans
		self.__amount_proc = self.amount_proc_available()
		self.amount_input_add(-self.__amount_proc)
		self.amount_processed_add(self.__amount_proc)

	def step_teardown(self):
		if self.__amount_proc < 0:
			self.__amount_proc = ut.clamp(self.__amount_proc, -self.amount_input(), 0)  # Store it back
			self.amount_input_add(self.__amount_proc)
			self.amount_processed_add(-self.__amount_proc)

		self.container_processed.amount = self.amount_processed  # Ensures connectedness b/w ops on different structural stability spans


class ProcessOp(Operation):

	def step(self):
		amount_proc = self.amount_proc_available()
		self.amount_input_add(-amount_proc)
		self.amount_processed_add(amount_proc)


class DropOp(Operation):
	def step(self):
		self.amount_processed_add(self.amount_input())
		self.container_input.amount = 0


class GenerateOp(Operation):

	def step(self):
		self.container_input.amount = self.proc_intensity_upper


@dataclass
class Simulation:
	env: linsmat.Env
	helper_virt: linsmat.HelperVirt = None

	def containers_add_by_plain(self, indices_plain: tuple, c: Container):
		self.containers[indices_plain] = c

	def container_by_plain(self, indices_plain):
		return self.containers[indices_plain]

	def _init_make_containers(self):
		for indices in self.helper_virt.indices_container_iter_plain():
			log.verbose("creating container with indices", indices, self.containers)
			self.containers_add_by_plain(indices, Container())

	def transfer_ops_add(self, op):
		self.transfer_ops[op.indices_planned_plain] = op

	def _init_make_transfer_ops(self):
		for indices in self.helper_virt.indices_transfer_iter_plain():
			if self.helper_virt.indices_transfer_is_connected(indices):
				# Ensure connectedness by picking the correct input and output containers
				#TODO indices: missing variable str
				indices_container_input = self.helper_virt.indices_transfer_to_indices_container_sender(indices)
				container_input = self.container_by_plain(indices_container_input)
				indices_container_output = self.helper_virt.indices_transfer_to_indices_container_receiver(indices)
				container_output = self.container_by_plain(indices_container_output)
				# Create the op itself
				op = TransferOp(sim_global=self.sim_global, indices_planned_plain=indices,
					val_l = self.helper_virt.indices_transfer_l(indices),
					amount_planned=self.helper_virt.amount_planned_transfer(indices),
					proc_intensity_fraction=self.helper_virt.intensity_fraction_transfer(indices),
					proc_intensity_upper=self.helper_virt.intensity_upper_transfer(indices),
					container_input=container_input, container_output=container_output, proc_noise_type="gauss")
				# Register the op
				self.transfer_ops_add(op)
				log.verbose("created TransferOp", op)

	def store_ops_add(self, op):
		self.store_ops[op.indices_planned_plain] = op

	def _init_make_containers_processed(self):
		for indices in self.helper_virt.indices_container_processed_iter_plain():
			log.verbose("containers processed index", indices)
			self.containers_processed[indices] = Container()

	def _init_make_store_ops(self):
		for indices in self.helper_virt.indices_store_iter_plain():
			op = StoreOp(sim_global=self.sim_global, indices_planned_plain=indices,
				val_l=self.helper_virt.indices_store_l(indices),
				amount_planned=self.helper_virt.amount_planned_store(indices),
				proc_intensity_fraction=self.helper_virt.intensity_fraction_store(indices),
				proc_intensity_upper=self.helper_virt.intensity_upper_store(indices),
				proc_intensity_lower=-self.helper_virt.intensity_upper_store(indices),
				container_input=self.container_by_plain(
					self.helper_virt.indices_store_to_indices_container(indices)),
				container_processed=self.containers_processed[
					self.helper_virt.indices_store_to_indices_container_processed(indices)])
			self.store_ops_add(op)

	def process_ops_add(self, op):
		self.process_ops[op.indices_planned_plain] = op

	def _init_make_process_ops(self):
		for indices in self.helper_virt.indices_process_iter_plain():
			op = ProcessOp(sim_global=self.sim_global, indices_planned_plain=indices,
				val_l=self.helper_virt.indices_process_l(indices),
				amount_planned=self.helper_virt.amount_planned_process(indices),
				proc_intensity_fraction=self.helper_virt.intensity_fraction_process(indices),
				proc_intensity_upper=self.helper_virt.intensity_upper_process(indices),
				container_input=self.container_by_plain(self.helper_virt.indices_process_to_indices_container(indices)))
			self.process_ops_add(op)

	def drop_ops_add(self, op):
		self.drop_ops[op.indices_planned_plain] = op

	def _init_make_drop_ops(self):
		for indices in self.helper_virt.indices_drop_iter_plain():
			op = ProcessOp(sim_global=self.sim_global, indices_planned_plain=indices,
				val_l=self.helper_virt.indices_drop_l(indices),
				amount_planned=self.helper_virt.amount_planned_drop(indices),
				proc_intensity_fraction=self.helper_virt.intensity_fraction_drop(indices),
				proc_intensity_upper=self.helper_virt.intensity_upper_drop(indices),
				container_input=self.container_by_plain(self.helper_virt.indices_drop_to_indices_container(indices)))
			self.drop_ops_add(op)

	def generate_ops_add(self, op):
		self.generate_ops[op.indices_planned_plain] = op

	def _init_generate_ops(self):
		for indices in self.helper_virt.indices_generate_iter_plain():
			op = GenerateOp(sim_global=self.sim_global, indices_planned_plain=indices,
				val_l=self.helper_virt.indices_generate_l(indices),
				amount_planned=self.helper_virt.amount_planned_generate(indices), proc_intensity_fraction=1.0,
				proc_intensity_upper=self.helper_virt.intensity_upper_generate(indices),
				container_input=self.container_by_plain(
				self.helper_virt.indices_generate_to_indices_container(indices)))
			self.generate_ops_add(op)

	def __post_init__(self):
		if self.helper_virt is None:
			self.helper_virt = linsmat.HelperVirt(env=self.env)

		self.sim_global = SimGlobal(self.helper_virt)
		self.containers = dict()
		self._init_make_containers()
		self.containers_processed = dict()
		self._init_make_containers_processed()
		self.transfer_ops = dict()
		self._init_make_transfer_ops()
		self.store_ops = dict()
		self._init_make_store_ops()
		self.process_ops = dict()
		self._init_make_process_ops()
		self.drop_ops = dict()
		self._init_make_drop_ops()
		self.generate_ops = dict()
		self._init_generate_ops()

	def ops_all(self):
		return sum(functools.reduce(lambda a, b: list(a) + list(b),
			[self.drop_ops.items(), self.generate_ops.items(), self.process_ops.items(), self.store_ops.items(),
			self.transfer_ops.items()], []))

	def payload_ops_shuffled(self):
		ops = list(self.process_ops.items()) + list(self.transfer_ops.items()) + list(self.store_ops.items())
		random.shuffle(ops)

		return ops

	def teardown_ops(self):
		return list(self.process_ops.items()) + list(self.store_ops.items())

	def reset(self):
		self.sim_global.t = 0.0
		self.sim_global.l = 0

		for op in self.ops_all():
			op.reset()

	def step(self):
		for op in self.generate_ops.items():
			if op.is_current_l():
				op.step()

		for op in self.payload_ops_shuffled():
			if op.is_current_l():
				op.step()

		for op in self.teardown_ops():
			if op.is_current_l():
				op.step_teardown()

		for op in self.drop_ops.items():
			if op.is_current_l():
				op.step()

		self.sim_global.t_inc()
