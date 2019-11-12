#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J apriori_cal
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o apriori.sh.stdout.log
#SBATCH -e apriori.sh.stderr.log
#Run the application:
inbase=eg078g

/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa\
 /usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg\
   "casa" --nologger --log2term --nogui -c run_mpi_priorcal.py $inbase