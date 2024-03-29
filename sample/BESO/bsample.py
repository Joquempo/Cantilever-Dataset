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

import os, sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.collections as clct

file_ini    = 0     # initial file index |from file 0
file_lim    = 4     # file index limit   |up to file 9264
fig_top_opt = True  # optimized topology
fig_top_sen = True  # topology vectors and sensitivity vectors
fig_dis     = True  # displacements vectors
fig_obj_vol = True  # objective function and volume

# fixed properties
Ly = 1.0       # cantilever height
small = 1e-14  # small value to compare float numbers
Ny = 32        # number of elements in y-axis
Nx = 2*Ny      # number of elements in x-axis
N = Nx*Ny      # total number of elements
esize = Ly/Ny  # element size

# check directories
rpath = '../../dataset/BESO/'
if not os.path.exists(rpath):
    print('missing BESO dataset')
    sys.exit()
if not os.path.exists('./top_opt'):
    os.mkdir('./top_opt')
if not os.path.exists('./top_sen'):
    os.mkdir('./top_sen')
if not os.path.exists('./dis'):
    os.mkdir('./dis')
if not os.path.exists('./obj_vol'):
    os.mkdir('./obj_vol')

file = file_ini
while (file < file_lim) and (os.path.exists(rpath + 'f{:04d}'.format(file))):
    #%% Read files
    print('> reading files of f{:04d}'.format(file))

    # input files id, input data and pointers to optimization
    if not os.path.exists(rpath + 'f{:04d}/fid.npy'.format(file)):
        print('missing : f{:04d}/fid.npy'.format(file))
        sys.exit()
    list_fid = np.load(rpath + 'f{:04d}/fid.npy'.format(file))
    if not os.path.exists(rpath + 'f{:04d}/inp.npy'.format(file)):
        print('missing : f{:04d}/inp.npy'.format(file))
        sys.exit()
    list_inp = np.load(rpath + 'f{:04d}/inp.npy'.format(file))
    if not os.path.exists(rpath + 'f{:04d}/ptr2opt.npy'.format(file)):
        print('missing : f{:04d}/ptr2opt.npy'.format(file))
        sys.exit()
    list_ptr2opt = np.load(rpath + 'f{:04d}/ptr2opt.npy'.format(file))
    
    # optimized topology
    if fig_top_opt:
        if not os.path.exists(rpath + 'f{:04d}/top_opt.npy'.format(file)):
            print('missing : f{:04d}/top_opt.npy'.format(file))
            sys.exit()
        list_top_opt = np.load(rpath + 'f{:04d}/top_opt.npy'.format(file))
    
    # topology vectors
    if fig_top_sen or fig_dis:
        if not os.path.exists(rpath + 'f{:04d}/top.npy'.format(file)):
            print('missing : f{:04d}/top.npy'.format(file))
            sys.exit()
        list_top = np.load(rpath + 'f{:04d}/top.npy'.format(file))
        
    # sensitivity vectors
    if fig_top_sen:
        if not os.path.exists(rpath + 'f{:04d}/sen_0.npy'.format(file)):
            print('missing : f{:04d}/sen_0.npy'.format(file))
            sys.exit()
        list_sen_0 = np.load(rpath + 'f{:04d}/sen_0.npy'.format(file))
        if not os.path.exists(rpath + 'f{:04d}/sen_1.npy'.format(file)):
            print('missing : f{:04d}/sen_1.npy'.format(file))
            sys.exit()
        list_sen_1 = np.load(rpath + 'f{:04d}/sen_1.npy'.format(file))
        if not os.path.exists(rpath + 'f{:04d}/sen_2.npy'.format(file)):
            print('missing : f{:04d}/sen_2.npy'.format(file))
            sys.exit()
        list_sen_2 = np.load(rpath + 'f{:04d}/sen_2.npy'.format(file))
        if not os.path.exists(rpath + 'f{:04d}/sen_w.npy'.format(file)):
            print('missing : f{:04d}/sen_w.npy'.format(file))
            sys.exit()
        list_sen_w = np.load(rpath + 'f{:04d}/sen_w.npy'.format(file))
    
    # displacements vectors
    if fig_dis:
        if not os.path.exists(rpath + 'f{:04d}/dis.npy'.format(file)):
            print('missing : f{:04d}/dis.npy'.format(file))
            sys.exit()
        list_dis = np.load(rpath + 'f{:04d}/dis.npy'.format(file))
        
    # objective function and volume
    if fig_obj_vol:
        if not os.path.exists(rpath + 'f{:04d}/obj.npy'.format(file)):
            print('missing : f{:04d}/obj.npy'.format(file))
            sys.exit()
        list_obj = np.load(rpath + 'f{:04d}/obj.npy'.format(file))
        if not os.path.exists(rpath + 'f{:04d}/vol.npy'.format(file)):
            print('missing : f{:04d}/vol.npy'.format(file))
            sys.exit()
        list_vol = np.load(rpath + 'f{:04d}/vol.npy'.format(file))
    
    #%% Generate figures
    print(': generating figures')
    
    # optimized topology
    if fig_top_opt:
        print(': : optimized topology...')
        for k in range(len(list_fid)):
            # boundary conditions
            fid = list_fid[k]
            inp = list_inp[k]
            ycoor = esize*np.array(list(range(Ny+1)))-0.5*Ly
            mask = (ycoor > inp[0]-inp[1]-small) & (ycoor < inp[0]+inp[1]+small)
            c0 = np.zeros((32,1))
            c0[mask[1:]]  += 0.25 
            c0[mask[:-1]] += 0.25
            mask = (ycoor > inp[2]-inp[3]-small) & (ycoor < inp[2]+inp[3]+small)
            c1 = np.zeros((32,1))
            c1[mask[1:]]  += 0.25 
            c1[mask[:-1]] += 0.25
            # figure
            plt.figure(num=0).clear()
            fig,ax = plt.subplots(num=0)
            x = list_top_opt[k]
            x = np.unpackbits(x,axis=None).astype(float)
            xmat = np.reshape(x,(Ny,Nx),order='F')
            xmat = np.concatenate((c0,xmat,c1),axis=1)
            ax.imshow(xmat,cmap='gray_r',vmin=0,vmax=1.0,origin='lower')
            ax.axis('off')
            fig.set_size_inches(8, 4)
            plt.savefig('./top_opt/f{:06d}.png'.format(fid),bbox_inches='tight',pad_inches=0.05,dpi=100)
    
    # topology vectors and sensitivity vectors
    if fig_top_sen:
        print(': : topology vectors and sensitivity vectors...')
        for k in range(len(list_fid)):
            # boundary conditions
            fid = list_fid[k]
            inp = list_inp[k]
            ycoor = esize*np.array(list(range(Ny+1)))-0.5*Ly
            mask = (ycoor > inp[0]-inp[1]-small) & (ycoor < inp[0]+inp[1]+small)
            c0 = np.zeros((32,1))
            c0[mask[1:]]  += 0.25 
            c0[mask[:-1]] += 0.25
            mask = (ycoor > inp[2]-inp[3]-small) & (ycoor < inp[2]+inp[3]+small)
            c1 = np.zeros((32,1))
            c1[mask[1:]]  += 0.25 
            c1[mask[:-1]] += 0.25
            j = 0
            for kk in range(list_ptr2opt[k],list_ptr2opt[k+1]):
                # figure
                plt.figure(num=0).clear()
                fig,ax = plt.subplots(nrows=3,ncols=2,num=0)
                x = list_top[kk]
                x = np.unpackbits(x,axis=None).astype(float)
                xmat = np.reshape(x,(Ny,Nx),order='F')
                xmat = np.concatenate((c0,xmat,c1),axis=1)
                ax[0,0].imshow(xmat,cmap='gray_r',vmin=0,vmax=1.0,origin='lower')
                ax[0,0].axis('off')
                alpha_0 = list_sen_0[kk].astype(float)
                alpha_1 = list_sen_1[kk].astype(float)
                alpha_2 = list_sen_2[kk].astype(float)
                alpha_w = list_sen_w[kk].astype(float)
                mval = max([max(abs(alpha_0)),max(abs(alpha_1)),max(abs(alpha_2)),max(abs(alpha_w))])
                alpha_0 = alpha_0/mval
                alpha_1 = alpha_1/mval
                alpha_2 = alpha_2/mval
                alpha_w = alpha_w/mval
                amat = np.reshape(np.log(-alpha_0+1e-6),(Ny,Nx),order='F')
                ax[0,1].imshow(amat,cmap='jet',vmin=np.log(1e-6),vmax=np.log(1.0+1e-6),origin='lower')
                ax[0,1].axis('off')
                amat = np.reshape(np.log(-alpha_1+1e-6),(Ny,Nx),order='F')
                ax[1,1].imshow(amat,cmap='jet',vmin=np.log(1e-6),vmax=np.log(1.0+1e-6),origin='lower')
                ax[1,1].axis('off')
                amat = np.reshape(np.log(-alpha_2+1e-6),(Ny,Nx),order='F')
                ax[2,1].imshow(amat,cmap='jet',vmin=np.log(1e-6),vmax=np.log(1.0+1e-6),origin='lower')
                ax[2,1].axis('off')
                amat = np.reshape(np.log(-alpha_w+1e-6),(Ny,Nx),order='F')
                ax[2,0].imshow(amat,cmap='jet',vmin=np.log(1e-6),vmax=np.log(1.0+1e-6),origin='lower')
                ax[2,0].axis('off')
                ax[1,0].axis('off')
                fig.set_size_inches(12, 9)
                plt.savefig('./top_sen/f{:06d}_{:03d}.png'.format(fid,j),bbox_inches='tight',pad_inches=0.05,dpi=100)
                j += 1
        
    # displacements vectors
    if fig_dis:
        print(': : displacements vectors...')
        # coordinates matrix
        xcoor = (Ny+1)*[list(range(Nx+2+1))]
        xcoor = np.ravel(xcoor,'F')
        ycoor = (Nx+2+1)*[list(range(Ny+1))]
        ycoor = np.ravel(ycoor,'C')
        coor = esize*np.array([xcoor,ycoor]).T
        coor[:,1] = coor[:,1] - 0.5*Ly
        # incidence matrix
        N = (Nx+2)*Ny
        inci = np.ndarray([N,4],dtype=int)
        elem_ids = np.arange(N)
        inci[:,0] = elem_ids + elem_ids//Ny
        inci[:,1] = inci[:,0] + Ny + 1
        inci[:,2] = inci[:,0] + Ny + 2
        inci[:,3] = inci[:,0] + 1
        for k in range(len(list_fid)):
            # boundary conditions
            fid = list_fid[k]
            inp = list_inp[k]
            ycoor = esize*np.array(list(range(Ny+1)))-0.5*Ly
            mask = (ycoor > inp[0]-inp[1]-small) & (ycoor < inp[0]+inp[1]+small)
            c0 = np.zeros(32)
            c0[mask[1:]]  += 0.25 
            c0[mask[:-1]] += 0.25
            mask = (ycoor > inp[2]-inp[3]-small) & (ycoor < inp[2]+inp[3]+small)
            c1 = np.zeros(32)
            c1[mask[1:]]  += 0.25 
            c1[mask[:-1]] += 0.25
            j = 0
            for kk in range(list_ptr2opt[k],list_ptr2opt[k+1]):
                # figure
                plt.figure(num=0).clear()
                fig,ax = plt.subplots(num=0)
                ug = list_dis[kk]
                if j == 0:
                    scale = 0.50*Ly/max(abs(ug))
                ug = np.concatenate((ug[:66],ug,ug[-66:]))
                umat = np.reshape(ug,coor.shape)
                coor_dis = coor + scale*umat
                if j == 0:
                    xmax = max(coor_dis[:,0])
                    xmin = min(coor_dis[:,0])
                    ymax = max(coor_dis[:,1])
                    ymin = min(coor_dis[:,1])
                    Dx = xmax-xmin
                    Dy = ymax-ymin
                polys = clct.PolyCollection(coor_dis[inci],cmap='gray_r',edgecolor=(0,0,0,0))
                x = list_top[kk]
                x = np.unpackbits(x,axis=None).astype(float)
                x = np.concatenate((c0,x,c1))
                polys.set_array(x)
                polys.set_clim(0.0,1.0)
                ax.add_collection(polys)
                ax.set_aspect('equal')
                ax.set_xlim([xmin-0.01*Dx,xmax+0.01*Dx])
                ax.set_ylim([ymin-0.05*Dy,ymax+0.01*Dy])
                ax.axis('off')
                fig.set_size_inches(8, 6)
                fig.savefig('./dis/f{:06d}_{:03d}.png'.format(fid,j),bbox_inches='tight',pad_inches=0,dpi=100)
                j += 1
                
    # objective function and volume
    if fig_obj_vol:
        print(': : objective function and volume...')
        for k in range(len(list_fid)):
            fid = list_fid[k]
            plt.figure(num=0).clear()
            fig,ax = plt.subplots(nrows=2,ncols=1,num=0)
            obj = list_obj[list_ptr2opt[k]:list_ptr2opt[k+1]]
            delta = max(obj) - min(obj)
            miny = min(obj)-0.02*delta
            maxy = max(obj)+0.02*delta
            ax[0].plot(obj,'ok-',linewidth=2)
            ax[0].axis([-0.75, len(obj)-0.25, miny, maxy])
            ax[0].set_ylabel('compliance [J]',fontsize=18)
            ax[0].grid()
            vol = list_vol[list_ptr2opt[k]:list_ptr2opt[k+1]]
            ax[1].plot(vol,'ok-',linewidth=2)
            ax[1].axis([-0.75, len(obj)-0.25, -0.05, 1.05])
            ax[1].set_ylabel('volume fraction',fontsize=18)
            ax[1].grid()
            ax[1].set_xlabel('iteration',fontsize=18)
            fig.set_size_inches(8, 9)
            fig.savefig('./obj_vol/f{:06d}.png'.format(fid),bbox_inches='tight',pad_inches=0.05,dpi=100)

    # prepare to read next file
    file = file + 1

plt.close(fig=0)
print('done!')
