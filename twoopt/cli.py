import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import linsmat
import argparse
from dataclasses import dataclass
import ut
import random
from generic import Log
import pygal
import sim
from sim import sim
import os


@dataclass
class RandomGenerator:
	"""
	Domain-aware random input generator. Generates constraints for the linear programming-based optimizer. Expects the
	provided schema to match the structure of data implied by the 2022 paper.

	Generated sequences have the "k/v" format: (k, v).
	"""
	schema_filename: str
	variables: list
	var_bounds: dict
	var_lower_bounds: dict

	def _functor_iter_wrapper(self):
		for var in self.variables:
			for prod in ut.radix_cartesian_product(self.schema.get_var_radix(var)):
				if var in self.var_lower_bounds.keys():
					yield (var, *prod,), random.uniform(self.var_lower_bounds[var], self.var_bounds[var])
				else:
					yield (var, *prod,), random.uniform(0, self.var_bounds[var])

	def __post_init__(self):
		self.schema = linsmat.Schema(None, self.schema_filename)
		self.iter_state = None

	def __iter__(self):
		self.iter_state = iter(self._functor_iter_wrapper())
		return self.iter_state

	def __next__(self):
		return next(self.iter_state)


def generate_random(schema, psi_upper, phi_upper, v_upper, x_eq_upper, mm_phi_upper, mm_v_upper, mm_psi_upper,
		tl_upper, output):
	sch = linsmat.Schema(None, schema)
	n_rho = sch.get_index_bound("rho")
	generator = RandomGenerator(schema, ["psi", "v", "phi", "alpha_1", "x_eq", "mm_phi", "mm_v", "mm_psi", "tl",
		"m_v", "m_psi", "m_phi"],
		dict(psi=psi_upper, phi=phi_upper, v=v_upper, alpha_1=1.0, x_eq=x_eq_upper, mm_phi=mm_phi_upper,
		mm_v=mm_v_upper, mm_psi=mm_psi_upper, tl=tl_upper, m_v=1.0 / n_rho, m_psi=1.0 / n_rho, m_phi=1.0 / n_rho),
		dict(m_v=1.0 / n_rho, m_psi=1.0 / n_rho, m_phi=1.0 / n_rho))
	ut.file_create_if_not_exists(output)
	csv_data_provider = linsmat.PermissiveCsvBufferedDataProvider(output)

	for k, v in generator:
		csv_data_provider.set_plain(*k, v)

	csv_data_provider.set_plain("alpha_0", 1 - csv_data_provider.get_plain("alpha_1"))
	csv_data_provider.sync()


def _parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("--generate-random", action="store_true", help="Gen. random constraints for the linear programming task based on a schema")
	parser.add_argument("--schema", type=str, help="Schema JSON file")
	parser.add_argument("--psi-upper", type=float, help="Upper bound for psi (upper bound in a le-constraint)")
	parser.add_argument("--phi-upper", type=float, help="Upper bound for phi (upper bound in a le-constraint)")
	parser.add_argument("--v-upper", type=float, help="Upper bound for v (upper bound in a le-constraint)")
	parser.add_argument("--x-eq-upper", type=float, help="Upper bound for x_jlrho (right side in an eq-constraint)")
	parser.add_argument("--mm-psi-upper", type=float, help="Upper bound for max throughput"),
	parser.add_argument("--mm_phi_upper", type=float, help="Upper bound for max performance"),
	parser.add_argument("--mm-v-upper", type=float, help="Upper bound for memory read/write speed")
	parser.add_argument("--tl-upper", type=float, help="Max duration of structural stability interval")
	parser.add_argument("--output", type=str, default=ut.Datetime.format_time(ut.Datetime.today()) + ".csv")

	return parser.parse_args()


class Format:
	"""
	Boilerplate reducers for representing output from various components in human-readable form
	"""

	@staticmethod
	def iter_numpy_result(res, schema):

		if res.success:
			row_index = linsmat.RowIndex.make_from_schema(schema, ["x", "y", "z", "g"])

			for var in ['x', 'y', 'g', 'z']:
				for indices in ut.radix_cartesian_product(schema.get_var_radix(var)):
					_, indices_map = schema.indices_plain_to_dict(var, *indices)
					pos = row_index.get_pos(var, **indices_map)

					yield ' '.join([var, str(indices_map), " = ", str(res.x[pos])])
		else:
			yield "Optimization failure"

	@staticmethod
	def numpy_result(res, schema):
		return '\n'.join(Format.iter_numpy_result(res, schema))

	@staticmethod
	def simulation_trace_graph_scatter(simulation: sim.Simulation, variables):
		"""
		:return: Graph object with "output()" method
		"""

		@dataclass
		class GraphObject:
			trace: object

			def output(self):
				try:
					os.mkdir("out")
				except FileExistsError:
					pass

				for k, series in self.trace:
					title = '_'.join(list(map(str, k)))
					chart = pygal.XY(stroke=True, title=title)

					for s in series:
						chart.add(title=s.title, values=s.as_line_x1y1())

						if s.title != "trajectory":
							Log.debug(s)

					chart.render_to_png("out/out_%s.svg" % title)

		return GraphObject(simulation.trace())


def _main():
	args = _parse_arguments()

	if args.generate_random:
		generate_random(args.schema, args.psi_upper, args.phi_upper, args.v_upper, args.output)
		generate_random(
			schema=args.schema,
			psi_upper=args.psi_upper,
			phi_upper=args.phi_upper,
			v_upper=args.v_upper,
			mm_psi_upper=args.mm_v_upper,
			mm_phi_upper=args.mm_phi_upper,
			mm_v_upper=args.mm_v_upper,
			output=args.output
		)


if __name__ == "__main__":
	_main()
