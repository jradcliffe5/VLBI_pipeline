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
casalog.origin('vp_prepare_apply_all')

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


inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['prepare_apply_all'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = os.path.join(params['global']['cwd'],"")
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

target_path = os.path.join(params['prepare_apply_all']['target_path'],"")

target_files = get_target_files(target_dir=target_path,telescope=msinfo['TELE_NAME'],project_code=params['global']['project_code'],idifiles=[])

tar = str(target_files['tar'])
with open('target_files.txt', 'w') as f:
	for i in target_files.keys():
		if i != 'tar':
			f.write(tar+" "+i+" "+" ".join(target_files[i])+'\n')

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
steps_run['prepare_apply_all'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)

