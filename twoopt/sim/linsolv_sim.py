import pathlib
import sys
import simpy
from dataclasses import dataclass
import random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # We need files from "src/", that's how we access them
import ut


@dataclass
class SimInfo:
	row_index: object
	schema: object
	data_interface: object
	env: simpy.Environment

	def l(self):
		"""
		:return:  Id of the current structural stability interval
		"""
		pass

	def dt(self):
		return 1

	def time_before_tick(self):
		"""
		The process is modeled in "ticks" which are small fractions of time during which each node processes
		information in a random order
		"""
		return self.env.now - self.dt() * (self.env.now() // self.dt())


@dataclass
class Node:
	sim_info: SimInfo

	def __post_init__(self):
		pass

	def operations_init(self):
		pass

	def operations_perform(self):
		pass

	def excess_drop(self):
		pass

	def on_new_ssinterv(self, event):
		pass

	def run(self):
		while True:
			self.operations_init()
			self.operations_perform()
			self.excess_drop()

			yield self.sim_info.env.timeout(self.sim_info.simpy_timeout_duration())


@dataclass
class OpBase:
	sim_info: SimInfo
	container_in: simpy.Container
	indices: dict
	var_amount_planned: str  # The amount to be processed as per the plan
	var_intensity: str  # Physical limitations
	var_intensity_fraction: str  # The fraction of performance dedicated to the virtualized environment
	amount_processed: float = 0
	_EPSILON = 1e-5  # Small fraction of time. Helps to ensure the correct ordering of operations during one tick
	_PROCESS_MARGIN = 2 * _EPSILON  # Safe interval before the next tick

	#TODO: autoupdate l

	def __post_init__(self):
		assert self._EPSILON * 2 > self.sim_info.dt()

	def amount_planned(self):
		self.sim_info.data_interface.get(self.var_amount_planned, **self.indices)

	def intensity(self):
		self.sim_info.data_interface.get(self.var_intensity)

	intensity_neg = intensity  # Disk read / write speed. Expected to return an absolute value

	def intensity_fraction(self):
		self.sim_info.data_interface.get(self.var_intensity_fraction)

	intensity_fraction_neg = intensity_fraction

	def noise(self):
		ret = random.gauss(0, self.intensity() / 4)

		if ret < 0:
			ret = 0

		return ret

	noise_neg = noise

	def random_timeout_before_tick_margin(self):
		timeout = self.sim_info.time_before_tick()

		if timeout <= self._PROCESS_MARGIN:
			timeout = 0
		else:
			timeout -= self._PROCESS_MARGIN
			timeout = random.uniform(0, timeout)

		return timeout

	def amount_max_available(self):
		"""
		:return: Max. amount of information available for processing on this tick. Adjusted for noise, plan, and
		technical capabilities of the modeled node
		"""
		res = min(
			self.amount_planned() - self.amount_processed(),
			self.container_in.level,
		)
		intensity_adjusted = (self.intensity() * self.intensity_fraction() + self.noise()) * self.sim_info.dt()
		intensity_adjusted_neg = (self.intensity_neg() * self.intensity_fraction_neg() + self.noise_neg()) \
			* self.sim_info.dt()
		res = ut.clamp(res, -intensity_adjusted_neg, intensity_adjusted)

		return res

	def amount_processed_add(self, diff):
		self.amount_processed += diff


class TransferOp(OpBase):
	def __init__(self, container_out: simpy.Container, i, *args, **kwargs):
		"""
		:param container_out: Output container (link to another node)
		:param i: Output node id.
		"""
		self.container_out = container_out
		OpBase.__init__(*args, **kwargs)
		self.delayed_send = 0  # Send on the next tick

	def on_tick(self):
		"""
		Timing-based process. Guaranteed to finish before the end of a tick. Tries to extract a certain amount of
		information to process
		"""
		self.container_out.put(self.delayed_send)  # After the tick is passed, update the incoming buffer of the connected receiver

		yield self.sim_info.env.timeout(self.random_timeout_before_tick_margin())  # To prevent deterministic queueing

		amount = self.amount_max_available()
			get_request = self.container_in.get(amount)

		wait_result = yield get_request

		if get_request in wait_result:
			self.delayed_send = amount


class MemorizeOp(OpBase):
	_PROCESS_MARGIN = OpBase._PROCESS_MARGIN / 2  # It is expected that no other operation uses this value for margin. At the end of a tick,

	def on_tick(self):
		amount = self.amount_max_available()

		if amount > 0:
		else:
			# Extract excessive amount from the storage for node to process it
			self.amount_processed_add(amount)
			self.container_in.put(-amount)

			yield self.sim_info.env.timeout(self.sim_info.time_before_tick() - self._PROCESS_MARGIN)

			# After all the opearations have finished, save whatever has not been processed back, thus imitating
			# partial processing.

			amount = ut.clamp(-amount, 0, self.container_in.level)
			req = self.container_in.get(amount)
			
			wait_result = yield req

			if req in wait_result:
				self.amount_processed_add(amount)

	def noise(self):
		return 0.0


@dataclass
class LinsolvSimulation:
	sim_info: SimInfo
