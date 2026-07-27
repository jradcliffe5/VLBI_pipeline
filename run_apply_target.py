import inspect, os, sys, json, re
from collections import OrderedDict
import tarfile
import numpy as np

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

try:
	# CASA 6
	import casatools
	from casatasks import *
	casalog.showconsole(True)
	casa6=True
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import casalog
	casa6=False
casalog.origin('vp_apply_target')

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['apply_target'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = os.path.join(params['global']['cwd'],"")
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(cwd,params['global']['project_code']))==False:
	casalog.post(origin=filename,message='No cached msinfo found ... generating %s/%s_msinfo.json'%(cwd,params['global']['project_code']),priority='INFO')
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(cwd,params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(cwd,params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(cwd,params['global']['project_code']))

if steps_run['apply_target'] == 1:
	flagmanager(vis=msfile,mode='restore',versionname='vp_apply_target')
else:
	flagmanager(vis=msfile,mode='save',versionname='vp_apply_target')

## Apply to standard files
casalog.post(origin=filename,message='Applying %d gaintable(s) to target field(s): %s'%(len(gaintables['gaintable']),",".join(params['global']['targets'])),priority='INFO')
applycal(vis='%s%s'%(cwd,msfile),
	     field=",".join(params['global']['targets']),
	     gaintable=gaintables['gaintable'],
		 gainfield=gaintables['gainfield'],
		 interp=gaintables['interp'],
		 spwmap=gaintables['spwmap'],
		 parang=gaintables['parang'])

for i in params['global']['targets']:
	casalog.post(origin=filename,message='Processing target field: %s'%i,priority='INFO')
	rmdirs(['%s/%s_calibrated.ms'%(cwd,i),'%s/%s_calibrated.ms.flagversions'%(cwd,i)])

	if params['apply_target']["flag_target"] == True:
		casalog.post(origin=filename,message='Running tfcrop flagging on calibrated target: %s'%i,priority='INFO')
		flagdata(vis='%s%s'%(cwd,msfile),
				mode='tfcrop',
				field=i,
				datacolumn='corrected',
				combinescans=False,
				winsize=3,
				timecutoff=4.5,
				freqcutoff=4.5,
				maxnpieces=7,
				halfwin=1,
				extendflags=False,
				action='apply',
				display='',
			    flagbackup=False)
	casalog.post(origin=filename,message='Splitting calibrated target %s to %s/%s_calibrated.ms'%(i,cwd,i),priority='INFO')
	split(vis='%s%s'%(cwd,msfile),
		  field=i,
		  outputvis='%s/%s_calibrated.ms'%(cwd,i))

	if params['apply_target']["statistical_reweigh"]['run'] == True:
		casalog.post(origin=filename,message='Statistically reweighting %s_calibrated.ms'%i,priority='INFO')
		statwt(vis='%s%s_calibrated.ms'%(cwd,i),
			   minsamp=params['apply_target']["statistical_reweigh"]["minsamp"],
               datacolumn='data')
		tb = casatools.table()
		tb.open('%s/%s_calibrated.ms'%(cwd,i)) 
		weight=tb.getcol('WEIGHT')
		tb.close()
		flagdata(vis='%s/%s_calibrated.ms'%(cwd,i),
		         mode='clip',
				 datacolumn='WEIGHT',
				 clipminmax=[0,np.median(weight)+6*np.std(weight)])
		
	elif params['apply_target']["weigh_by_ants"]['run'] == True:
		casalog.post(origin=filename,message='weigh_by_ants is not implemented yet ... skipping reweighting for %s'%i,priority='WARN')
	else:
		pass
	delims = []
	for z in ['.psf','.image','.sumwt','.mask','.residual','.pb']:
		delims.append('%s-initimage%s'%(i,z))
	rmdirs(delims)

	casalog.post(origin=filename,message='Making initial image for target %s (%s/images/%s-initimage)'%(i,cwd,i),priority='INFO')
	tclean(vis='%s/%s_calibrated.ms'%(cwd,i),
		   imagename='%s/images/%s-initimage'%(cwd,i),
		   field='%s'%i,
		   datacolumn='data',
		   stokes='pseudoI',
		   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][i]/1000.),
		   imsize=[1024,1024],
		   deconvolver='clarkstokes',
		   niter = int(1e5),
		   weighting='natural',
		   nsigma=1.2,
		   usemask='auto-multithresh',
		   noisethreshold=4.0,
		   sidelobethreshold=1.0,
		   parallel=False)
	
	#rmfiles(['%s/%s.tar.gz'%(cwd,i)])
	#make_tarfile(output_filename='%s_calibrated.tar.gz'%i, source_dir='%s/%s_calibrated.ms'%(cwd,i))
	#rmdirs(['%s/%s_calibrated.ms'%(cwd,i)])

if params['apply_target']["backup_caltables"] == True:
	casalog.post(origin=filename,message='Backing up caltables to %s_caltables.tar'%p_c,priority='INFO')
	rmfiles(["%s_caltables.tar"%p_c])
	archive = tarfile.open("%s_caltables.tar"%p_c, "w")
	for i in gaintables['gaintable']:
		archive.add(i, arcname=i.split('/')[-1])
	archive.close()

casalog.post(origin=filename,message='apply_target complete',priority='INFO')
save_json(filename='%s/vp_gaintables.last.json'%(cwd), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(cwd), array=gaintables, append=False)
steps_run['apply_target'] = 1
save_json(filename='%s/vp_steps_run.json'%(cwd), array=steps_run, append=False)