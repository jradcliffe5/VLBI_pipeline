import inspect, os, sys, json

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from casavlbitools.fitsidi import append_tsys, convert_flags
from casavlbitools.casa import convert_gaincurve
from VLBI_pipe_functions import *

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

## Load global inputs
inputs = headless(sys.argv[i])
## Load parameters
with open(inputs['parameter_file'], "r") as f:
	params = json_load_byteified(f)

casalog.post(origin=filename,message='Searching for location of fitsidifiles')
## Set location of fitsidifiles
if params['prepare_EVN']['fitsidi_path'] == "":
	params['prepare_EVN']['fitsidi_path'] = params['global']['cwd']
	casalog.post(origin=filename,message='Fitsidifile path not set ... assuming they are in the current working directory',priority='WARN')

casalog.post(origin=filename,message='Fitsidifiles to be located in %s'%params['prepare_EVN']['fitsidi_path'])



## Find fitsfiles
if params['prepare_EVN']['fitsidi_files'] == ["auto"]:
	idifiles = find_fitsidi(idifilepath=params['prepare_EVN']['fitsidi_path'],\
		         cwd=params['global']['cwd'])
else:
	casalog.post(origin=filename,message='Using idifiles specified in parameter file')
	casalog.post(origin=filename,message='Checking whether specified idifiles exist')
	idifiles = params['prepare_EVN']['fitsidi_files']
	for i,j in enumerate(idifiles):
		fullidi = "%s/%s"%(params['prepare_EVN']['fitsidi_path'],j)
		idifiles[i] = fullidi
		if os.path.exists(fullidi) == False:
			casalog.post(priority='SEVERE',origin=filename,message='Fitsidifile %s does not exist ... exiting'%fullidi)
			sys.exit()


## Copy idifiles to cwd if not originally there
if params['prepare_EVN']['fitsidi_path'] != params['global']['cwd']:
	casalog.post(origin=filename,message='Fitsidifiles in different directory. Moving to cwd.',priority='INFO')
	for j,i in enumerate(idifiles):
		rmfiles(['%s/%s'%(params['global']['cwd'],i.split(params['prepare_EVN']['fitsidi_path']+'/')[1])])
		os.system('rsync --progress %s %s'%(i,params['global']['cwd']))
		if os.path.exists('%s/%s'%(params['global']['cwd'],i.split(params['prepare_EVN']['fitsidi_path']+'/')[1])) == False:
			os.system('cp %s %s'%(i,params['global']['cwd']))
			if os.path.exists('%s/%s'%(params['global']['cwd'],i.split(params['prepare_EVN']['fitsidi_path']+'/')[1])) == False:
				casalog.post(origin=filename,message='Could not move files with rsync or cp ... exiting',priority='SEVERE')
				sys.exit()
		idifiles[j] = '%s/%s'%(params['global']['cwd'],i.split(params['prepare_EVN']['fitsidi_path']+'/')[1])

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
append_tsys(antabfile=antabfile, idifiles=idifiles)

### Convert gaincurve
rmdirs(['%s/%s.gc'%(params['global']['cwd'],params['global']['project_code'])])
convert_gaincurve(antab=antabfile, gc='%s/%s.gc'%(params['global']['cwd'],params['global']['project_code']), min_elevation=params['prepare_EVN']['gaincurve']['min_elevation'], max_elevation=params['prepare_EVN']['gaincurve']['min_elevation'])

print(idifiles)



