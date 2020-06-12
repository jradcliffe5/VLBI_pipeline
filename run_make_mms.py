import inspect, os, sys, json

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json')


mmsfile='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])
msfile='%s_2.ms'%(mmsfile,mmsfile.split('.ms')[0])

## Make mms data-set
os.system('mv %s %s_2.ms'%(mmsfile,msfile))

partition(vis=msfile,\
		  outputvis=mmsfile,
		  separationaxis=params['make_mms']['separationaxis'], 
     	  numsubms= params['make_mms']['numsubms'])
rmdirs([msfile])

steps_run['make_mms'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)

