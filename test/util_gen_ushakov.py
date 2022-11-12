#!/usr/bin/python3

import sys
import itertools

N_J = 7
CONNECTED_PSI = [
	[
		(0, 1),
		(0, 2),
		(1, 3),
		(1, 6),
		(2, 3),
		(3, 1),
		(3, 5),
		(3, 6),
		(4, 3),
		(4, 5),
		(5, 3),
		(5, 6),
		(6, 1),
	],
	[
		(0, 2),
		(0, 1),
		(1, 3),
		(1, 6),
		(2, 3),
		(3, 1),
		(3, 6),
		(4, 3),
		(5, 6),
		(6, 1),
	],
	[
		(1, 3),
		(1, 6),
		(2, 3),
		(3, 1),
		(3, 6),
		(4, 3),
		(6, 1),
	],
]
L_DURATION = [4, 2, 1]
THROUGHPUT = 10  # Each inter-node channel has the same throughput value
N_RHO = 2
PSI_THROUGHPUT = 10  # Channel throughput, Mb/s. Each channel has the same one


def gen_psi():
	for l, lst in enumerate(CONNECTED_PSI):
		for rho in range(N_RHO):
			for i, j in lst:
				yield "psi", i, j, rho, l, L_DURATION[l] * PSI_THROUGHPUT


PHI_THROUGHPUT = [2, 5, 8, 12, 9, 3, 7]


def gen_phi():
	for l in range(len(L_DURATION)):
		for j, dphi_dt in enumerate(PHI_THROUGHPUT):
			for rho in range(N_RHO):
				yield "phi", j, rho, l, dphi_dt * L_DURATION[l]


V = [20, 20, 20, 50, 50, 10, 20]


def gen_v():
	for l in range(len(L_DURATION)):
		for j, v in enumerate(V):
			for rho in range(N_RHO):
				yield "v", j, rho, l, v


def gen_x_eq():
	yield "x_eq", 0, 0, 0, 100
	yield "x_eq", 0, 1, 0, 100
	yield "x_eq", 2, 0, 0, 50
	yield "x_eq", 2, 1, 0, 50
	yield "x_eq", 0, 0, 1, 50
	yield "x_eq", 0, 1, 1, 50
	yield "x_eq", 2, 0, 1, 60
	yield "x_eq", 2, 1, 1, 60
	yield "x_eq", 2, 0, 2, 50
	yield "x_eq", 2, 1, 2, 50


def gen():
	yield from gen_psi()
	yield from gen_phi()
	yield from gen_v()
	yield from gen_x_eq()

	alpha_1 = .5
	alpha_0 = 1.0 - alpha_1

	yield "alpha_0", alpha_0
	yield "alpha_1", .9


def main():
	for line in gen():
		print(' '.join(map(str, line)))


if __name__ == "__main__":
	    main()
