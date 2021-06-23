import inspect, os, sys, json

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
casalog.origin('vp_make_mms')

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json',Odict=True,casa6=casa6)

rmdirs(['%s/%s.ms.flagversions'%(params['global']['cwd'],params['global']['project_code'])])
mmsfile='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])
msfile='%s_2.ms'%(mmsfile.split('.ms')[0])

## Make mms data-set
os.system('mv %s %s'%(mmsfile,msfile))

partition(vis=msfile,\
		  outputvis=mmsfile,
		  separationaxis=params['make_mms']['separationaxis'], 
     	  numsubms= params['make_mms']['numsubms'])
rmdirs([msfile])

steps_run['make_mms'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)

