#!/bin/bash
#SBATCH -N 1-1
#SBATCH --tasks-per-node 24
#SBATCH -J VLBA_image_targets
#SBATCH -m plane=8
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.f.radcliffe@gmail.com
#SBATCH -o make64kIMs.sh.stdout.log
#SBATCH -e make64kIMs.sh.stderr.log
#SBATCH --partition=HighMem


for src in {100..122}
do
cp -r "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/UV/VLBA_SRC"$src".ms" "."
cp -r "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/UV/VLBA_SRC"$src".ms.flagversions" "."
/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg wsclean -name "VLBA_IM_SRC"$src -scale 0.001asec -size 64000 64000 -weight natural -niter 0 --mgain 1 'VLBA_SRC'$src'.ms'
rm -r "VLBA_SRC"$src".ms"
rm -r "VLBA_SRC"$src".ms.flagversions"
cp "VLBA_IM_SRC"$src"-image.fits" "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/IM/"
cp "VLBA_IM_SRC"$src"-dirty.fits" "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/IM/"
rm "VLBA_IM_SRC"$src"-image.fits"
rm "VLBA_IM_SRC"$src"-dirty.fits"
done