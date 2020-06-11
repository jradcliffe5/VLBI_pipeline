import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections
from taskinit import casalog

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

## Load global inputs
inputs = headless(sys.argv[i])


steps = copy.deepcopy(inputs)
for i in steps:
	if i in ['parameter_file','make_scripts','run_jobs']:
		del steps[i]

## Load parameters
with open(inputs['parameter_file'], "r") as f:
	params = json_load_byteified(f)
f.close()

with open('%s/vp_inputs.json'%(params['global']['cwd']), 'w') as f:
	json.dump(inputs, f,indent=4, separators=(',', ': '))
f.close()

casalog.post(priority='INFO',origin=filename,message='Initialising VLBI pipeline run')

if os.path.exists('%s/%s'%(params['global']['cwd'],'vlbi_pipe_step_run.json')) == False:
	casalog.post(priority='INFO',origin=filename,message='No previous steps have been run - creating step logger')
	init_pipe_run(inputs)
else:
	casalog.post(priority='INFO',origin=filename,message='A previous run has been detected')
	casalog.post(priority='WARN',origin=filename,message='If you dont mean to do this please delete vlbi_pipe_step_run.json')

## Time to build all scripts
if bool(inputs['make_scripts']) == True:
	for i in steps.keys():
		if steps[i]==1:
			write_hpc_headers(step=i,params=params)
			write_commands(step=i,inputs=inputs,params=params,parallel=False,aoflag=False)

