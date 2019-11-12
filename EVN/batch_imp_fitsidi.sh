#!/bin/bash
#SBATCH -N 1-1
#SBATCH --tasks-per-node 12
#SBATCH -J import_fitsidi
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o importfits.sh.stdout.log
#SBATCH -e importfits.sh.stderr.log
#Run the application:
/usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg  "casa" --nologger --log2term --nogui -c imp_fitsidi.py