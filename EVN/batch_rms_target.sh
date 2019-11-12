#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J VLBA_image_pcal
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.f.radcliffe@gmail.com
#SBATCH -o tclean.sh.stdout.log
#SBATCH -e tclean.sh.stderr.log
#Run the application:
## Inputs
#/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
#	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg\
#	   "casa" --nologger --log2term --nogui -c run_test_target.py
rm -r test_rms-*
/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg wsclean -name test_rms -scale 1mas -size 640 640 -weight natural -niter 1 --mgain 0.95 all/test_target.ms