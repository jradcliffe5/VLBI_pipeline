#!/bin/bash
#PBS -N aprioriEVN
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=2:00:00
#PBS -o aprioriEVN.stdout 
#PBS -e aprioriEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
cwd="/home/jradcliffe/lustre/EG078G/calibration"
parallel="True"
cd $cwd

/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/mpicasa --map-by node -hostfile $PBS_NODEFILE /mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c "run_mpi_priorcal.py" $epoch $cwd $parallel
