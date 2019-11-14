#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J AOflag
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o initflag.sh.stdout.log
#SBATCH -e initflag.sh.stderr.log
#Run the application:
#a1 a2 b1 b2 c1 c2 c3 d1 d2 d3 e1 e2
# bad c2 e1 e2
inbase=eg078g
/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg  "aoflagger" -strategy J1234_619.rfis -fields 0,1,157 $inbase".ms"
#/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg  "aoflagger" -strategy 0319+415.rfis -fields 0  VLBAGN_cal_all.ms
