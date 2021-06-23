import inspect, os, sys, json, re
from collections import OrderedDict
import tarfile

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
mpipath = os.path.dirname(os.path.realpath(filename))

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
casalog.origin('vp_apply_to_all')

try:
	if casa6 == True:
		from casampi.MPICommandClient import MPICommandClient
	else:
		from mpi4casa.MPICommandClient import MPICommandClient
	client = MPICommandClient()
	client.set_log_mode('redirect')
	client.start_services()
	parallel=True
	cmd = []
except:
	parallel=False

## Import arguments
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass


inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

target_files = {}
prefix = sys.argv[i+2]
tar = sys.argv[i+1]
target_files[prefix] = sys.argv[i+3:]

if steps_run['make_mms'] == 1:
	parallel=True
else:
	parallel = False

if sys.argv[i] == '0':
	apply_to_all(prefix=prefix,files=target_files[prefix],tar=tar,params=params,casa6=casa6,parallel=parallel)
if sys.argv[i] == '1':
	apply_tar_output(prefix=prefix,params=params)

