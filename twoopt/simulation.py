from dataclasses import dataclass
import linsmat
import ut
import random


@dataclass
class SimGlobal:
	dt: float = 1.0
	t: float = 0.0


@dataclass
class Operation:
	sim_global: SimGlobal
	amount_input: float
	amount_output: object
	amount_planned: float
	indices_planned_plain: dict
	proc_intensity_upper: float
	proc_intensity_fraction: float
	proc_intensity_lower: float = None
	proc_noise_type: bool = None  # None, "gauss"
	amount_processed: float = 0.0

	def __post_init__(self):
		if self.proc_intensity_lower is None:
			self.proc_intensity_lower = 0

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

	def amount_step(self):
		diff_planned = self.amount_diff_planned()

		if self.proc_intensity_lower == 0.0:
			amount_step_lower = 0.0
		else:
			amount_step_lower = (self.proc_intensity_lower * self.proc_intensity_fraction + self.noise())\
								* self.sim_global.dt

		amount_step_upper = (self.proc_intensity_upper * self.proc_intensity_fraction + self.noise())\
							* self.sim_global.dt
		amount_step = ut.clamp(diff_planned, amount_step_lower, amount_step_upper)

		return amount_step


class Simulation:
	env: linsmat.Env

	def make_ops_trasnfer(self):
		pass

	def connect_ops_transfer(self):
		pass
