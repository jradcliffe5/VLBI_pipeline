import inspect, os, sys, json

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json')

cwd = params['global']['cwd']