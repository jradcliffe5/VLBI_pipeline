#!/bin/bash
#PBS -N selfcal
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=4:00:00
#PBS -o selfcal.stdout 
#PBS -e selfcal.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

## Inputs
epoch="eg078g"
cwd="/home/jradcliffe/lustre/EG078G/calibration"
phasecal="J1241+602,J1234+619"
caltype=('p' 'p' 'p' 'ap' 'ap' 'p' 'p')
solint=("inf" "inf" "inf" "inf" "inf" "inf" "30s")
combine=("spw" "" "" "spw" "spw" "" "spw")
applytype="calflag"
pad_ant="2"

cd $cwd

/mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/mpicasa --map-by node -hostfile $PBS_NODEFILE /mnt/lustre/users/jradcliffe/CASA_distros/casa-pipeline-release-5.6.2-3.el7/bin/casa --nologger --log2term --nogui -c run_selfcal.py $epoch $cwd $phasecal 1 $(IFS=$','; echo "${caltype[*]}") $(IFS=$','; echo "${solint[*]}") $(IFS=$','; echo "${combine[*]}") $applytype $pad_ant
