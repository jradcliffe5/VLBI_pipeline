#!/bin/bash
#PBS -N AOflagEVN
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=1:00:00
#PBS -o aoflagEVN.stdout 
#PBS -e aoflagEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
fields="0,1,157"
cwd="/home/jradcliffe/lustre/EG078G/calibration"
cd $cwd

module load chpc/singularity 
singularity exec /mnt/lustre/users/jradcliffe/singularity_ims/kern5-dev.simg aoflagger -strategy $cwd"/J1234_619.rfis" -fields $fields $cwd"/"$epoch".ms"

