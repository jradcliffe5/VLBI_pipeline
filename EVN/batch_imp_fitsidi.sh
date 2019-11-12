#!/bin/bash
#SBATCH -N 1-1
#SBATCH --tasks-per-node 12
#SBATCH -J EVN_imp_fits
#SBATCH -m cyclic
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jack.radcliffe@manchester.ac.uk
#SBATCH -o importfits.sh.stdout.log
#SBATCH -e importfits.sh.stderr.log
#Run the application:
inbase=eg078g


/usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg  "casa" --nologger --log2term --nogui -c append_tsys.py $inbase".antab" $inbase"_1_1.IDI"*
rm "-r" $inbase".gcal"
/usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg  "casa" --nologger --log2term --nogui -c gc.py $inbase".antab" $inbase".gcal"
rm $inbase".CASA.flags.txt"
/usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg  "casa" --nologger --log2term --nogui -c flag.py $inbase".flag" $inbase".CASA.flags.txt"
/usr/bin/singularity exec /data/exp_soft/containers/casa-stable-5.5.0-149.simg  "casa" --nologger --log2term --nogui -c run_imp_fitsidi.py $inbase