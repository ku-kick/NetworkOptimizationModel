# Encapsulates working with data.
# The format adopted for data is list of dictionaries with keys comprised of values stored in Generation.SCHEME.
# The indices, namely i, j, l are counted from 1. The appropriate adjustments must be taken by data consuming modules,
# such as linsolv_model

from random import Random, randint, uniform, random
import csv
import re
import pickle


class KvData(dict):
	"""
	Stores key-value data pairs in format {(str(VAR), int(INDEX1), int(INDEX2), ...) : numeric(VALUE)}
	"""

	def save(self, filename):
		with open(filename, 'wb') as f:
			pickle.dump(dict(self), f)

	def load(self, filename):
		with open(filename, 'rb') as f:
			self.update(pickle.load(f))

	def get(self, var, *indices):
		key = KvData._as_key(var, *indices)

		if key in self.keys():
			return self[key]
		else:
			self._generate(key)
			return self.get(var, *indices)

	def reset(self, var, *indices):
		self.pop(KvData._as_key(var, *indices), None)

	def get_reset(self, var, *indices):
		self.reset(var, *indices)
		return self.get(var, *indices)

	def __str__(self):
		res = []

		for k in self.keys():
			v = self[k]
			v = round(v, 2)
			k_str = ' '.join([str(i) for i in k])
			res.append(' = '.join([k_str, str(v)]))

		return '\n'.join(res)

	@staticmethod
	def _as_key(var, *indices):
		var = str(var)
		indices = (int(i) for i in indices)
		return (var, *indices,)

	def _generate(self, key):
		"""
		Either generates a key guaranteeing its presence in the dictionary, or throws an assertion
		"""
		raise NotImplemented

	def set(self, val, var, *indices):
		key = KvData._as_key(var, *indices)
		self[key] = val

	def contains(self, var, *indices):
		return KvData._as_key(var, *indices) in self.keys()


class RandomKvData(KvData):

	PSI_JL_MAX = 3.0  # Max channel throughput
	V_J_MAX = 1.0  # Max memory for node J
	PHI_JL_MAX = 1.5  # Max node performance
	N_L = 2  # Number of structural stability intervals
	N_J = 3  # Number of nodes
	CONNECTEDNESS = .6  # Probability that there is a link b/w 2 nodes
	X_JL_MAX = 2.0  # Data threshold, max constraint value. Fixed amount of data that should be processed on a given node during structural stability timespan `L`

	@staticmethod
	def _uniform(a, b):
		f_float = type(a) is float or type(b) is float

		if f_float:
			return uniform(a, b)
		else:
			return randint(a ,b)

	@staticmethod
	def _is_connected() -> int:
		return int(random() < RandomKvData.CONNECTEDNESS)

	def _generate(self, key):

		var = key[0]

		gen_map = {
			'v_j': lambda: RandomKvData._uniform(0, RandomKvData.V_J_MAX),
			'phi_jl': lambda: RandomKvData._uniform(0, RandomKvData.PHI_JL_MAX),
			'x_jl': lambda: RandomKvData._uniform(0, RandomKvData.X_JL_MAX),
			'psi_jil': lambda: RandomKvData._is_connected() * RandomKvData._uniform(0, RandomKvData.PSI_JL_MAX),
			'm': lambda: RandomKvData.N_J,  # Number of nodes
			'k': lambda: RandomKvData.N_L,  # Number of structural stability intervals
			'alpha_1': lambda: RandomKvData._uniform(0, 1.0),
			'alpha_2': lambda: 1 - self.get('alpha_1')
		}
		assert var in gen_map.keys()
		assert not self.contains(key)
		generated = gen_map[var]()
		self.set(generated, *key)


class UiKvData(KvData):

	def _generate(self, key):
		"""
		Forms dictionary of values according to the following format:
		{(str(VAR), int(INDEX1), int(INDEX2), ...) : float(VALUE)}
		"""
		while True:
			if self.contains(key):
				return

			raw_inp = input(str(key))
			inp = raw_inp.strip()
			inp = re.split(r'\s+', inp)
			cmd = inp[0] if len(inp) else ''

			try:
				if cmd == '?':
					print('\n'.join([
						"?                           help",
						"edit VAR INDEX1 INDEX2 ...  change entry",
						"show                        show all"
					]))

				elif cmd == 'show':
					for k in self.keys():
						print(f"{k}  -  {self[k]}")

				elif cmd == 'edit':
					k = KvData._as_key(*inp[1:])

					res = self.pop(k, None)
					print(f"Removed: {res}")

					while k not in self.keys():
						self._generate(k)

				else:
					val = float(eval(raw_inp))
					self.set(val, *key)

					return

			except Exception as e:
				print(str(e))


class Generation:

	SCHEME = ["l", "j", "i", "psi_jil", "v_j", "phi_jl", "x_jl", "alpha_1", "alpha_2"]

	@staticmethod
	def iter_generate_kv(kv_data: KvData, f_gen_scheme = True):
		if f_gen_scheme:
			yield Generation.SCHEME

		alpha_1 = kv_data.get('alpha_1')
		alpha_2 = kv_data.get('alpha_2')

		for j in range(int(kv_data.get('m'))):
			v_j = kv_data.get('v_j', j)

			for l in range(int(kv_data.get('k'))):
				phi_jl = kv_data.get('phi_jl', j, l)
				x_jl  = kv_data.get('x_jl', j, l)

				for i in range(int(kv_data.get('m'))):
					if i == j:
						continue

					psi_jil = kv_data.get('psi_jil', j, i, l)

					yield [l, j, i, psi_jil, v_j, phi_jl, x_jl, alpha_1, alpha_2]

	@staticmethod
	def generate_kv(kv_data, f_gen_scheme=True):
		return list(Generation.iter_generate_kv(kv_data, f_gen_scheme))

	@staticmethod
	def file_generate_kv(filename, kv_data, f_gen_scheme=True):
		with open(filename, 'w') as f:
			writer = csv.writer(f)

			for row in Generation.iter_generate_kv(kv_data, f_gen_scheme):
				writer.writerow(row)


class Read:
	@staticmethod
	def readf_iter(filename):
		with open(filename, 'r') as f:
			reader = csv.DictReader(f)

			for row in reader:
				yield(row)

	@staticmethod
	def search_iter(data_iterable, condition=lambda row: None):
		for d in data_iterable:
			if condition(d):
				yield(d)


if __name__ == "__main__":
	Generation.file_generate('data.csv')

	for r in Read.readf_iter("data.csv"):
		print(r)
