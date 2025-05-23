import inspect, os, sys, json, tarfile

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
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json',Odict=True,casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['import_fitsidi'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

rmdirs(['%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])])
if os.path.exists("%s/%s_backup.tar"%(params['global']['cwd'],params['global']['project_code'])) == False:
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
		idifiles = natural_sort(idifiles)
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

	idifiles= natural_sort(idifiles)
	casalog.post(origin=filename,message='Importing fits into measurement set: %s.ms'%(params['global']['project_code']),priority='INFO')
	
	use_quick_constobs = True
	if use_quick_constobs == False:
		importfitsidi(fitsidifile=idifiles,\
					  vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),\
					  constobsid=params['import_fitsidi']["const_obs_id"],\
					  scanreindexgap_s=params['import_fitsidi']["scan_gap"])
	else:
		importfitsidi(fitsidifile=idifiles,\
					  vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),\
					  constobsid=False,\
					  scanreindexgap_s=params['import_fitsidi']["scan_gap"])
		if params['import_fitsidi']["const_obs_id"] == True:
			quick_constobs(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']))

	append_pbcor_info(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),
					params=params)

	if params['import_fitsidi']['remove_idi'] == True:
		rmfiles(idifiles)

	if params['import_fitsidi']['make_backup'] == True:
		casalog.post(origin=filename,message='Creating backup: %s_backup.tar'%(params['global']['project_code']),priority='INFO')
		rmfiles(["%s/%s_backup.tar"%(params['global']['cwd'],params['global']['project_code'])])
		source_dir = "%s/%s.ms"%(params['global']['cwd'],params['global']['project_code'])
		with tarfile.open('%s/%s_backup.tar'%(params['global']['cwd'],params['global']['project_code']),"w") as tar:
			tar.add(source_dir, arcname=os.path.basename(source_dir))
else:
	casalog.post(origin=filename,message='Extracting: %s_backup.tar'%(params['global']['project_code']),priority='INFO')
	file = tarfile.open("%s/%s_backup.tar"%(params['global']['cwd'],params['global']['project_code']))  
	file.extractall('%s/'%params['global']['cwd']) 
	file.close() 


if params['global']['use_initial_model'] != {}:
	clearcal(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),addmodel=True)
	for i in params['global']['use_initial_model'].keys():
		ft(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),
			field=i,
			nterms=len(params['global']['use_initial_model'][i]),
			model=params['global']['use_initial_model'][i],usescratch=True)


save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)


save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
steps_run['import_fitsidi'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
