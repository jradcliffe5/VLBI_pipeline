#! /bin/bash

# first job - import fitsidi
jid1=$(sbatch batch_imp_fitsidi.sh)
# Do priorcals
jid2=$(sbatch  --dependency=afterany:$jid1 batch_mpi_priorcal.sh)
# Do flagging
jid3=$(sbatch  --dependency=afterany:$jid2 batch_aoflag.sh)
# Do fringefitting
jid4=$(sbatch  --dependency=afterany:$jid3 batch_ff_v2.sh)