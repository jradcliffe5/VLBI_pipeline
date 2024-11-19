import inspect, os, sys, json

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from casavlbitools.fitsidi import append_tsys, convert_flags, append_gc
from casavlbitools.casa import convert_gaincurve
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
casalog.origin('vp_prepare_data')

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

try: 
	from astropy.io import fits
except:
	import pyfits as fits

casalog.origin('prepare_data')
casalog.post("")

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)

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
	idifiles= natural_sort(idifiles)
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

telescop = []
for i in idifiles:
	hdu = fits.open(i)
	telescop.append(hdu['ARRAY_GEOMETRY'].header['ARRNAM'])
	hdu.close()

if telescop.count(telescop[0]) == len(telescop):
	telescop = telescop[0]
	casalog.post(origin=filename,message='All fits files from same array i.e. %s'%telescop,priority='INFO')
else:
	casalog.post(origin=filename,message='Fits files from different arrays :( please clean your fits file directory'%telescop,priority='SEVERE')
	sys.exit()

## Find antab file (typical EVN antab files are <project_code>.antab)
if telescop == 'EVN':
	if params['prepare_data']['antab_file'] == 'auto':
		if os.path.exists('%s.antab'%params['global']['project_code']) == True:
			antabfile='%s.antab'%params['global']['project_code']
			casalog.post(origin=filename,message='Antab file found - %s.antab'%params['global']['project_code'],priority='INFO')
		elif os.path.exists('%s_1.antab'%params['global']['project_code']) == True:
			antabfile='%s_1.antab'%params['global']['project_code']
			casalog.post(origin=filename,message='Antab file found - %s_1.antab'%params['global']['project_code'],priority='INFO')
		else:
			casalog.post(origin=filename,message='Auto set antab file %s.antab does not exist ... exiting'%params['global']['project_code'],priority='SEVERE')
			sys.exit()
	else:
		if os.path.exists('%s'%params['prepare_data']['antab']) == False:
			casalog.post(origin=filename,message='Antab file %s does not exist, please correct ... exiting'%params['prepare_data']['antab'],priority='SEVERE')
			sys.exit()
		else:
			antabfile='%s'%params['prepare_data']['antab']

ts_fits = check_fits_ext(idifiles=idifiles,ext='SYSTEM_TEMPERATURE',del_ext=params['prepare_data']['replace_antab'])
if (params['prepare_data']['replace_antab'] == True)|(ts_fits==False):
	casalog.post(origin=filename,message='Appending TSYS information onto idifiles',priority='INFO')
	for i in idifiles:
		if parallel == True:
			cmd1 = "import inspect, os, sys; sys.path.append('%s'); from casavlbitools.fitsidi import append_tsys; append_tsys(antabfile='%s', idifiles='%s')"%(mpipath,antabfile,i)
			cmdId = client.push_command_request(cmd1,block=False)
			cmd.append(cmdId[0])
		else:
			casalog.post(origin=filename,message='Appending to %s'%i)
			append_tsys(antabfile=antabfile, idifiles=i)
	if parallel == True:
		resultList = client.get_command_response(cmd,block=True)
else:
	casalog.post(origin=filename,message='System temperature information already exists in the idifile',priority='INFO')

### Convert gaincurve
gc_fits = check_fits_ext(idifiles=idifiles,ext='GAIN_CURVE',del_ext=params['prepare_data']['replace_antab'])
if (params["prepare_data"]["replace_antab"] == True)|(gc_fits==False):
	rmdirs(['%s/%s.gc'%(params['global']['cwd'],params['global']['project_code'])])
	casalog.post(origin=filename,message='Appending gaincurve information',priority='INFO')
	if telescop == 'VLBA':
		antabfile='%s/%s/data/VLBA_gains/vlba_gains.key'%(params['global']['cwd'],params['global']['vlbipipe_path'])
	for i in idifiles:
		if parallel == True:
			cmd1 = "import inspect, os, sys; sys.path.append('%s'); from casavlbitools.fitsidi import append_tsys; append_gc(antabfile='%s', idifile='%s')"%(mpipath,antabfile,i)
			cmdId = client.push_command_request(cmd1,block=False)
			cmd.append(cmdId[0])
		else:
			casalog.post(origin=filename,message='Appending to %s'%i)
			append_gc(antabfile=antabfile, idifile=i)
	if parallel == True:
		resultList = client.get_command_response(cmd,block=True)
else:
	casalog.post(origin=filename,message='Gain curve information already exists in the idifile',priority='INFO')

#for i in idifiles:
#	append_gc(antabfile=antabfile, idifile=i)

if params["prepare_data"]["flag_file"] != "none":
	casalog.post(origin=filename,message='Generating CASA-compatable observatory flags',priority='INFO')
	if params["prepare_data"]["flag_file"] == "auto":
		if telescop == 'EVN':
			flagfile="%s/%s.uvflg"%(params['global']['cwd'],params['global']['project_code'])
			if os.path.exists(flagfile) == False:
				flagfile="%s/%s_1.uvflg"%(params['global']['cwd'],params['global']['project_code'])
				if os.path.exists(flagfile) == False:
					casalog.post(origin=filename,message='Flag file - %s - does not exist, please correct ... exiting'%flagfile,priority='SEVERE')
					sys.exit()
		elif telescop == 'VLBA':
			flagfile="%s/%s.flag"%(params['global']['cwd'],params['global']['project_code'])
			if os.path.exists(flagfile) == False:
				casalog.post(origin=filename,message='Flag file - %s - does not exist, please correct ... exiting'%flagfile,priority='SEVERE')
				sys.exit()
		else:
			casalog.post(origin=filename,message='Cannot find flags automatically for array %s'%telescop,priority='SEVERE')
			sys.exit()
	else:
		flagfile="%s"%(params['prepare_data']['flag_file'])
		if os.path.exists(flagfile) == False:
			casalog.post(origin=filename,message='Flag file - %s - does not exist, please correct ... exiting'%flagfile,priority='SEVERE')
			sys.exit()
	convert_flags(infile=flagfile, idifiles=idifiles, outfp=sys.stdout, outfile='%s_casa.flags'%params['global']['project_code'])

gt_r['prepare_data'] = {}
for k in ['gaintable','gainfield','spwmap','interp']:
	gt_r['prepare_data'][k] = []
save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)

steps_run['prepare_data'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
