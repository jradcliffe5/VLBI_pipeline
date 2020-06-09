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
cwd="/Volumes/HD-LXU3/EG078G/calibration/CASA"
cd $cwd

source /Volumes/HD-LXU3/anaconda2/anaconda2/bin/activate aoflag
#module load chpc/singularity 
aoflagger -strategy $cwd"/J1234_619.rfis" -fields $fields $cwd"/"$epoch".ms"

