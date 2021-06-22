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

target_path = params['apply_to_all']['target_path']

target_files = get_target_files(target_dir=target_path,telescope=msinfo['TELE_NAME'],project_code=params['global']['project_code'],idifiles=[])


for i in target_files.keys():
	if i!='tar':
		if parallel == True:
			cmd1 = "import inspect, os, sys; sys.path.append('%s'); from VLBI_pipe_functions import *; inputs = load_json('vp_inputs.json'); params = load_json(inputs['parameter_file']); apply_to_all(prefix='%s',files=%s,tar=%s,params=params,casa6=%s); os.system('bash %s/job_flag_all.bash %s'); apply_tar_output(prefix=%s,params=params)"%(mpipath,i,target_files[i],target_files['tar'],casa6,cwd,'%s/%s.ms'%(cwd,i),i)
			cmd1 = "import inspect, os, sys; sys.path.append('%s'); from VLBI_pipe_functions import *; inputs = load_json('vp_inputs.json'); params = load_json(inputs['parameter_file']); os.system('bash %s/job_flag_all.bash %s'); apply_tar_output(prefix=%s,params=params)"%(mpipath,cwd,'%s/%s.ms'%(cwd,i),i)
			cmdId = client.push_command_request(cmd1,block=False)
			cmd.append(cmdId[0])
		else:
			apply_to_all(prefix=i,files=target_files[i],tar=target_files['tar'],params=params,casa6=casa6)
			os.system('bash %s/job_flag_all.bash %s'%(cwd,'%s/%s.ms'%(cwd,i)))
			apply_tar_output(prefix=i,params=params)
if parallel == True:
	resultList = client.get_command_response(cmd,block=True)
