#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J fringe_fitting
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o fringefitall.sh.stdout.log
#SBATCH -e fringefitall.sh.stderr.log
#Run the application:
epoch="a1"
phasecal="J1234+619"
sbdcal="J0927+390"
casa_tclean="True"
# a1 a2 b1 b2 c1 c2 c3 d1 d2 d3 e1 e2
# bad c1 e1 e2
for epoch in all
do
	/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg\
	   "casa" --nologger --log2term --nogui -c fringe_fit_part1.py $epoch $phasecal $sbdcal

	/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg  "aoflagger" -strategy J1234_619.rfis -fields 1,3 --column CORRECTED_DATA "$epoch"/VLBA_"$epoch".ms

	/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg\
	   "casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $phasecal $sbdcal $casa_tclean 1

	for W_LOOP in 2 3
	do
		rm -r $epoch"/ff_im_cycle_"$W_LOOP"-0*"
		/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg "casa" --nologger --log2term --nogui -c fringe_fit_part2.py $epoch $phasecal $sbdcal $casa_tclean $W_LOOP
	done
done