import inspect, os, sys, json, re
from collections import OrderedDict
import tarfile

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
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

## Apply to standard files
applycal(vis='%s/%s'%(cwd,msfile),
	     field=",".join(params['global']['targets']),
	     gaintable=gaintables['gaintable'],
		 gainfield=gaintables['gainfield'],
		 interp=gaintables['interp'],
		 spwmap=gaintables['spwmap'],
		 parang=gaintables['parang'])

for i in params['global']['targets']:
	rmdirs(['%s/%s_calibrated.ms'%(cwd,i),'%s/%s_calibrated.ms.flagversions'%(cwd,i)])
	split(vis='%s/%s'%(cwd,msfile),
		  field=i,
		  outputvis='%s/%s_calibrated.ms'%(cwd,i))
	if params['apply_target']["statistical_reweigh"]['run'] == True:
		statwt(vis='%s/%s_calibrated.ms'%(cwd,i),
			   timebin=params['apply_target']["statistical_reweigh"]["timebin"],
               chanbin=params['apply_target']["statistical_reweigh"]["chanbin"],
               statalg=params['apply_target']["statistical_reweigh"]["statalg"],
               fitspw= params['apply_target']["statistical_reweigh"]["fitspw"],
               datacolumn='data')
	elif params['apply_target']["weigh_by_ants"]['run'] == True:
		print('not implemented yet')
	else:
		pass
	delims = []
	for z in ['.psf','.image','.sumwt','.mask','.residual','.pb']:
		delims.append('%s-initimage%s'%(i,z))
	rmdirs(delims)
	tclean(vis='%s/%s_calibrated.ms'%(cwd,i),
		   imagename='%s-initimage'%i,
		   field='%s'%i,
		   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][i]/1000.),
		   imsize=[1024,1024],
		   deconvolver='clarkstokes',
		   niter = int(1e5),
		   weighting='natural',
		   nsigma=1.2,
		   usemask='auto-multithresh',
		   noisethreshold=4.0,
		   sidelobethreshold=1.0
		   )
	#rmfiles(['%s/%s.tar.gz'%(cwd,i)])
	#make_tarfile(output_filename='%s_calibrated.tar.gz'%i, source_dir='%s/%s_calibrated.ms'%(cwd,i))
	#rmdirs(['%s/%s_calibrated.ms'%(cwd,i)])

save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['apply_target'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)