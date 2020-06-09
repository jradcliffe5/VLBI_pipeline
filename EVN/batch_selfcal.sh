#!/bin/bash
#PBS -N selfcal
#PBS -q normal
#PBS -P ASTR1313
#PBS -l select=2:ncpus=24:mpiprocs=24:nodetype=haswell_reg
#PBS -l walltime=1:00:00
#PBS -o selfcal.stdout 
#PBS -e selfcal.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

## Inputs
epoch="eg078g_dbbc_model"
cwd="/Volumes/HD-LXU3/EG078G/calibration/CASA"
CASApath="/Applications/CASA-5.7.app/Contents/MacOS"
parallel="False"
phasecal="J1241+602"
caltype=('p' 'p' 'p' 'ap' 'ap' 'p' 'p')
solint=("inf" "inf" "inf" "inf" "inf" "inf" "30s")
combine=("spw" "" "" "" "" "" "spw")
applytype="calflag"
pad_ant=""
caltype=('p' 'p' 'p')
solint=("inf" "inf" "inf")
combine=("spw" "" "")

cd $cwd

if [ "$parallel" == "True" ]; then
	$CASApath"/mpicasa" --map-by node -hostfile $PBS_NODEFILE $CASApath"/casa" --nologger --log2term --nogui -c run_selfcal.py $epoch $cwd $phasecal 1 $(IFS=$','; echo "${caltype[*]}") $(IFS=$','; echo "${solint[*]}") $(IFS=$','; echo "${combine[*]}") $applytype $pad_ant
else
	$CASApath"/casa" --nologger --log2term --nogui -c run_selfcal.py $epoch $cwd $phasecal 1 $(IFS=$','; echo "${caltype[*]}") $(IFS=$','; echo "${solint[*]}") $(IFS=$','; echo "${combine[*]}") $applytype $pad_ant
fi
