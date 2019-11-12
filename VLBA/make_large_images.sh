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


for src in 024 031 032 033 035 088 089 091 092 093 094 100 119 130 133 135 145 147 152 153 155 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204
do
cp -r "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/UV/VLBA_SRC"$src".ms.tar.gz" "."
cp -r "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/UV/VLBA_SRC"$src".ms.flagversions.tar.gz" "."
tar "-xvzf" "VLBA_SRC"$src".ms.tar.gz" 
tar "-xvzf" "VLBA_SRC"$src".ms.flagversions.tar.gz" 
/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg wsclean -name "VLBA_IM_SRC"$src -scale 0.001asec -size 64000 64000 -weight natural -niter 0 --mgain 1 'VLBA_SRC'$src'.ms'
rm -r "VLBA_SRC"$src".ms" "VLBA_SRC"$src".ms.tar.gz"
rm -r "VLBA_SRC"$src".ms.flagversions" "VLBA_SRC"$src".ms.flagversions.tar.gz"
cp "VLBA_IM_SRC"$src"-image.fits" "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/IM/"
cp "VLBA_IM_SRC"$src"-dirty.fits" "/users/jradcliffe5/idia/VLBA_GOODSN/targets/phase_referenced/IM/"
rm "VLBA_IM_SRC"$src"-image.fits"
rm "VLBA_IM_SRC"$src"-dirty.fits"
done