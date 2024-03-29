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

#%% Imports
import os, sys, gc, pickle
import numpy as np
from time import time
from datetime import datetime
from scipy.sparse import coo_matrix
from sksparse.cholmod import analyze

sys.path.append('../../cython/')
from structural_bsens import str_cgs
from structural_filter import str_filter

#%% Setup

# fixed properties
VV = 0.015625     # maximal volume variation
TV = 0.031250     # maximal topology variation
rmax = 0.125      # sensitivity filter radius
patience = 20     # patience stop criterion
momentum = 0.50   # sensitivity momentum
Ey = 1.0          # Young's modulus
nu = 0.3          # Poisson's coefficient
epsk = 1e-6       # soft-kill parameter
Ly = 1.0          # cantilever height
small = 1e-14     # small value to compare float numbers

noptf   = 16      # number of optimizations to be stored in the same file
fid_ini = 0       # initial input index |run from input 0
fid_lim = 148240  # input index limit   |up to input 148239

# Elemental Matrix (Quad4) - Plane Stress State
### numbering rule
### 3_____2
### | (e) |
### 0_____1
kk = (Ey/(1-nu**2))*np.array([ 1/2-nu/6 ,  1/8+nu/8, -1/4-nu/12, -1/8+3*nu/8,
                              -1/4+nu/12, -1/8-nu/8,      nu/6 ,  1/8-3*nu/8])
Ke = np.array([[kk[0],kk[1],kk[2],kk[3],kk[4],kk[5],kk[6],kk[7]],
               [kk[1],kk[0],kk[7],kk[6],kk[5],kk[4],kk[3],kk[2]],
               [kk[2],kk[7],kk[0],kk[5],kk[6],kk[3],kk[4],kk[1]],
               [kk[3],kk[6],kk[5],kk[0],kk[7],kk[2],kk[1],kk[4]],
               [kk[4],kk[5],kk[6],kk[7],kk[0],kk[1],kk[2],kk[3]],
               [kk[5],kk[4],kk[3],kk[2],kk[1],kk[0],kk[7],kk[6]],
               [kk[6],kk[3],kk[4],kk[1],kk[2],kk[7],kk[0],kk[5]],
               [kk[7],kk[2],kk[1],kk[4],kk[3],kk[6],kk[5],kk[0]]])
Kevec = Ke.ravel()
dKe = (1.0-epsk)*Ke  # stiffness variation of a topological change

# Elemental Matrix Factorizations
D,V = np.linalg.eigh(dKe)
mask = abs(D) > small
D = D[mask]
V = V[:,mask]
H = V*np.sqrt(D)
D,V = np.linalg.eigh(dKe[:,[2,3,4,5,6,7]][[2,3,4,5,6,7],:])
mask = abs(D) > small
D = D[mask]
V = V[:,mask]
H_01 = V*np.sqrt(D)
D,V = np.linalg.eigh(dKe[:,[0,1,2,3,4,5]][[0,1,2,3,4,5],:])
mask = abs(D) > small
D = D[mask]
V = V[:,mask]
H_67 = V*np.sqrt(D)
D,V = np.linalg.eigh(dKe[:,[2,3,4,5]][[2,3,4,5],:])
H_0167 = V*np.sqrt(D)

# check directories
if not os.path.exists('../input'):
    os.mkdir('../input')
if not os.path.exists('./output'):
    os.mkdir('./output')
if not os.path.exists('./output/run_{:06d}_{:06d}'.format(fid_ini,fid_lim-1)):
    os.mkdir('./output/run_{:06d}_{:06d}'.format(fid_ini,fid_lim-1))

# check input
if not os.path.exists('../input/inp_000000.pckl'):
    Ny = np.uint32(32)          # number of elements in y-axis
    bc_pos = np.float32(0.0)    # center of the restricted area
    bc_rad = np.float32(0.5)    # half-length (radius) of the restricted area
    ld_pos = np.float32(0.0)    # center of the loaded area
    ld_rad = np.float32(0.125)  # half-length (radius) of the loaded area
    finp = open('../input/inp_000000.pckl','wb')
    pickle.dump([Ny,bc_pos,bc_rad,ld_pos,ld_rad],finp)
    finp.close()

# open log files
if not os.path.exists('./output/run_{:06d}_{:06d}/logs'.format(fid_ini,fid_lim-1)):
    os.mkdir('./output/run_{:06d}_{:06d}/logs'.format(fid_ini,fid_lim-1))
iolog = open('./output/run_{:06d}_{:06d}/logs/io_log.txt'.format(fid_ini,fid_lim-1),'a')
tlog = open('./output/run_{:06d}_{:06d}/logs/time_log.txt'.format(fid_ini,fid_lim-1),'a')
iolog.truncate(0)
tlog.truncate(0)

iolog.write('DISCRETE STRUCTURAL OPTIMIZATION (IO LOG)\n')    # write in IO log
iolog.write('=====================================================================================================\n')
iolog.write('= OUTPUT :                input file id :              fid.npy                                      =\n')
iolog.write('= ------ :                   input data :              inp.npy                                      =\n')
iolog.write('= ------ :           optimized topology :          top_opt.npy                                      =\n')
iolog.write('= ------ : optimized objective function :          obj_opt.npy                                      =\n')
iolog.write('= ------ : pointer input > optimization :          ptr2opt.npy                                      =\n')
iolog.write('= ------ : pointer optimization > input :          ptr2inp.npy                                      =\n')
iolog.write('= ------ :             topology vectors :              top.npy                                      =\n')
iolog.write('= ------ :        displacements vectors :              dis.npy                                      =\n')
iolog.write('= ------ :    CGS-0 sensitivity vectors :            sen_0.npy                                      =\n')
iolog.write('= ------ :    CGS-1 sensitivity vectors :            sen_1.npy                                      =\n')
iolog.write('= ------ :    CGS-2 sensitivity vectors :            sen_2.npy                                      =\n')
iolog.write('= ------ :       WS sensitivity vectors :            sen_w.npy                                      =\n')
iolog.write('= ------ :                 volume array :              vol.npy                                      =\n')
iolog.write('= ------ :     objective function array :              obj.npy                                      =\n')
iolog.write('= ------ :                   time array :              tim.npy                                      =\n')
iolog.write('=====================================================================================================\n')
iolog.write('       INPUT || ELEM Y :  BC POS : BC RAD :  LD POS : LD RAD ||             BEGIN :               END\n')
tlog.write('DISCRETE STRUCTURAL OPTIMIZATION (TIME LOG)\n')   # write in time log
tlog.write('=======================================================================================================\n') 
tlog.write('       INPUT ||    FILES :     MESH :   B-COND : ASSEMBLY :    PRE-S :   SOLVER :   POST-S ||----------\n')
tlog.write('-------------||            (  IT x ):   M-SENS : M-UPDATE :  M-PRE-S : M-SOLVER : M-POST-S ||     TOTAL\n')

file = 0  # file counter
fid = fid_ini
while (fid < fid_lim) and (os.path.exists('../input/inp_{:06d}.pckl'.format(fid))):
    if not os.path.exists('./output/run_{:06d}_{:06d}/file_{:05d}'.format(fid_ini,fid_lim-1,file)):
        os.mkdir('./output/run_{:06d}_{:06d}/file_{:05d}'.format(fid_ini,fid_lim-1,file))
    
    list_fid     = []
    list_inp     = []
    list_top_opt = []
    list_obj_opt = []
    list_ptr2opt = []
    list_ptr2inp = []
    list_top     = []
    list_dis     = []
    list_sen_0   = []
    list_sen_1   = []
    list_sen_2   = []
    list_sen_w   = []
    list_obj     = []
    list_vol     = []
    list_tim     = []
    
    ptr = 0  # pointer to input
    for counter in range(noptf):
        if (fid >= fid_lim) or (not os.path.exists('../input/inp_{:06d}.pckl'.format(fid))):
            break

        print('running : {:06d} : setup'.format(fid))
        inp_file = 'inp_{:06d}.pckl'.format(fid)
        iolog.write('> ' + inp_file[:-5] + ' ||')
        tlog.write('> ' + inp_file[:-5] + ' ||')
        
        #%% Read files
        t0 = time()
        
        # read input file
        finp = open('../input/'+inp_file,'rb')
        Ny,bc_pos,bc_rad,ld_pos,ld_rad = pickle.load(finp)
        Ny = int(Ny)
        bc_pos = float(bc_pos)
        bc_rad = float(bc_rad)
        ld_pos = float(ld_pos)
        ld_rad = float(ld_rad)
        finp.close()
        list_fid += [fid]
        list_inp += [[bc_pos,bc_rad,ld_pos,ld_rad]]
        
        # write in log
        iolog.write(' {:6d} :'.format(Ny))
        iolog.write(' {:7.4f} :'.format(bc_pos))
        iolog.write(' {:6.4f} :'.format(bc_rad))
        iolog.write(' {:7.4f} :'.format(ld_pos))
        iolog.write(' {:6.4f} ||'.format(ld_rad))
        iolog.write(datetime.now().strftime(' %y/%m/%d-%H:%M:%S :'))
    
        # input properties
        Nx = 2*Ny      # number of elements in x-axis
        N = Nx*Ny      # total number of elements
        esize = Ly/Ny  # element size
        
        x = np.ones(N,dtype=bool)  # set initial topology
            
        # write in log
        time_array = np.zeros(14)  # initialize time array
        t1 = time()    
        time_array[0] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[0]))
    
        #%% Generate Mesh
        t0 = time()
        ### numbering rule
        ### 2_____5_____8_____11
        ### | (1) | (3) | (5) |
        ### 1_____4_____7_____10
        ### | (0) | (2) | (4) |
        ### 0_____3_____6_____9
        
        # coordinates matrix
        xcoor = (Ny+1)*[list(range(Nx+1))]
        xcoor = np.ravel(xcoor,'F')
        ycoor = (Nx+1)*[list(range(Ny+1))]
        ycoor = np.ravel(ycoor,'C')
        coor = esize*np.array([xcoor,ycoor]).T
        coor[:,1] = coor[:,1] - 0.5*Ly
        
        # incidence matrix
        N = Nx*Ny
        G = 2*(Nx+1)*(Ny+1)
        inci = np.ndarray([N,4],dtype=int)
        elem_ids = np.arange(N)
        inci[:,0] = elem_ids + elem_ids//Ny
        inci[:,1] = inci[:,0] + Ny + 1
        inci[:,2] = inci[:,0] + Ny + 2
        inci[:,3] = inci[:,0] + 1
        
        # write in log    
        t1 = time()
        time_array[1] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[1]))
        
        #%% Boundary Conditions
        t0 = time()
        
        # free DOFs
        bc_ycoor = coor[:Ny+1,1]
        bc_mask = abs(bc_ycoor - bc_pos*Ly) < bc_rad*Ly + small
        if sum(bc_mask) < 2:
            print('insufficient constraint')
            iolog.close()
            tlog.close()
            sys.exit()
        bc_ids = np.arange(0,Ny+1)
        bc_ids = bc_ids[bc_mask]
        bc_lim = np.array([bc_ids[0],bc_ids[-1]],dtype="int64")
        bc = np.concatenate((2*bc_ids,2*bc_ids+1))
        freeDofs = np.ones(G,dtype=bool)
        freeDofs[bc] = False
        sys_size = sum(freeDofs)
        
        # load vector
        fg = np.zeros(G)
        ld_ycoor = coor[Nx*(Ny+1):,1]
        ld_mask = abs(ld_ycoor - ld_pos*Ly) < ld_rad*Ly + small
        ld_mask_ele = ld_mask[1:] | ld_mask[:-1]
        ld_ele = np.arange((Nx-1)*Ny,Nx*Ny)
        ld_ele = ld_ele[ld_mask_ele]
        ld_lim = np.array([ld_ele[0],ld_ele[-1]],dtype="int64")
        ld_num = sum(ld_mask)
        ld_ids = np.arange(Nx*(Ny+1),(Nx+1)*(Ny+1))
        ld_ids = ld_ids[ld_mask]
        if ld_num == 0:
            pass
        elif ld_num == 1:
            fg[2*ld_ids+1] = -1.0
        else:
            ld_val = -1.0/(ld_num-1)
            fg[2*ld_ids[1:-1]+1] = ld_val    
            fg[2*ld_ids[[0,-1]]+1] = 0.5*ld_val
        fr = fg[freeDofs]
        
        # write in log    
        t1 = time()
        time_array[2] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[2]))
        
        #%% Matrix Assembly
        t0 = time()
        
        # COO data
        pen = np.ones(N)
        pen[~x] = epsk
        pen = pen.repeat(64)
        data = pen*np.tile(Kevec,N)
        
        # COO indices
        dof0 = 2*inci[:,0]
        dof1 = dof0 + 1
        dof2 = 2*inci[:,1]
        dof3 = dof2 + 1
        dof4 = 2*inci[:,2]
        dof5 = dof4 + 1
        dof6 = 2*inci[:,3]
        dof7 = dof6 + 1
        eledofs = np.array([dof0,dof1,dof2,dof3,dof4,dof5,dof6,dof7])
        row = eledofs.repeat(8,axis=0).ravel('F')
        col = eledofs.T.repeat(8,axis=0).ravel('C')
        
        # stiffness matrix
        Kg_coo = coo_matrix((data,(row,col)),shape=(G,G))
        Kg_csc = Kg_coo.tocsc()
        Kr = Kg_csc[freeDofs,:][:,freeDofs]
        
        # write in log    
        t1 = time()
        time_array[3] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[3]))
        
        #%% Pre-Solver
        t0 = time()
        
        # initialize displacements vector
        ug  = np.zeros(G)
        
        # analyze sparse matrix
        factor = analyze(Kr)
        
        # write in log    
        t1 = time()
        time_array[4] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[4]))
        
        #%% Solve System
        t0 = time()
        
        # call solver
        factor.cholesky_inplace(Kr)
        ug[freeDofs] = factor(fr)
        
        # write in log    
        t1 = time()
        time_array[5] = t1 - t0
        tlog.write(' {:6.3f} s :'.format(time_array[5]))
        
        #%% Post-Solver
        t0 = time()
        
        # optimization setup
        alpha_0 = np.zeros(N)        # CGS-0
        alpha_1 = np.zeros(N)        # CGS-1
        alpha_2 = np.zeros(N)        # CGS-2
        alpha_r = np.zeros(N)        # raw sensitivity vector
        alpha_f = np.zeros(N)        # filtered sensitivity vector
        alpha_m = np.zeros(N)        # filtered sensitivity vector with momentum
        fe = np.zeros((sys_size,5))  # auxiliary matrix for WS approach
        Vt = int(N/2)                # target volume
        dVmax = max([1,int(VV*N)])   # maximal volume change
        dXmax = max([2,TV*N])        # maximal topological change
        vol = sum(x)                 # volume
        
        list_vol = list_vol + [vol/N]  # volume progression
        obj = np.dot(ug,fg)            # objective function
        list_obj = list_obj + [obj]    # objective function progression
        obj_opt = np.infty
        keep_going = True
        waiting = 0
        it = 0
        size_list = len(list_ptr2inp)
        list_ptr2opt += [size_list]
        
        # write in log
        t1 = time()
        time_array[6] = t1 - t0
        tlog.write(' {:6.3f} s ||----------\n'.format(time_array[6]))
        
        #%% Optimization (BESO)
        while keep_going:
            it = it + 1
            print('running : {:06d} :  {:4d}'.format(fid,it))
            
            # sensitivity analysis
            t0 = time()
            ur = ug[freeDofs]
            str_cgs(alpha_0, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=0)
            str_cgs(alpha_1, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=1)
            str_cgs(alpha_2, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=2)
            for e in range(N):
                n0 = e + (e // Ny)
                n1 = n0 + Ny + 1
                n2 = n1 + 1
                n3 = n0 + 1
                nodes = np.array([n0,n1,n2,n3])
                freeNodes = (nodes < bc_lim[0]) | (nodes > bc_lim[1])
                nodes = nodes[freeNodes]
                mask = nodes > bc_lim[1]
                nodes[mask] = nodes[mask] - (bc_lim[1]-bc_lim[0]+1)
                gv = np.repeat(2*nodes,2)
                gv[1::2] = gv[1::2] + 1
                rank = 5
                if all(freeNodes):
                    He = H
                elif (not freeNodes[0]) and (freeNodes[-1]):
                    He = H_01
                elif (freeNodes[0]) and (not freeNodes[-1]):
                    He = H_67
                else:
                    He = H_0167
                    rank = 4
                Ai = np.zeros((rank,rank))
                fe[gv,:rank] = He
                aux = factor.solve_L(factor.apply_P(fe[:,:rank]),use_LDLt_decomposition=False)
                fe[gv,:rank] = 0.0
                Ai = aux.T @ aux
                vi = He.T @ ur[gv]
                Ii = np.identity(rank)
                if x[e]:
                    alpha_r[e] = -vi @ np.linalg.inv(Ii-Ai) @ vi
                else:
                    alpha_r[e] = -vi @ np.linalg.inv(Ii+Ai) @ vi

            list_ptr2inp += [ptr]
            list_top     += [x.copy()]
            list_dis     += [ug.copy()]
            list_sen_0   += [alpha_0.copy()]
            list_sen_1   += [alpha_1.copy()]
            list_sen_2   += [alpha_2.copy()]
            list_sen_w   += [alpha_r.copy()]
            
            str_filter(alpha_r, alpha_f, rmax, esize, Nx, Ny, load_lim=ld_lim)
            alpha_m[ld_ele] = 0.0
            alpha_m = momentum*alpha_m + (1.0-momentum)*(alpha_f/max(abs(alpha_f)))
            alpha_m = alpha_m/max(abs(alpha_m))
            alpha_m[ld_ele] = -np.infty
            t1 = time()
            time_array[7] = time_array[7] + (t1-t0)
    
            # update topology
            t0 = time()
            solid = np.argwhere(x)[:,0]
            void = np.argwhere(~x)[:,0]   
            sorted_solid = np.argsort(alpha_m[solid])
            sorted_void = np.argsort(alpha_m[void])
            # changing volume
            count = 0
            for i in range(min([vol-Vt,dVmax])):
                es = solid[sorted_solid[-1-i]]
                x[es] = False
                Kg_coo.data[64*es:64*(es+1)] = epsk*Kevec
                # update Cholesky factor (faster for coarse meshes)
                n0 = es + (es // Ny)
                n1 = n0 + Ny + 1
                n2 = n1 + 1
                n3 = n0 + 1
                nodes = np.array([n0,n1,n2,n3])
                freeNodes = (nodes < bc_lim[0]) | (nodes > bc_lim[1])
                nodes = nodes[freeNodes]
                mask = nodes > bc_lim[1]
                nodes[mask] = nodes[mask] - (bc_lim[1]-bc_lim[0]+1)
                gv = np.repeat(2*nodes,2)
                gv[1::2] = gv[1::2] + 1
                lgv = len(gv)
                rank = 5
                if all(freeNodes):
                    hdata = H.ravel()
                elif (not freeNodes[0]) and (freeNodes[-1]):
                    hdata = H_01.ravel()
                elif (freeNodes[0]) and (not freeNodes[-1]):
                    hdata = H_67.ravel()
                else:
                    hdata = H_0167.ravel()
                    rank = 4
                hrow  = np.repeat(gv,rank)
                hcol  = np.tile(np.arange(rank),lgv)
                H_coo = coo_matrix((hdata,(hrow,hcol)),shape=(sys_size,rank))
                H_csc = H_coo.tocsc()    
                factor.update_inplace(H_csc, subtract=True)
                count = count + 1
            # constant volume
            for i in range(min([len(sorted_void),int((dXmax-count)/2)])):
                es = solid[sorted_solid[-1-i-count]]
                ev = void[sorted_void[i]]
                if alpha_m[es] < alpha_m[ev]:
                    break
                x[es] = False
                x[ev] = True
                Kg_coo.data[64*es:64*(es+1)] = epsk*Kevec
                Kg_coo.data[64*ev:64*(ev+1)] = Kevec
                # update Cholesky factor (faster for coarse meshes)
                n0 = es + (es // Ny)
                n1 = n0 + Ny + 1
                n2 = n1 + 1
                n3 = n0 + 1
                nodes = np.array([n0,n1,n2,n3])
                freeNodes = (nodes < bc_lim[0]) | (nodes > bc_lim[1])
                nodes = nodes[freeNodes]
                mask = nodes > bc_lim[1]
                nodes[mask] = nodes[mask] - (bc_lim[1]-bc_lim[0]+1)
                gv = np.repeat(2*nodes,2)
                gv[1::2] = gv[1::2] + 1
                lgv = len(gv)
                rank = 5
                if all(freeNodes):
                    hdata = H.ravel()
                elif (not freeNodes[0]) and (freeNodes[-1]):
                    hdata = H_01.ravel()
                elif (freeNodes[0]) and (not freeNodes[-1]):
                    hdata = H_67.ravel()
                else:
                    hdata = H_0167.ravel()
                    rank = 4
                hrow  = np.repeat(gv,rank)
                hcol  = np.tile(np.arange(rank),lgv)
                H_coo = coo_matrix((hdata,(hrow,hcol)),shape=(sys_size,rank))
                H_csc = H_coo.tocsc()    
                factor.update_inplace(H_csc, subtract=True)
                n0 = ev + (ev // Ny )
                n1 = n0 + Ny + 1
                n2 = n1 + 1
                n3 = n0 + 1
                nodes = np.array([n0,n1,n2,n3])
                freeNodes = (nodes < bc_lim[0]) | (nodes > bc_lim[1])
                nodes = nodes[freeNodes]
                mask = nodes > bc_lim[1]
                nodes[mask] = nodes[mask] - (bc_lim[1]-bc_lim[0]+1)
                gv = np.repeat(2*nodes,2)
                gv[1::2] = gv[1::2] + 1
                lgv = len(gv)
                rank = 5
                if all(freeNodes):
                    hdata = H.ravel()
                elif (not freeNodes[0]) and (freeNodes[-1]):
                    hdata = H_01.ravel()
                elif (freeNodes[0]) and (not freeNodes[-1]):
                    hdata = H_67.ravel()
                else:
                    hdata = H_0167.ravel()
                    rank = 4
                hrow  = np.repeat(gv,rank)
                hcol  = np.tile(np.arange(rank),lgv)
                H_coo = coo_matrix((hdata,(hrow,hcol)),shape=(sys_size,rank))
                H_csc = H_coo.tocsc()     
                factor.update_inplace(H_csc, subtract=False)
            t1 = time()
            time_array[8] = time_array[8] + (t1-t0)
            
            # assembly
            t0 = time()
            Kg_csc = Kg_coo.tocsc()
            t1 = time()
            time_array[9] = time_array[9] + (t1-t0)
            
            # solver
            t0 = time()
            ug[freeDofs] = factor(fr)
            t1 = time()
            time_array[10] = time_array[10] + (t1-t0)
            
            # post-solver
            t0 = time()
            vol = sum(x)
            list_vol = list_vol + [vol/N]
            obj = np.dot(ug,fg)
            list_obj = list_obj + [obj]
            if vol == Vt:
                # update optimized topology
                if obj < (1.0-small) * obj_opt:
                    x_opt = x.copy()
                    obj_opt = obj
                    waiting = 0
                else:
                    waiting = waiting + 1
                    # check convergence
                    if waiting == patience:
                        keep_going = False
            t1 = time()
            time_array[11] = time_array[11] + (t1-t0)
        
        #%% Post-Optimization
        # sensitivity analysis
        ur = ug[freeDofs]
        str_cgs(alpha_0, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=0)
        str_cgs(alpha_1, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=1)
        str_cgs(alpha_2, x, Kg_csc, bc_lim, dKe, ug, Nx, Ny, steps=2)
        for e in range(N):
            n0 = e + (e // Ny)
            n1 = n0 + Ny + 1
            n2 = n1 + 1
            n3 = n0 + 1
            nodes = np.array([n0,n1,n2,n3])
            freeNodes = (nodes < bc_lim[0]) | (nodes > bc_lim[1])
            nodes = nodes[freeNodes]
            mask = nodes > bc_lim[1]
            nodes[mask] = nodes[mask] - (bc_lim[1]-bc_lim[0]+1)
            gv = np.repeat(2*nodes,2)
            gv[1::2] = gv[1::2] + 1
            rank = 5
            if all(freeNodes):
                He = H
            elif (not freeNodes[0]) and (freeNodes[-1]):
                He = H_01
            elif (freeNodes[0]) and (not freeNodes[-1]):
                He = H_67
            else:
                He = H_0167
                rank = 4
            Ai = np.zeros((rank,rank))
            fe[gv,:rank] = He
            aux = factor.solve_L(factor.apply_P(fe[:,:rank]),use_LDLt_decomposition=False)
            fe[gv,:rank] = 0.0
            Ai = aux.T @ aux
            vi = He.T @ ur[gv]
            Ii = np.identity(rank)
            if x[e]:
                alpha_r[e] = -vi @ np.linalg.inv(Ii-Ai) @ vi
            else:
                alpha_r[e] = -vi @ np.linalg.inv(Ii+Ai) @ vi
        
        # write in log
        tlog.write('-------------||            ({:4d} x ):'.format(it))
        time_array[12] = sum(time_array[:12])
        time_array[7:12] = time_array[7:12]/it
        time_array[13] = (1+small)*it
        tlog.write(' {:6.3f} s : {:6.3f} s : {:6.3f} s : {:6.3f} s : {:6.3f} s ||'.format(
            time_array[7],time_array[8],time_array[9],time_array[10],time_array[11]))
        tlog.write(' {:7.1f} s\n'.format(time_array[12]))
        iolog.write(datetime.now().strftime(' %y/%m/%d-%H:%M:%S\n'))
        
        list_top_opt += [x_opt.copy()]
        list_obj_opt += [obj_opt]
        list_ptr2inp += [ptr]
        list_top     += [x.copy()]
        list_dis     += [ug.copy()]
        list_sen_0   += [alpha_0.copy()]
        list_sen_1   += [alpha_1.copy()]
        list_sen_2   += [alpha_2.copy()]
        list_sen_w   += [alpha_r.copy()]
        list_tim     += [time_array.copy()]
        
        # update pointer
        ptr = ptr + 1
        
        # prepare to open next input file
        fid = fid + 1
    
    #%% Write files
    size_list = len(list_ptr2inp)
    list_ptr2opt += [size_list]

    # save files
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/fid.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_fid,dtype=np.uint32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/inp.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_inp,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/top_opt.npy'.format(
        fid_ini,fid_lim-1,file),np.packbits(np.array(list_top_opt),axis=1))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/obj_opt.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_obj_opt,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/ptr2opt.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_ptr2opt,dtype=np.uint32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/ptr2inp.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_ptr2inp,dtype=np.uint32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/top.npy'.format(
        fid_ini,fid_lim-1,file),np.packbits(np.array(list_top),axis=1))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/dis.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_dis,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/sen_0.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_sen_0,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/sen_1.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_sen_1,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/sen_2.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_sen_2,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/sen_w.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_sen_w,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/obj.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_obj,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/vol.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_vol,dtype=np.float32))
    np.save('./output/run_{:06d}_{:06d}/file_{:05d}/tim.npy'.format(
        fid_ini,fid_lim-1,file),np.array(list_tim,dtype=np.float32))
    
    del list_fid, list_inp, list_top_opt, list_obj_opt, list_ptr2opt, list_ptr2inp, list_top, list_dis
    del list_sen_0, list_sen_1, list_sen_2, list_sen_w, list_obj, list_vol, list_tim
    gc.collect()
    
    # prepare to write next output file
    file = file + 1

#%% close log files
iolog.close()
tlog.close()
print('done!')
