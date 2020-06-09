#!/bin/bash
#PBS -N aprioriEVN
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=1:00:00
#PBS -o aprioriEVN.stdout 
#PBS -e aprioriEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
cwd="/Volumes/HD-LXU3/EG078G/calibration/CASA"
CASApath="/Applications/CASA-5.7.app/Contents/MacOS"
parallel="False"
cd $cwd

if [ "$parallel" == "True" ]; then
	$CASApath"/mpicasa" --map-by node -hostfile $PBS_NODEFILE $CASApath"/casa" --nologger --log2term --nogui -c "run_mpi_priorcal.py" $epoch $cwd $parallel
else
	$CASApath"/casa" --nologger --log2term --nogui -c "run_mpi_priorcal.py" $epoch $cwd $parallel
fi
