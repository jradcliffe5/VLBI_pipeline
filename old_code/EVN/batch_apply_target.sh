#!/bin/bash
#SBATCH -N 1-1
#SBATCH --tasks-per-node 12
#SBATCH -J VLBA_apply_targets
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.f.radcliffe@gmail.com
#SBATCH -o applytarget2.sh.stdout.log
#SBATCH -e applytarget2.sh.stderr.log
#Run the application:
# '049' '055' '081' '085' '097' '110' '111' '156' '160' '164' '182' '183'
#for src in '110' '160' '164' '182' '183'
for src in 000
do
echo "$src"
#/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
#	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg casa --nologger --log2term -c run_calibrate_target.py 1 $src

/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg  "aoflagger" -strategy J1234_619.rfis 'VLBA_SRC'$src'.ms'

/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg casa --nologger --log2term -c run_calibrate_target.py 2 $src

tar '-cvzf' 'VLBA_SRC'$src'.ms.tar.gz' 'VLBA_SRC'$src'.ms'
tar '-cvzf' 'VLBA_SRC'$src'.ms.flagversions.tar.gz' 'VLBA_SRC'$src'.ms.flagversions'
'/bin/cp' '-r' 'VLBA_SRC'$src'.ms.tar.gz' '/users/jradcliffe5/idia/VLBA_GOODSN/phase_referenced/UV/'
'/bin/cp' '-r' 'VLBA_SRC'$src'.ms.flagversions.tar.gz' '/users/jradcliffe5/idia/VLBA_GOODSN/phase_referenced/UV/'
'/bin/cp' '-r'  'test_'$src'.image' '/users/jradcliffe5/idia/VLBA_GOODSN/phase_referenced/IM/'
'/bin/rm' '-r' 'VLBA_SRC'$src'.ms' 'VLBA_SRC'$src'.ms.tar.gz' 'VLBA_SRC'$src'.ms.flagversions' 'VLBA_SRC'$src'.ms.flagversions.tar.gz' 'test_'$src'.image' 'test_'$src'.model' 'test_'$src'.psf' 'test_'$src'.residual' 'test_'$src'.sumwt'
done
