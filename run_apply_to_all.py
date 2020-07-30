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

try:
	if casa6 == True:	
		from casampi.MPICommandClient import MPICommandClient
	else:
		from mpi4casa.MPICommandClient import MPICommandClient
	client = MPICommandClient()
	client.set_log_mode('redirect')
	client.start_services()
	parallel=True
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
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

target_path = params['apply_to_all']['target_path']

target_files = get_target_files(target_dir=target_path,telescope=msinfo['TELE_NAME'],project_code=params['global']['project_code'],idifiles=[])

params['import_fitsidi']["const_obs_id"] = False

if parallel == True:
	cmd = []
	for i in target_files.keys():
		if i !='tar':
			cmd1 = "importfitsidi(fitsidifile=%s, vis='%s.ms', constobsid=%s, scanreindexgap_s=%s)"%("%s"%target_files[i], i, params['import_fitsidi']["const_obs_id"], params['import_fitsidi']["scan_gap"])
			cmdId = client.push_command_request(cmd1,block=False)
			cmdId = client.push_command_request("applycal(vis='%s.ms', gaintable=%s, parang=True)"%(i,"%s"%gaintables['gaintable']),block=False,target_server=cmdId)
			cmd.append(cmdId[0])
if parallel == True:
	resultList = client.get_command_response(cmd,block=True)
#importfitsidi(fitsidifile=idifiles,\
#	          vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),\
#	          constobsid=params['import_fitsidi']["const_obs_id"],\
#	          scanreindexgap_s=params['import_fitsidi']["scan_gap"])
#		cmd.append(cmdId[0])
'''
if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))
'''