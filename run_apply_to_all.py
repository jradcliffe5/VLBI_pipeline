import inspect, os, sys, json, re, csv
from collections import OrderedDict
import tarfile

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

mpipath = os.path.dirname(os.path.realpath(filename))

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
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['apply_to_all'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

if params['global']['job_manager'] == 'bash':
	target_files={}
	tar = []
	prefix = []
	for line in open('target_files.txt'):
		listWords = line.strip('\n').split(" ")
		prefix.append(listWords[1])
		tar.append(listWords[0])
		target_files[listWords[1]] = listWords[2:]
	for j in range(len(prefix)):
		if (params['apply_to_all']["mppc_parallel"] == True)&(parallel==True):
			if int(sys.argv[i]) == 1:
				if params["apply_to_all"]["image_target"]["run"] == True:
					cmd1 = "import inspect, os, sys; sys.path.append('%s'); inputs = load_json('%s/vp_inputs.json'); params = load_json(inputs['parameter_file_path']);apply_to_all(prefix='%s',files=%s,tar=%s,params=params,casa6=%s,parallel=False,part=%s);targets = image_targets(prefix='%s',params=params,parallel=False);apply_tar_output(prefix='%s',params=params,targets=targets)"%(mpipath,cwd,prefix[j],target_files[prefix[j]],tar[j],casa6,int(sys.argv[i]),prefix[j],prefix[j])
				else:
					cmd1 = "import inspect, os, sys; sys.path.append('%s'); inputs = load_json('%s/vp_inputs.json'); params = load_json(inputs['parameter_file_path']); apply_to_all(prefix='%s',files=%s,tar=%s,params=params,casa6=%s,parallel=False,part=%s);targets = [], apply_tar_output(prefix='%s',params=params,targets=targets)"%(mpipath,cwd,prefix[j],target_files[prefix[j]],tar[j],casa6,int(sys.argv[i]),prefix[j])
			else:
				cmd1 = "import inspect, os, sys; sys.path.append('%s'); inputs = load_json('%s/vp_inputs.json'); params = load_json(inputs['parameter_file_path']);apply_to_all(prefix='%s',files=%s,tar=%s,params=params,casa6=%s,parallel=False,part=%s)"%(mpipath,cwd,prefix[j],target_files[prefix[j]],tar[j],casa6,int(sys.argv[i]))
			cmdId = client.push_command_request(cmd1,block=False)
			cmd.append(cmdId[0])
		else:
			apply_to_all(prefix=prefix[j],files=target_files[prefix[j]],tar=tar[j],params=params,casa6=casa6,parallel=parallel,part=int(sys.argv[i]))
			if int(sys.argv[i]) == 1:
				if params["apply_to_all"]["image_target"]["run"] == True:
					targets = image_targets(prefix=prefix[j],params=params,parallel=parallel)
				else:
					targets = []
				apply_tar_output(prefix=prefix[j],params=params,targets=targets)
				rmfiles(['%s/%s_msinfo.json'%(params['global']['cwd'],prefix[j])])

	if parallel == True:
		resultList = client.get_command_response(cmd,block=True)
else:
	target_files = {}
	prefix = sys.argv[i+2]
	tar = sys.argv[i+1]
	target_files[prefix] = sys.argv[i+3:]
	
	if sys.argv[i] == '0':
		apply_to_all(prefix=prefix,files=target_files[prefix],tar=tar,params=params,casa6=casa6,parallel=parallel,part=0)
	if sys.argv[i] == '1':
		if params["apply_to_all"]["image_target"]["run"] == True:
			apply_to_all(prefix=prefix,files=target_files[prefix],tar=tar,params=params,casa6=casa6,parallel=parallel,part=1)
			targets = image_targets(prefix=prefix,params=params,parallel=parallel)
		else:
			apply_to_all(prefix=prefix,files=target_files[prefix],tar=tar,params=params,casa6=casa6,parallel=parallel,part=1)
			targets = []
		apply_tar_output(prefix=prefix,params=params,targets=targets)
		rmfiles(['%s/%s_msinfo.json'%(params['global']['cwd'],prefix)])
	
save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
steps_run['apply_to_all'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)