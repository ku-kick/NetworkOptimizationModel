import pathlib
import sys
from dataclasses import dataclass
import random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # We need files from "src/", that's how we access them
import ut
import linsmat
from generic import Log


@dataclass
class SimEnv(linsmat.Env):
	def l(self):
		"""
		:return:  Id of the current structural stability interval
		"""
		pass

	def dt(self):
		return 1


@dataclass
class OpIdentity:
	"""
	Stores info or how the op. is addressed.
	"""
	indices: dict
	var_amount_planned: str  # The amount to be processed as per the plan
	var_intensity: str  # Physical limitations
	var_intensity_fraction: str  # The fraction of performance dedicated to the virtualized environment
	var_amount_processed: str
	indices_amount_planned: object
	indices_intensity: object
	indices_intensity_fraction: object
	indices_amount_processed: object


@dataclass
class Container:
	amount: float = 0.0


@dataclass
class OpState:
	input_container: Container  # "o(t)" in the paper, the amount that a node should process during that tick
	processed_container: Container  # x^, y^, z^, g^ in the paper
	output_container: Container = None

	def process(self, diff):
		assert(diff <= self.input_container.amount)
		self.input_container.amount -= diff
		self.processed_container += diff

		if self.output_container is not None:
			self.output_container += diff


@dataclass
class Op:
	sim_env: SimEnv
	op_identity: OpIdentity
	op_state: OpState

	def register_processed(self):
		self.sim_env.data_interface.set(self.op_identity.var_amount_processed, self.op_state.processed_container,
			**self.op_identity.indices)

	def var_value_get(self, var_name, index_names):
		return self.sim_env.data_interface.get(var_name, **{i: self.op_identity.indices[i] for i in index_names})

	def on_tick_before(self):
		"""
		Set up
		"""
		pass

	def on_tick(self):
		pass

	def on_tick_after(self):
		"""
		Tear down
		"""
		pass

	def intensity(self):
		"""
		Wrapper over data interface
		"""
		Log.debug(Op.intensity, self.op_identity.indices_intensity)
		return self.var_value_get(self.op_identity.var_intensity, self.op_identity.indices_intensity)

	intensity_neg = intensity  # Disk read / write speed. Expected to return an absolute value

	def intensity_fraction(self):
		return self.var_value_get(self.op_identity.var_intensity_fraction, self.op_identity.indices_intensity_fraction)

	intensity_fraction_neg = intensity_fraction

	def noise(self):
		ret = random.gauss(0, self.intensity() / 4)

		if ret < 0:
			ret = 0

		return ret

	noise_neg = noise

	def amount_planned(self):
		return self.var_value_get(self.op_identity.var_amount_planned, self.op_identity.indices_amount_planned)

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
			* self.sim_info.dt()
		res = ut.clamp(res, -intensity_adjusted_neg, intensity_adjusted)

		return res


class TransferOp(Op):

	def on_tick(self):
		self.amount = self.amount_max_available()
		self.op_state.processed_container -= self.amount
		# TODO: register processed

	def on_tick_after(self):
		self.op_state.output_container += self.amount


class MemorizeOp(Op):
	def noise(self):
		return 0.0

	def on_tick_before(self):
		self.amount = self.amount_max_available()

		if self.amount < 0:
			# Try to process the excessive amount of information
			self.op_state.process(self.amount)

	def on_tick(self):
		if self.amount > 0:
			self.op_state.process(self.amount)

	def on_tick_after(self):
		# XXX: What if it does not manage to process the excess during the structural stability span? (The heck with it then)
		# Put the unprocessed info back into memory
		if self.amount < 0:
			self.amount = ut.clamp(self.amount, -self.op_state.input_container.amount, 0)
			self.op_state.input_container.process(self.amount)


class ProcessOp(Op):

	def on_tick(self):
		amount = self.amount_max_available()
		self.op_state.process(amount)


class DropOp(Op):
	def intensity(self):
		return float("inf")

	def intensity_fraction(self):
		return 1

	def noise(self):
		return 0

	def on_tick(self):
		amount = self.op_state.input_container.amount
		self.op_state.process(amount)
