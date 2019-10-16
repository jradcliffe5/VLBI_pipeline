#!/bin/bash
#SBATCH -N 2-2
#SBATCH --tasks-per-node 12
#SBATCH -J VLBA_image_pcal
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.f.radcliffe@gmail.com
#SBATCH -o pselfcal.sh.stdout.log
#SBATCH -e pselfcal.sh.stderr.log
#Run the application:
## Inputs
field="J1234+619"
type=('p' 'p' 'p' 'ap' 'ap' 'p' 'p')
solint=("inf" "inf" "inf" "inf" "inf" "inf" "30s")
combine=("spw" "" "" "spw" "spw" "" "spw")
applytype="calonly"
#a1 a2 b1 b2 c1 c2 c3 d1 d2 d3 e1 e2
#bad c2 e1 e2
#$epoch'/VLBA.mbd2' $epoch'/VLBA.mbd3'
for epoch in all
do
	vis=$epoch"/VLBA_"$epoch".ms"
	gaintables=($epoch'/VLBA.tsys' $epoch'/VLBA.gcal' $epoch'/VLBA.accor' $epoch'/VLBA.sbd' $epoch'/VLBA.bpass' $epoch'/VLBA.mbd1' $epoch'/VLBA.mbd2' $epoch'/VLBA.mbd3')

	#rm -r "$epoch"/"$field"_"$cycle"-*
	#/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg "wsclean"\
	# -name "$epoch"/"$field"_"$cycle" -size 640 640 -scale 0.0005asec -weight natural -niter 1000 -auto-threshold 0.5 -auto-mask 4 -mgain 0.95 $vis
	#/usr/bin/singularity exec /data/exp_soft/containers/kern5-dev.simg "wsclean"\
	#-size 640 640 -scale 0.0005asec -weight natural -niter 1000 -auto-threshold 0.5 -auto-mask 4 -mgain 0.95 -name "$epoch"/"$field"_"$cycle" $vis -predict
	/data/exp_soft/pipelines/casa-prerelease-5.3.0-115.el7/bin/mpicasa /usr/bin/singularity\
	 exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg\
	   "casa" --nologger --log2term --nogui -c run_selfcal.py $vis $(IFS=$','; echo "${type[*]}") $field $(IFS=$','; echo "${solint[*]}") $(IFS=$','; echo "${gaintables[*]}") $(IFS=$','; echo "${combine[*]}") $applytype $epoch
done