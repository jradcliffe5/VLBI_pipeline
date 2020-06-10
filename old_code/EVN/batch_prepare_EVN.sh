#!/bin/bash
#PBS -N prepEVN
#PBS -q serial
#PBS -P ASTR1313
#PBS -l select=1:ncpus=4:mpiprocs=4:nodetype=haswell_reg
#PBS -l walltime=10:00:00
#PBS -o prepEVN.stdout 
#PBS -e prepEVN.stderr 
#PBS -m abe -M jack.f.radcliffe@gmail.com

epoch=eg078g
num_idi=5
cwd="/Volumes/HD-LXU3/EG078G/calibration/CASA"
CASApath="/Applications/CASA-5.7.app/Contents/MacOS"
cd $cwd

echo "Appending Tsys information to IDI files"
for i in {1..5}
do
	echo "Appending to "$epoch"_1_1.IDI"$i
	$CASApath"/casa" --nologger --log2term --nogui -c casa-vlbi/append_tsys.py $epoch".antab" $epoch"_1_1.IDI"$i
done

echo "Making gain curve file"
rm -r $epoch".gc"
$CASApath"/casa" --nologger --log2term --nogui -c casa-vlbi/gc.py $epoch".antab" $epoch".gc"


echo "Converting AIPS flag file to a CASA-compatible version"
rm $epoch"_casa.flag" 
$CASApath"/casa" --nologger --log2term --nogui -c casa-vlbi/flag.py $epoch".uvflg" $epoch"_casa.flag" $epoch"_1_1.IDI"*

rm "casa"*"log"
