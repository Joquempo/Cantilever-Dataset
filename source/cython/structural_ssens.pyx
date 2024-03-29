"""
Dataset Generation
Topology Optimization of a Cantilever Beam
--------------------------------------------------------------------
Laboratory of Topology Optimization and Multiphysics Analysis
Department of Computational Mechanics
School of Mechanical Engineering
University of Campinas (Brazil)
--------------------------------------------------------------------
author  : Daniel Candeloro Cunha
version : 1.0
date    : May 2022
--------------------------------------------------------------------
To collaborate or report bugs, please look for the author's email
address at https://www.fem.unicamp.br/~ltm/

All codes and documentation are publicly available in the following
github repository: https://github.com/Joquempo/Cantilever-Dataset

If you use this program (or the data generated by it) in your work,
the developer would be grateful if you would cite the indicated
references. They are listed in the "CITEAS" file available in the
github repository.
--------------------------------------------------------------------
Copyright (C) 2022 Daniel Candeloro Cunha

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses
"""

# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

cimport cython

cdef void sens_serial(double [:] alpha_r, double [:] dens, double [:,::1] dKe, double [:] ug, double p, long long Nx, long long Ny):
    cdef long long N
    cdef long long e
    cdef long long k1
    cdef long long k2
    cdef double sval
    cdef long long nodes[4]
    cdef long long dofs[8]
    cdef double ue[8]
    cdef double fe[8]
    N = Nx*Ny
    for e in range(N):
        nodes[0] = e + e//Ny
        nodes[1] = nodes[0] + 1 + Ny
        nodes[2] = nodes[1] + 1
        nodes[3] = nodes[0] + 1
        for k1 in range(4):
            dofs[2*k1] = 2*nodes[k1]
            dofs[2*k1+1] = dofs[2*k1] + 1
        for k1 in range(8):
            ue[k1] = ug[dofs[k1]]
        sval = 0.0
        for k1 in range(8):
            fe[k1] = 0.0
            for k2 in range(8):
                fe[k1] = fe[k1] + dKe[k1][k2]*ue[k2] 
            sval = sval - ue[k1]*fe[k1]
        if p > 1 + 1e-9:
            sval = sval * p * (dens[e]**(p-1.0))
        alpha_r[e] = sval
    return

def str_ssens(alpha_r, dens, dKe, ug, p, Nx, Ny):
    sens_serial(alpha_r, dens, dKe, ug, p, Nx, Ny)
    return