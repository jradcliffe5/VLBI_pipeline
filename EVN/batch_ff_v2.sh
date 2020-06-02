#!/bin/bash
#PBS -N fringefitEVN
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=7:00:00
#PBS -o ffEVN.stdout 
#PBS -e ffEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
cwd="/home/jradcliffe/lustre/EG078G/calibration"
parallel="True"
phasecal="J1241+602,J1234+619"
sbdcal="DA193,3C345"
casa_tclean="True"
ao_fields="0,1,157"
pad_ant="2"

cd $cwd
/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/mpicasa --map-by node -hostfile $PBS_NODEFILE /mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c fringe_fit_part1.py $epoch $cwd $phasecal $sbdcal

module load chpc/singularity
singularity exec /mnt/lustre/users/jradcliffe/singularity_ims/kern5-dev.simg  aoflagger -strategy J1234_619.rfis -fields $ao_fields --column CORRECTED_DATA $cwd/$epoch".ms"

#phasecal="J1011+0106"
/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/mpicasa --map-by node -hostfile $PBS_NODEFILE /mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean 1 1 $pad_ant

for W_LOOP in 2 3
do
	#rm -r ff_im_cycle_$W_LOOP"-0*"
	/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/mpicasa --map-by node -hostfile $PBS_NODEFILE /mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $cwd $phasecal $sbdcal $casa_tclean $W_LOOP 1 $pad_ant
done
