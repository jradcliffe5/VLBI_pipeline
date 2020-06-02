#!/bin/bash
#PBS -N importEVN
#PBS -q serial
#PBS -P ASTR1313
#PBS -l select=1:ncpus=4:mpiprocs=4:nodetype=haswell_reg
#PBS -l walltime=10:00:00
#PBS -o importEVN.stdout 
#PBS -e importEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com
#Run the application:

epoch=eg078g
cwd="/home/jradcliffe/lustre/EG078G/calibration"
cd $cwd

/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c run_imp_fitsidi.py $epoch $cwd 
