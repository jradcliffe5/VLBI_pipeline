from simms import simms
import os, glob, sys
import numpy as np

#INPUT  = "input"
#OUTPUT = "output"
#MSDIR  = "msdir"
#singularity_image_dir=os.environ["STIMELA_IMAGES_PATH"]
#stimela.register_globals()
#SKYMODEL   = "blank_sky.txt"
import sys
i = sys.argv[1]


arcmin = np.floor(np.linspace(0,20,121))
arcsec = np.linspace(0,20,121)*60. % 60.
arcmin=[0]
arcsec=[0]

for k in range(len(arcmin)): 
	os.system('rm -r %s/%s_%d_%d.ms'%(i,i,np.round(arcmin[k]),np.round(arcsec[k])))
	MS="%s_%d_%d.ms"%(i,np.round(arcmin[k]),np.round(arcsec[k]))
	simms.create_empty_ms(
	msname=MS,
	label=None,
	tel="EVN",
	pos="evn_vla_mod.itrf",
	pos_type='ascii',
	ra="12h00m00s",
	dec="60d%02dm%02ds"%(np.round(arcmin[k]),np.round(arcsec[k])),
	synthesis=12,
	scan_length=[1],
	dtime=10,
	freq0="1.536GHz",#1536000000.0,
	dfreq="4MHz",
	nchan="32",
	stokes='RR RL LR LL',
	setlimits=False,
	elevation_limit=0,
	shadow_limit=0,
	outdir="%s"%i,
	nolog=False,
	coords='itrf',
	lon_lat=None,
	noup=False,
	nbands=1,
	direction=[],
	date=None,
	fromknown=False,
	feed='perfect R L',
	scan_lag=0,
	auto_corr=False,
	optimise_start=None
)
