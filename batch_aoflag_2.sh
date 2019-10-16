#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J AOflag
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o flag_2.sh.stdout.log
#SBATCH -e flag_2.sh.stderr.log
#Run the application:
#a2 b1 b2 c1 c2 c3 d1 d2 d3 e1 e2
for VARIABLE in a1 
do
	/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg  "aoflagger" -strategy J1234_619.rfis -fields 1,3 "$VARIABLE"/VLBA_"$VARIABLE".ms
done