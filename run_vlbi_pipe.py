import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections

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

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

## Load global inputs
inputs = headless(sys.argv[i])


steps = copy.deepcopy(inputs)
for i in inputs:
	if i in ['parameter_file','make_scripts','run_jobs']:
		del steps[i]

## Load parameters
params=load_json(inputs['parameter_file'])

save_json(filename='%s/vp_inputs.json'%(params['global']['cwd']),array=inputs,append=False)

casalog.post(priority='INFO',origin=filename,message='Initialising VLBI pipeline run')

if os.path.exists('%s/%s'%(params['global']['cwd'],'vp_steps_run.json')) == False:
	casalog.post(priority='INFO',origin=filename,message='No previous steps have been run - creating step logger')
	init_pipe_run(steps)
	steps_run=load_json('vp_steps_run.json')
else:
	casalog.post(priority='INFO',origin=filename,message='A previous run has been detected')
	casalog.post(priority='WARN',origin=filename,message='If you dont mean to do this please delete vp_steps_run.json')
	steps_run=load_json('vp_steps_run.json')

## Time to build all scripts
if inputs['make_scripts'] == 'True':
	for i in steps.keys():
		if steps[i]==1:
			write_hpc_headers(step=i,params=params)
			if i in ['import_fitsidi']:
				parallel=False
			elif ((steps['make_mms'] == 1)|(steps_run['make_mms']==1)):
				parallel=True
			elif i in ['prepare_data']:
				parallel=True
			else:
				parallel=False
			if i=='init_flag':
				write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag='both',casa6=casa6)
			else:
				write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag=False,casa6=casa6)
			print(i,parallel)


if inputs['run_jobs'] == 'True':
	jobs_to_run = []
	for i in steps.keys():
		if steps[i]==1:
			jobs_to_run.append(i)
	write_job_script(steps=jobs_to_run,job_manager=params['global']['job_manager'])