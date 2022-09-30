from dataclasses import dataclass
import linsmat
import ut
import random


@dataclass
class SimGlobal:
	dt: float = 1.0
	t: float = 0.0


@dataclass
class Container:
	amount: float


@dataclass
class Operation:
	sim_global: SimGlobal
	container_input: Container
	amount_planned: float
	indices_planned_plain: dict
	proc_intensity_upper: float
	proc_intensity_fraction: float
	proc_intensity_lower: float = None
	proc_noise_type: bool = None  # None, "gauss"
	amount_processed: float = 0.0

	def amount_input(self):
		return self.container_input.amount

	def __post_init__(self):
		if self.proc_intensity_lower is None:
			self.proc_intensity_lower = 0

	def amount_stash(self):
		return 0

	def amount_diff_planned(self):
		return self.amount_planned - self.amount_processed

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

	def __post_init__(self):
		Operation.__post_init__(self)
		self.container_output: Container = None

	def step(self):
		assert self.container_output is not None
		self._proc_step = self.amount_proc_available()
		self.amount_input_add(-self._proc_step)

	def step_transfer(self):
		""" Flush out the stashed `_proc_step into the output container """
		self.amount_processed_add(self._proc_step)
		self.container_output.amount = self._proc_step


class Simulation:
	env: linsmat.Env

	def transfer_ops_init(self):
		pass

	def transfer_ops_connect(self):
		pass
