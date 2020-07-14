import inspect, os, sys, json

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from casavlbitools.fitsidi import append_tsys, convert_flags, append_gc
from casavlbitools.casa import convert_gaincurve
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

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)

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

## Find antab file (typical EVN antab files are <project_code>.antab)
if params['prepare_EVN']['antab_file'] == 'auto':
	if os.path.exists('%s.antab'%params['global']['project_code']) == False:
		casalog.post(origin=filename,message='Auto set antab file %s.antab does not exist ... exiting'%params['global']['project_code'],priority='SEVERE')
		sys.exit()
	else:
		antabfile='%s.antab'%params['global']['project_code']
else:
	if os.path.exists('%s'%params['prepare_EVN']['antab']) == False:
		casalog.post(origin=filename,message='Antab file %s does not exist, please correct ... exiting'%params['prepare_EVN']['antab'],priority='SEVERE')
		sys.exit()
	else:
		antabfile='%s'%params['prepare_EVN']['antab']


## Append tsys
casalog.post(origin=filename,message='Appending TSYS information onto idifiles',priority='INFO')
for i in idifiles:
	casalog.post(origin=filename,message='Appending to %s'%i)
	append_tsys(antabfile=antabfile, idifiles=i)

### Convert gaincurve
rmdirs(['%s/%s.gc'%(params['global']['cwd'],params['global']['project_code'])])
casalog.post(origin=filename,message='Generating gaincurve information - %s.gc'%params['global']['project_code'],priority='INFO')
convert_gaincurve(antab=antabfile, gc='%s/%s.gc'%(params['global']['cwd'],params['global']['project_code']), min_elevation=params['prepare_EVN']['gaincurve']['min_elevation'], max_elevation=params['prepare_EVN']['gaincurve']['max_elevation'])
#for i in idifiles:
#	append_gc(antabfile=antabfile, idifile=i)

if params["prepare_EVN"]["flag_file"] != "none":
	casalog.post(origin=filename,message='Generating CASA-compatable observatory flags',priority='INFO')
	if params["prepare_EVN"]["flag_file"] == "auto":
		flagfile="%s/%s.uvflg"%(params['global']['cwd'],params['global']['project_code'])
		if os.path.exists(flagfile) == False:
			casalog.post(origin=filename,message='Flag file - %s - does not exist, please correct ... exiting'%flagfile,priority='SEVERE')
			sys.exit()
	else:
		flagfile="%s"%(params['prepare_EVN']['flag_file'])
		if os.path.exists(flagfile) == False:
			casalog.post(origin=filename,message='Flag file - %s - does not exist, please correct ... exiting'%flagfile,priority='SEVERE')
			sys.exit()
	convert_flags(infile=flagfile, idifiles=idifiles, outfp=sys.stdout, outfile='%s_casa.flags'%params['global']['project_code'])

steps_run['prepare_EVN'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
