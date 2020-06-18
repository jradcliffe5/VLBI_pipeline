import inspect, os, sys, json, re
from collections import OrderedDict

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json',Odict=True)
gaintables = load_gaintables(params)

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

msinfo = get_ms_info(msfile)


if params['init_flag']['flag_edge_chans']['run'] == True:
	if steps_run['init_flag'] == 1:
		flagmanager(vis=msfile,
			 		mode='restore',
			 		versionname='pre_edge_chan')
	else:
		flagmanager(vis=msfile,
					mode='save',
					versionname='pre_edge_chan')

	ec=calc_edge_channels(value=params['init_flag']['flag_edge_chans']['edge_chan_flag'],
						  nspw=msinfo['SPECTRAL_WINDOW']['nspws'],
						  nchan=msinfo['SPECTRAL_WINDOW']['nchan'])

	flagdata(vis=msfile,
			 mode='manual',
			 spw=ec)

if params['init_flag']['autocorrelations'] == True:
	if steps_run['init_flag'] == 1:
		flagmanager(vis=msfile,
				    mode='restore',
				    versionname='autocorrelations')
	else:
		flagmanager(vis=msfile,
			        mode='save',
			        versionname='autocorrelations')
	flagdata(vis=msfile,
		     mode='manual',
		     autocorr=True)

if params['init_flag']['quack_data']['run'] == True:
	if steps_run['init_flag'] == 1:
		flagmanager(vis=msfile,
			        mode='restore',
			        versionname='quack')
	else:
		flagmanager(vis=msfile,
			        mode='save',
			        versionname='quack')
	quack_ints = params['init_flag']['quack_data']['quack_time']
	quack_mode = params['init_flag']['quack_data']['quack_mode']
	if type(quack_ints)==dict:
		for i in quack_ints.keys():
			flagdata(vis=msfile,
				     antenna=i,
				     mode='quack',
				     quackinterval=quack_ints[i],
				     quackmode=quack_mode)
	elif type(quack_ints)==float:
		flagdata(vis=msfile,
			     mode='quack',
			     quackinterval=quack_ints,
			     quackmode=quack_mode)
	else:
		casalog.post(priority='SEVERE',origin=filename,message='quack can either be dictionary to map antenna to quacking time or float to apply to all telescopes')
		sys.exit()

save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['init_flag'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)