import inspect, os, sys, json

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
casalog.origin('vp_import_fitsidi')

## Load params
inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json',Odict=True,casa6=casa6)


casalog.post(origin=filename,message='Searching for location of fitsidifiles')
## Set location of fitsidifiles
if params['global']['fitsidi_path'] == "":
	params['global']['fitsidi_path'] = params['global']['cwd']
	casalog.post(origin=filename,message='Fitsidifile path not set ... assuming they are in the current working directory',priority='WARN')

casalog.post(origin=filename,message='Fitsidifiles to be located in %s'%params['global']['fitsidi_path'])



## Find fitsfiles
if params['global']['fitsidi_files'] == ["auto"]:
	idifiles = find_fitsidi(idifilepath=params['global']['fitsidi_path'],\
		         cwd=params['global']['cwd'])
else:
	casalog.post(origin=filename,message='Using idifiles specified in parameter file')
	casalog.post(origin=filename,message='Checking whether specified idifiles exist')
	idifiles = params['global']['fitsidi_files']
	for i,j in enumerate(idifiles):
		fullidi = "%s/%s"%(params['global']['fitsidi_path'],j)
		idifiles[i] = fullidi
		if os.path.exists(fullidi) == False:
			casalog.post(priority='SEVERE',origin=filename,message='Fitsidifile %s does not exist ... exiting'%fullidi)
			sys.exit()


## Copy idifiles to cwd if not originally there
if steps_run['prepare_data'] == 0:
	if params['global']['fitsidi_path'] != params['global']['cwd']:
		casalog.post(origin=filename,message='Fitsidifiles in different directory. Moving to cwd.',priority='INFO')
		for j,i in enumerate(idifiles):
			rmfiles(['%s/%s'%(params['global']['cwd'],i.split(params['global']['fitsidi_path']+'/')[1])])
			os.system('rsync --progress %s %s'%(i,params['global']['cwd']))
			if os.path.exists('%s/%s'%(params['global']['cwd'],i.split(params['global']['fitsidi_path']+'/')[1])) == False:
				os.system('cp %s %s'%(i,params['global']['cwd']))
				if os.path.exists('%s/%s'%(params['global']['cwd'],i.split(params['global']['fitsidi_path']+'/')[1])) == False:
					casalog.post(origin=filename,message='Could not move files with rsync or cp ... exiting',priority='SEVERE')
					sys.exit()
			idifiles[j] = '%s/%s'%(params['global']['cwd'],i.split(params['global']['fitsidi_path']+'/')[1])
else: 
	for j,i in enumerate(idifiles):
		idifiles[j] = '%s/%s'%(params['global']['cwd'],i.split(params['global']['fitsidi_path']+'/')[1])

rmdirs(['%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])])
importfitsidi(fitsidifile=idifiles,\
	          vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),\
	          constobsid=params['import_fitsidi']["const_obs_id"],\
	          scanreindexgap_s=params['import_fitsidi']["scan_gap"])

append_pbcor_info(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),
	              params=params)

if params['import_fitsidi']['remove_idi'] == True:
	rmfiles(idifiles)

if params['import_fitsidi']['make_backup'] == True:
	rmfiles(["%s/%s_backup.tar.gz"%(params['global']['cwd'],params['global']['project_code'])])
	os.system("tar -cvzf %s/%s_backup.tar.gz %s/%s.ms"%(params['global']['cwd'],params['global']['project_code'],params['global']['cwd'],params['global']['project_code']))


save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)

steps_run['import_fitsidi'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
