#!/bin/bash
#PBS -N fringefitEVN
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=2:00:00
#PBS -o ffEVN.stdout 
#PBS -e ffEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
cwd="/Volumes/HD-LXU3/EG078G/calibration/CASA"
CASApath="/Applications/CASA-5.7.app/Contents/MacOS"
phasecal="J1241+602,J1234+619"
sbdcal="3C345"
casa_tclean="True"
ao_fields="0,1,157"
pad_ant=""

parallel="False"
do_sbd="True"
do_mbd="False"
cd $cwd

if [ "$parallel" == "True" ]; then
	if [ "$do_sbd" == "True" ]; then
		$CASApath"/mpicasa" --map-by node -hostfile $PBS_NODEFILE $CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part1.py $epoch $cwd $phasecal $sbdcal
	fi
	#module load chpc/singularity
	#singularity exec /mnt/lustre/users/jradcliffe/singularity_ims/kern5-dev.simg  aoflagger -strategy J1234_619.rfis -fields $ao_fields --column CORRECTED_DATA $cwd/$epoch".ms"
	if [ "$do_mbd" == "True" ]; then
		$CASApath"/mpicasa" --map-by node -hostfile $PBS_NODEFILE $CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean 1 1 $pad_ant

		for W_LOOP in 2 3
		do
			$CASApath"/mpicasa" --map-by node -hostfile $PBS_NODEFILE $CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean $W_LOOP 1 $pad_ant
		done
	fi
else
	if [ "$do_sbd" == "True" ]; then
		$CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part1.py $epoch $cwd $phasecal $sbdcal
	fi
	#module load chpc/singularity
	#singularity exec /mnt/lustre/users/jradcliffe/singularity_ims/kern5-dev.simg  aoflagger -strategy J1234_619.rfis -fields $ao_fields --column CORRECTED_DATA $cwd/$epoch".ms"
	if [ "$do_mbd" == "True" ]; then
		$CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean 1 1 $pad_ant

		for W_LOOP in 2 3
		do
			$CASApath"/casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean $W_LOOP 1 $pad_ant
		done
	fi
fi
