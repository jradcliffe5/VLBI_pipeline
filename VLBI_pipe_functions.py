import re, os, json, inspect, sys, copy, glob, tarfile, random, math
import collections
from collections import OrderedDict
## Numerical routines
import numpy as np
## Plotting routines
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import gridspec
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.lines as mlines
## Sci-py dependencies
from scipy.interpolate import interp1d
from scipy.optimize import least_squares
from scipy import signal
from scipy.constants import c as speed_light
from itertools import cycle
import tempfile
try:
	# CASA 6
	import casatools
	from casatasks import *
	casalog.showconsole(True)
	casa6=True
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import *
	from bandpass_cli import bandpass_cli as bandpass
	from importfitsidi_cli import importfitsidi_cli as importfitsidi
	from flagdata_cli import flagdata_cli as flagdata
	from applycal_cli import applycal_cli as applycal
	from split_cli import split_cli as split
	from gencal_cli import gencal_cli as gencal
	from partition_cli import partition_cli as partition
	casa6=False
	

class NpEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, np.integer):
			return int(obj)
		elif isinstance(obj, np.floating):
			return float(obj)
		elif isinstance(obj, np.ndarray):
			return obj.tolist()
		else:
			return super(NpEncoder, self).default(obj)

def json_load_byteified(file_handle):
	return _byteify(
		json.load(file_handle, object_hook=_byteify),
		ignore_dicts=True
	)

def json_loads_byteified(json_text):
	return _byteify(
		json.loads(json_text, object_hook=_byteify),
		ignore_dicts=True
	)

def json_load_byteified_dict(file_handle,casa6):
	#print(casa6)
	if casa6==True:
		return convert_temp(_byteify(
			json.load(file_handle, object_hook=_byteify, object_pairs_hook=OrderedDict),
			ignore_dicts=True))
	else:
		return convert(_byteify(
			json.load(file_handle, object_hook=_byteify, object_pairs_hook=OrderedDict),
			ignore_dicts=True))

def json_loads_byteified_dict(json_text,casa6):
	if casa6==True:
		return convert_temp(_byteify(
			json.loads(json_text, object_hook=_byteify, object_pairs_hook=OrderedDict),
			ignore_dicts=True))
	else:
		return convert(_byteify(
			json.loads(json_text, object_hook=_byteify, object_pairs_hook=OrderedDict),
			ignore_dicts=True))

def convert(data):
	if isinstance(data, basestring):
		return str(data)
	elif isinstance(data, collections.Mapping):
		return OrderedDict(map(convert, data.iteritems()))
	elif isinstance(data, collections.Iterable):
		return type(data)(map(convert, data))
	else:
		return data

def convert_temp(data):
	if isinstance(data, str):
		return str(data)
	elif isinstance(data, collections.Mapping):
		return OrderedDict(map(convert_temp, data.items()))
	elif isinstance(data, collections.Iterable):
		#print(data)
		return type(data)(map(convert_temp, data))
	else:
		return data

def _byteify(data, ignore_dicts=False):
	# if this is a unicode string, return its string representation
	try:
		if isinstance(data, unicode):
			return data.encode('utf-8')
	except: 
		if isinstance(data, str):
			return data
	# if this is a list of values, return list of byteified values
	if isinstance(data, list):
		return [ _byteify(item, ignore_dicts=True) for item in data ]
	# if this is a dictionary, return dictionary of byteified keys and values
	# but only if we haven't already byteified it
	if isinstance(data, dict) and not ignore_dicts:
		try:
			return {
				_byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
				for key, value in data.iteritems()
			}
		except:
			return {
				_byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
				for key, value in data.items()
			}
	# if it's anything else, return it in its original form
	return data

def load_json(filename,Odict=False,casa6=False):
	if Odict==False:
		with open(filename, "r") as f:
			json_data = json_load_byteified(f)
		f.close()
	else:
		with open(filename, "r") as f:
			json_data = json_load_byteified_dict(f,casa6)
		f.close()
	return json_data

def save_json(filename,array,append=False):
	if append==False:
		write_mode='w'
	else:
		write_mode='a'
	with open(filename, write_mode) as f:
		json.dump(array, f,indent=4, separators=(',', ': '),cls=NpEncoder)
	f.close()

def headless(inputfile):
	''' Parse the list of inputs given in the specified file. (Modified from evn_funcs.py)'''
	INPUTFILE = open(inputfile, "r")
	control=collections.OrderedDict()
	# a few useful regular expressions
	newline = re.compile(r'\n')
	space = re.compile(r'\s')
	char = re.compile(r'\w')
	comment = re.compile(r'#.*')
	# parse the input file assuming '=' is used to separate names from values
	for line in INPUTFILE:
		if char.match(line):
			line = comment.sub(r'', line)
			line = line.replace("'", '')
			(param, value) = line.split('=')
			param = newline.sub(r'', param)
			param = param.strip()
			param = space.sub(r'', param)
			value = newline.sub(r'', value)
			value = value.replace(' ','').strip()
			valuelist = value.split(',')
			if len(valuelist) == 1:
				if valuelist[0] == '0' or valuelist[0]=='1' or valuelist[0]=='2':
					control[param] = int(valuelist[0])
				else:
					control[param] = str(valuelist[0])
			else:
				control[param] = ','.join(valuelist)
	return control

def rmfiles(files):
	func_name = inspect.stack()[0][3]
	for i in files:
		if "*" in i:
			files_to_die = glob.glob(i)
			casalog.post(priority="INFO",origin=func_name,message='Files matching with %s - deleting'% i)
			for j in files_to_die:
				if os.path.exists(j) == True:
					casalog.post(priority="INFO",origin=func_name,message='File %s found - deleting'% j)
					os.system('rm %s'%j)
				else:
					pass
		elif os.path.exists(i) == True:
			casalog.post(priority="INFO",origin=func_name,message='File %s found - deleting'% i)
			os.system('rm %s'%i)
		else:
			casalog.post(priority="INFO",origin=func_name,message='No file found - %s'% i)
	return

def rmdirs(dirs):
	func_name = inspect.stack()[0][3]
	for i in dirs:
		if "*" in i:
			files_to_die = glob.glob(i)
			casalog.post(priority="INFO",origin=func_name,message='Directories matching with %s - deleting'% i)
			for j in files_to_die:
				if os.path.exists(j) == True:
					casalog.post(priority="INFO",origin=func_name,message='Directory/table %s found - deleting'% j)
					os.system('rm -r %s'%j)
				else:
					pass
		elif os.path.exists(i) == True:
			casalog.post(priority="INFO",origin=func_name,message='Directory/table %s found - deleting'% i)
			os.system('rm -r %s'%i)
		else:
			casalog.post(priority="INFO",origin=func_name,message='No file found - %s'% i)
	return

def init_pipe_run(inputs):
	inputs2=OrderedDict({})
	for a,b in zip(inputs.keys(),inputs.values()):
		inputs2[a]=b
	#for i in ['parameter_file','make_scripts','run_jobs']:
	#	del inputs2[i]
	for i in inputs2.keys():
		inputs2[i] = 0
	save_json(filename='vp_steps_run.json',array=inputs2,append=False)

def find_fitsidi(idifilepath="",cwd="",project_code=""):
	func_name = inspect.stack()[0][3]
	casalog.post(priority="INFO",origin=func_name,message='Will attempt to find fitsidifiles in %s'%idifilepath)
	### Try first with project code and end
	fitsidifiles=[]
	for i in os.listdir(idifilepath):
		if (i.startswith(project_code.lower())|i.startswith(project_code.upper()))&(('IDI' in i)|(i.endswith("idifits"))):
			fitsidifiles.append('%s/%s'%(idifilepath,i))
			casalog.post(priority="INFO",origin=func_name,message='FOUND - %s'% i)
	if fitsidifiles == []:
		for i in os.listdir(idifilepath):
			if ('IDI' in i)|i.endswith('idifits'):
				fitsidifiles.append('%s/%s'%(idifilepath,i))
				casalog.post(priority="INFO",origin=func_name,message='FOUND - %s'% i)
	if fitsidifiles == []:
		casalog.post(priority="SEVERE",origin=func_name,message='Cannot find any fitsidifiles in %s.. exiting'%idifilepath)
		sys.exit()
	else:
		return fitsidifiles

def write_hpc_headers(step,params):
	func_name = inspect.stack()[0][3]

	hpc_opts = {}
	hpc_opts['job_manager'] = params['global']['job_manager']
	hpc_opts['job_name'] = 'vp_%s'%step
	hpc_opts['email_progress'] = params['global']["email_progress"] 
	hpc_opts['hpc_account'] = params['global']['HPC_project_code']
	hpc_opts['error'] = step

	if ((hpc_opts['job_manager'] == 'pbs')|(hpc_opts['job_manager'] == 'bash')|(hpc_opts['job_manager'] == 'slurm')):
		pass
	else:
		casalog.post(priority='SEVERE',origin=func_name, message='Incorrect job manager, please select from pbs, slurm or bash')
		sys.exit()

	for i in ['partition','walltime','nodetype']:
		if params[step]["hpc_options"][i] == 'default':
			hpc_opts[i] = params['global']['default_%s'%i]
		else:
			hpc_opts[i] = params[step]["hpc_options"][i]
	for i in ['nodes','cpus','mpiprocs']:
		if params[step]["hpc_options"][i] == -1:
			hpc_opts[i] = params['global']['default_%s'%i]
		else:
			hpc_opts[i] = params[step]["hpc_options"][i]
	

	hpc_dict = {'slurm':{
					 'partition'     :'#SBATCH --partition=%s'%hpc_opts['partition'],
					 'nodetype'      :'',
					 'cpus'          :'#SBATCH --tasks-per-node %s'%hpc_opts['cpus'], 
					 'nodes'         :'#SBATCH -N %s-%s'%(hpc_opts['nodes'],hpc_opts['nodes']),
					 'mpiprocs'      :'', 
					 'walltime'      :'#SBATCH --time=%s'%hpc_opts['walltime'],
					 'job_name'      :'#SBATCH -J %s'%hpc_opts['job_name'],
					 'hpc_account'   :'#SBATCH --account %s'%hpc_opts['hpc_account'],
					 'email_progress':'#SBATCH --mail-type=BEGIN,END,FAIL\n#SBATCH --mail-user=%s'%hpc_opts['email_progress'],
					 'error':'#SBATCH -o logs/%s.sh.stdout.log\n#SBATCH -e logs/%s.sh.stderr.log'%(hpc_opts['error'],hpc_opts['error'])
					},
				'pbs':{
					 'partition'     :'#PBS -q %s'%hpc_opts['partition'],
					 'nodetype'      :'',
					 'cpus'          :'#PBS -l select=%s:ncpus=%s:mpiprocs=%s:nodetype=%s'%(hpc_opts['nodes'],hpc_opts['cpus'],hpc_opts['mpiprocs'],hpc_opts['nodetype']), 
					 'nodes'         :'',
					 'mpiprocs'      :'', 
					 'walltime'      :'#PBS -l walltime=%s'%hpc_opts['walltime'],
					 'job_name'      :'#PBS -N %s'%hpc_opts['job_name'],
					 'hpc_account'   :'#PBS -P %s'%hpc_opts['hpc_account'],
					 'email_progress':'#PBS -m abe -M %s'%hpc_opts['email_progress'],
					 'error':'#PBS -o logs/%s.sh.stdout.log\n#PBS -e logs/%s.sh.stderr.log'%(hpc_opts['error'],hpc_opts['error'])
					},
				'bash':{
					 'partition'     :'',
					 'nodetype'      :'',
					 'cpus'          :'', 
					 'nodes'         :'',
					 'mpiprocs'      :'', 
					 'walltime'      :'',
					 'job_name'      :'',
					 'hpc_account'   :'',
					 'email_progress':'',
					 'error':''
					}
				}

	hpc_header= ['#!/bin/bash']

	if step == 'apply_to_all':
		file = open("%s/target_files.txt"%params['global']['cwd'], "r")
		nonempty_lines = [line.strip("\n") for line in file if line != "\n"]
		line_count = len(nonempty_lines)
		file.close()
		if params[step]['hpc_options']['max_jobs'] == -1:
			tasks = '0-'+str(line_count-1)
		else:
			if (line_count-1) > params[step]['hpc_options']['max_jobs']:
				tasks = '0-'+str(line_count-1)+'%'+str(params[step]['hpc_options']['max_jobs'])
			else:
				tasks = '0-'+str(line_count-1)
		hpc_dict['slurm']['array_job'] = '#SBATCH --array='+tasks
		hpc_dict['pbs']['array_job'] = '#PBS -t '+tasks
		hpc_dict['bash']['array_job'] = ''
		hpc_opts['array_job'] = -1

	hpc_job = hpc_opts['job_manager']
	for i in hpc_opts.keys():
		if i != 'job_manager':
			if hpc_opts[i] != '':
				if hpc_dict[hpc_opts['job_manager']][i] !='':
					hpc_header.append(hpc_dict[hpc_job][i])


	with open('job_%s.%s'%(step,hpc_job), 'w') as filehandle:
		for listitem in hpc_header:
			filehandle.write('%s\n' % listitem)

def write_commands(step,inputs,params,parallel,aoflag,casa6):
	func_name = inspect.stack()[0][3]
	commands=[]
	casapath=params['global']['casapath']
	vlbipipepath=params['global']["vlbipipe_path"]
	if aoflag==False:
		if parallel == True:
			mpicasapath = params['global']['mpicasapath']
		else:
			mpicasapath = ''
		if params['global']['singularity'] == True:
			singularity='singularity exec'
		else:
			singularity=''
		if (params['global']['job_manager'] == 'pbs'):
			job_commands=''
			commands.append('cd %s'%params['global']['cwd'])
			if (parallel == True):
				job_commands='--map-by node -hostfile $PBS_NODEFILE'
		else:
			job_commands=''
		if casa6 == False:
			commands.append('%s %s %s %s --nologger --log2term -c %s/run_%s.py'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
		else:
			commands.append('%s %s %s %s %s/run_%s.py'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
	elif aoflag=='both':
		for i in params['global']['AOflag_command']:
			commands.append(i)
		msfile='%s.ms'%params['global']['project_code']
		fields=params[step]['AO_flag_fields']
		if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
			msinfo = get_ms_info(msfile)
			save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
		else:
			msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))
		ids = []
		for i in fields:
			ids.append(str(msinfo['FIELD']['fieldtoID'][i]))
		commands[-1] = commands[-1]+' -fields %s '%(",".join(ids))
		commands[-1] = commands[-1]+'-strategy %s %s'%(params[step]['AO_flag_strategy'],msfile)
		if parallel == True:
			mpicasapath = params['global']['mpicasapath']
		else:
			mpicasapath = ''
		if params['global']['singularity'] == True:
			singularity='singularity exec'
		else:
			singularity=''
		if (params['global']['job_manager'] == 'pbs'):
			job_commands=''
			commands.append('cd %s'%params['global']['cwd'])
			if (parallel == True):
				job_commands='--map-by node -hostfile $PBS_NODEFILE'
		else:
			job_commands=''
		
		if casa6 == False:
			commands.append('%s %s %s %s --nologger --log2term -c %s/run_%s.py'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
		else:
			commands.append('%s %s %s %s %s/run_%s.py'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))

	elif aoflag==True:
		if (params['global']['job_manager'] == 'pbs'):
			commands.append('cd %s'%params['global']['cwd'])
		for i in params['global']['AOflag_command']:
			commands.append(i)
		msfile='%s.ms'%params['global']['project_code']
		fields=params[step]['flag_fields']
		if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
			msinfo = get_ms_info(msfile)
			save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
		else:
			msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))
		ids = []
		for i in fields:
			ids.append(str(msinfo['FIELD']['fieldtoID'][i]))
		commands[-1] = commands[-1]+' -fields %s '%(",".join(ids))
		commands[-1] = commands[-1]+'-strategy %s %s'%(params[step]['AO_flag_strategy'],msfile)

	elif aoflag=='apply_to_all':
		if (params['global']['job_manager'] == 'pbs'):
			commands.append('cd %s'%params['global']['cwd'])
		elif (params['global']['job_manager'] == 'slurm'):
			commands.append('a=$SLURM_ARRAY_TASK_ID')
		commands.append('readarray array < %s/target_files.txt'%params['global']['cwd'])

		if parallel == True:
			mpicasapath = params['global']['mpicasapath']
		else:
			mpicasapath = ''
		if params['global']['singularity'] == True:
			singularity='singularity exec'
		else:
			singularity=''
		if (params['global']['job_manager'] == 'pbs'):
			job_commands=''
			commands.append('cd %s'%params['global']['cwd'])
			if (parallel == True):
				job_commands='--map-by node -hostfile $PBS_NODEFILE'
		else:
			job_commands=''
		
		if casa6 == False:
			commands.append('%s %s %s %s --nologger --log2term -c %s/run_%s.py 0 ${array[$a]}'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
		else:
			commands.append('%s %s %s %s %s/run_%s.py 0 ${array[$a]}'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))

		commands.append("IFS=' ' read -r -a arrays <<< \"${array[$a]}\"")
		for i in params['global']['AOflag_command']:
			commands.append(i)
		commands[-1] = commands[-1]+' -strategy %s ${arrays[1]}.ms'%(params['init_flag']['AO_flag_strategy'])

		if casa6 == False:
			commands.append('%s %s %s %s --nologger --log2term -c %s/run_%s.py 1 ${array[$a]}'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
		else:
			commands.append('%s %s %s %s %s/run_%s.py 1 ${array[$a]}'%(mpicasapath,job_commands,singularity,casapath,vlbipipepath,step))
	else:
		casalog.post(priority='SEVERE',origin=func_name,message='Error with writing commands.')
		sys.exit()

	commands.append('mv "casa"*"log" "logs"')
	job_m = params['global']['job_manager']
	with open('job_%s.%s'%(step,job_m), 'a') as filehandle:
		for listitem in commands:
			filehandle.write('%s\n' % listitem)

def write_job_script(steps,job_manager):
	func_name = inspect.stack()[0][3]
	commands=['#!/bin/bash']
	for i,j in enumerate(steps):
		if i==0:
			depend=''
		else:
			if job_manager=='pbs':
				depend='-W depend=afterany:$%s'%(steps[i-1])
			if job_manager=='slurm':
				depend='--dependency=afterany:$%s'%(steps[i-1])
			if job_manager=='bash':
				depend=''
		if job_manager=='pbs':
			commands.append("%s=$(qsub %s job_%s.pbs)"%(j,depend,j))
		if job_manager=='slurm':
			commands.append('%s=$(sbatch --parsable %s job_%s.slurm)'%(j,depend,j))
		if job_manager=='bash':
			commands.append('bash job_%s.bash'%(j))
	

	with open('vp_runfile.bash','w') as f:
		for listitem in commands:
			f.write('%s\n' % listitem)
	f.close()

def get_ms_info(msfile):
	tb = casatools.table()
	ms = casatools.ms() 
	msinfo={}
	## antenna information
	tb.open('%s/ANTENNA'%msfile)
	ants = tb.getcol('NAME')
	ant={}
	ant['anttoID'] =dict(zip(ants, np.arange(0,len(ants),1)))
	ant['IDtoant'] = dict(zip(np.arange(0,len(ants),1).astype(str),ants))
	msinfo['ANTENNAS']=ant
	tb.close()

	## get spw information
	tb.open('%s/SPECTRAL_WINDOW'%msfile)
	spw={}
	spw['nspws'] = len(tb.getcol('TOTAL_BANDWIDTH'))
	spw['bwidth'] = np.sum(tb.getcol('TOTAL_BANDWIDTH'))
	spw['spw_bw'] = spw['bwidth']/spw['nspws']
	spw['freq_range'] = [tb.getcol('CHAN_FREQ')[0][0],tb.getcol('CHAN_FREQ')[0][0]+spw['bwidth']]
	spw['cfreq'] = np.average(spw['freq_range'])
	if ((np.max(tb.getcol('CHAN_WIDTH')) == np.min(tb.getcol('CHAN_WIDTH')))&(np.max(tb.getcol('NUM_CHAN')) == np.min(tb.getcol('NUM_CHAN')))) == True:
		spw['same_spws'] = True
		spw['nchan'] = np.max(tb.getcol('NUM_CHAN'))
	else:
		spw['same_spws'] = False
		spw['nchan'] = tb.getcol('NUM_CHAN')
	if spw['same_spws'] == True:
		spw['chan_width'] = tb.getcol('CHAN_WIDTH')[0][0]
	else:
		spw['chan_width'] = np.average(tb.getcol('CHAN_WIDTH'))
	tb.close()
	tb.open('%s/POLARIZATION'%msfile)
	spw['npol'] = tb.getcol('NUM_CORR')[0]
	polariz = tb.getcol('CORR_TYPE').flatten()
	ID_to_pol={'0': 'Undefined',
			 '1': 'I',
			 '2': 'Q',
			 '3': 'U',
			 '4': 'V',
			 '5': 'RR',
			 '6': 'RL',
			 '7': 'LR',
			 '8': 'LL',
			 '9': 'XX',
			 '10': 'XY',
			 '11': 'YX',
			 '12': 'YY',
			 '13': 'RX',
			 '14': 'RY',
			 '15': 'LX',
			 '16': 'LY',
			 '17': 'XR',
			 '18': 'XL',
			 '19': 'YR',
			 '20': 'YL',
			 '21': 'PP',
			 '22': 'PQ',
			 '23': 'QP',
			 '24': 'QQ',
			 '25': 'RCircular',
			 '26': 'LCircular',
			 '27': 'Linear',
			 '28': 'Ptotal',
			 '29': 'Plinear',
			 '30': 'PFtotal',
			 '31': 'PFlinear',
			 '32': 'Pangle'}
	pol2=[]
	for i,j in enumerate(polariz):
		pol2.append(ID_to_pol[str(j)])
	spw['spw_pols'] = pol2
	tb.close()
	msinfo['SPECTRAL_WINDOW'] = spw
	## Get field information
	tb.open('%s/FIELD'%msfile)
	fields = tb.getcol('NAME')
	field = {}
	field['fieldtoID'] =dict(zip(fields, np.arange(0,len(fields),1)))
	field['IDtofield'] = dict(zip(np.arange(0,len(fields),1).astype(str),fields))
	tb.close()
	## scans
	ms.open(msfile)
	scans = ms.getscansummary()
	ms.close()
	scan = {}
	for i in list(scans.keys()):
		#print(i)
		fieldid = scans[i]['0']['FieldId']
		if fieldid not in list(scan.keys()):
			#print(i)
			scan[fieldid] = [i]
		else:
			vals = scan[fieldid]
			scan[fieldid].append(i)
	msinfo['SCANS'] = scan
	## Get telescope_name
	tb.open('%s/OBSERVATION'%msfile)
	msinfo['TELE_NAME'] = tb.getcol('TELESCOPE_NAME')[0]
	tb.close()
	image_params = {}
	high_freq = spw['freq_range'][1]
	
	ms.open(msfile)
	f = []
	indx = []
	for i in field['fieldtoID'].keys():
		ms.selecttaql('FIELD_ID==%s'%field['fieldtoID'][i])
		try:
			max_uv = ms.getdata('uvdist')['uvdist'].max()
			image_params[i] = ((speed_light/high_freq)/max_uv)*(180./np.pi)*(3.6e6/5.)
			f.append(i)
			indx.append(field['fieldtoID'][i])
		except:
			pass
		ms.reset()
	ms.close()
	field = {}
	field['fieldtoID'] =dict(zip(f, indx))
	field['IDtofield'] =dict(zip(np.array(indx).astype(str),f))
	msinfo['FIELD'] = field
	msinfo["IMAGE_PARAMS"] = image_params
	
	return msinfo

def fill_flagged_soln(caltable='', fringecal=False):
	"""
	This is to replace the gaincal solution of flagged/failed solutions by the nearest valid 
	one.
	If you do not do that and applycal blindly with the table your data gets 
	flagged between  calibration runs that have a bad/flagged solution at one edge.
	Can be pretty bad when you calibrate every hour or more 
	(when you are betting on self-cal) of observation (e.g L-band of the EVLA)..one can 
	lose the whole hour of good data without realizing !
	"""
	if fringecal==False:
		gaincol='CPARAM'
	else:
		gaincol='FPARAM'
	tb = casatools.table()
	tb.open(caltable, nomodify=False)
	flg=tb.getcol('FLAG')
	#sol=tb.getcol('SOLUTION_OK')
	ant=tb.getcol('ANTENNA1')
	gain=tb.getcol(gaincol)
	t=tb.getcol('TIME')
	dd=tb.getcol('SPECTRAL_WINDOW_ID')
	#dd=tb.getcol('CAL_DESC_ID')
	maxant=np.max(ant)
	maxdd=np.max(dd)
	npol=len(gain[:,0,0])
	nchan=len(gain[0,:,0])
	
	k=1
	#print('maxant', maxant)
	numflag=0.0
	for k in range(maxant+1):
			for j in range (maxdd+1):
					subflg=flg[:,:,(ant==k) & (dd==j)]
					subt=t[(ant==k) & (dd==j)]
					#subsol=sol[:,:,(ant==k) & (dd==j)]
					subgain=gain[:,:,(ant==k) & (dd==j)]
					#print 'subgain', subgain.shape
					for kk in range(1, len(subt)):
							for chan in range(nchan):
									for pol in range(npol):
											if(subflg[pol,chan,kk] and not subflg[pol,chan,kk-1]):
													numflag += 1.0
													subflg[pol,chan,kk]=False
													#subsol[pol, chan, kk]=True
													subgain[pol,chan,kk]=subgain[pol,chan,kk-1]
											if(subflg[pol,chan,kk-1] and not subflg[pol,chan,kk]):
													numflag += 1.0
													subflg[pol,chan,kk-1]=False
													#subsol[pol, chan, kk-1]=True
													subgain[pol,chan,kk-1]=subgain[pol,chan,kk]
					flg[:,:,(ant==k) & (dd==j)]=subflg
					#sol[:,:,(ant==k) & (dd==j)]=subsol
					gain[:,:,(ant==k) & (dd==j)]=subgain


	#print('numflag', numflag)
	 
	###
	tb.putcol('FLAG', flg)
	#tb.putcol('SOLUTION_OK', sol)
	tb.putcol(gaincol, gain)
	tb.done()

def fill_flagged_soln2(caltable='', fringecal=False):
	"""
	This is to replace the gaincal solution of flagged/failed solutions by the nearest valid 
	one.
	If you do not do that and applycal blindly with the table your data gets 
	flagged between  calibration runs that have a bad/flagged solution at one edge.
	Can be pretty bad when you calibrate every hour or more 
	(when you are betting on self-cal) of observation (e.g L-band of the EVLA)..one can 
	lose the whole hour of good data without realizing !
	"""
	if fringecal==False:
		gaincol='CPARAM'
	else:
		gaincol='FPARAM'
	tb=casatools.table()
	tb.open(caltable, nomodify=False)
	flg=tb.getcol('FLAG')
	#sol=tb.getcol('SOLUTION_OK')
	ant=tb.getcol('ANTENNA1')
	gain=tb.getcol(gaincol)
	t=tb.getcol('TIME')
	dd=tb.getcol('SPECTRAL_WINDOW_ID')
	#dd=tb.getcol('CAL_DESC_ID')
	maxant=np.max(ant)
	maxdd=np.max(dd)
	npol=len(gain[:,0,0])
	nchan=len(gain[0,:,0])
	
	k=1
	numflag=0.0
	for k in range(maxant+1):
			for j in range (maxdd+1):
					subflg=flg[:,:,(ant==k) & (dd==j)]
					subt=t[(ant==k) & (dd==j)]
					#subsol=sol[:,:,(ant==k) & (dd==j)]
					subgain=gain[:,:,(ant==k) & (dd==j)]
					#print 'subgain', subgain.shape
					for kk in range(1, len(subt)):
							for chan in range(nchan):
									for pol in range(npol):
											if(subflg[pol,chan,kk] and not subflg[pol,chan,kk-1]):
													numflag += 1.0
													subflg[pol,chan,kk]=False
													#subsol[pol, chan, kk]=True
													subgain[pol,chan,kk]=subgain[pol,chan,kk-1]
											if(subflg[pol,chan,kk-1] and not subflg[pol,chan,kk]):
													numflag += 1.0
													subflg[pol,chan,kk-1]=False
													#subsol[pol, chan, kk-1]=True
													subgain[pol,chan,kk-1]=subgain[pol,chan,kk]
					for kk in range(len(subt)-2,-1, -1):
							for chan in range(nchan):
									for pol in range(npol):
											if(subflg[pol,chan,kk] and not subflg[pol,chan,kk+1]):
													numflag += 1.0
													subflg[pol,chan,kk]=False
													#subsol[pol, chan, kk]=True
													subgain[pol,chan,kk]=subgain[pol,chan,kk+1]
											if(subflg[pol,chan,kk] and not subflg[pol,chan,kk]):
													numflag += 1.0
													subflg[pol,chan,kk+1]=False
													#subsol[pol, chan, kk-1]=True
													subgain[pol,chan,kk+1]=subgain[pol,chan,kk]
					flg[:,:,(ant==k) & (dd==j)]=subflg
					#sol[:,:,(ant==k) & (dd==j)]=subsol
					gain[:,:,(ant==k) & (dd==j)]=subgain


	#print('numflag', numflag)
	 
	###
	tb.putcol('FLAG', flg)
	#tb.putcol('SOLUTION_OK', sol)
	tb.putcol(gaincol, gain)
	tb.done()

def filter_tsys_auto(caltable,nsig=[2.5,2.],jump_pc=20):
	tb=casatools.table()
	tb.open(caltable, nomodify=False)
	flg=tb.getcol('FLAG')
	#sol=tb.getcol('SOLUTION_OK')
	gaincol='FPARAM'
	ant=tb.getcol('ANTENNA1')
	gain=tb.getcol(gaincol)
	gain_edit = copy.deepcopy(gain)*0
	t=tb.getcol('TIME')
	dd=tb.getcol('SPECTRAL_WINDOW_ID')
	#print(dd)
	npol=gain.shape[0]
	for k in range(npol):
		print('npol=%s'%k)
		for i in np.unique(ant):
			print('nant=%s'%i)
			for j in np.unique(dd):
				print('nspw=%s'%j)
				flg_temp=flg[k,0,((ant==i)&(dd==j))]
				gain_uflg2=gain[k,0,((ant==i)&(dd==j))]
				gain_uflg = gain_uflg2[flg_temp==0]
				if gain_uflg != []:
					t_temp=t[((ant==i)&(dd==j))][flg_temp==0] 
					gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 41 ,n_sigmas=nsig[0])
					gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 10 ,n_sigmas=nsig[1])
					#gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 5 ,n_sigmas=2.5)
					gain_uflg, jump = detect_jump_and_smooth(gain_uflg,jump_pc=jump_pc)
					if jump == False:
						gain_uflg = smooth_series(gain_uflg, 21)
					gain_uflg2[flg_temp==0] = gain_uflg
					ind = np.where(np.isnan(gain_uflg2[flg_temp==0]))[0]
					flg_temp2 = flg_temp[flg_temp==0]
					flg_temp2[ind] = 1
					flg_temp[flg_temp==0] = flg_temp2
					flg[k,0,((ant==i)&(dd==j))] = flg_temp

					gain_edit[k,0,((ant==i)&(dd==j))]= gain_uflg2

	tb.putcol('FPARAM',gain_edit)
	tb.putcol('FLAG',flg)
	tb.close()

def smooth_series(y, box_pts):
	box = np.ones(box_pts)/box_pts
	#print(box_pts)
	y_smooth = np.convolve(y, box, mode='valid')
	y_smooth = np.hstack([np.ones(np.floor(box_pts/2.).astype(int))*y_smooth[0],y_smooth])
	y_smooth = np.hstack([y_smooth,np.ones(np.floor(box_pts/2.).astype(int))*y_smooth[-1]])
	return y_smooth

def hampel_filter(input_series, window_size, n_sigmas=3):
	
	n = len(input_series[1])
	new_series = input_series.copy()
	k = 1.4826 # scale factor for Gaussian distribution
	
	indices = []
	
	# possibly use np.nanmedian 
	for i in range((window_size),(n - window_size)):
		x0 = np.median(input_series[1][(i - window_size):(i + window_size)])
		S0 = k * np.median(np.abs(input_series[1][(i - window_size):(i + window_size)] - x0))
		if (np.abs(input_series[1][i] - x0) > n_sigmas * S0):
			new_series[1][i] = x0
			indices.append(i)

	detected_outliers = np.array(indices)
	already_tagged=[]
	for i in range(len(input_series[1])):
		if i<input_series[0].shape[0]-1:
			if i in detected_outliers:
				if i not in already_tagged:
					low=i-1
					t_low=input_series[0][low]
					while i+1 in detected_outliers:
						i+=1
						already_tagged.append(i)

					high=i+1
					t_high=input_series[0][high]
					#m=(gain_uflg[high]-gain_uflg[low])/(t_high-t_low)
					#c=gain_uflg[low]-(m*t_low)

					f = interp1d(x=[t_low,t_high], y=[input_series[1][low],input_series[1][high]])
					#print(t_temp2[np.arange(low,high,1)])
					#t_interp=t_temp2[np.arange(low,high,1)]
					
					input_series[1][low:high]= f(input_series[0][np.arange(low,high,1)])

	return input_series[1],detected_outliers

def detect_jump_and_smooth(array,jump_pc):
	jump_pc=jump_pc/100.
	try:
		for i,j in enumerate(array):
			if i<array.shape[0]-2:
				if (array[i+1] > 1.1*array[i])|(array[i+1]<0.9*array[i]):
					jump=True
					low=i
					if i < len(array)-1:
						#print(i+1)
						i+=1
						#print(i)
						while ((array[i+1] > (1+jump_pc)*array[i])==False)&((array[i+1]<(1-jump_pc)*array[i])==False):
							if i > (len(array)-3):
								#print(i)
								break
							else:
								#print(i)
								i+=1
					high=i+1
					diff=int((high-low)/2.)
					if diff%2 == 0:
						diff=diff+1
					array[low:high] = smooth_series(array[low:high],diff)
				else:
					jump=False
			else:
				jump=False
		return array, jump
	except:
		jump=False
		return array, jump

def append_gaintable(gaintables,caltable_params):
	for i,j in enumerate(gaintables.keys()):
		if j != 'parang':
			gaintables[j].append(caltable_params[i])
	return gaintables

def load_gaintables(params,casa6):
	cwd=params['global']['cwd']
	if os.path.exists('%s/vp_gaintables.json'%(cwd)) == False:
		gaintables=OrderedDict({})
		for a,b in zip(('gaintable','gainfield','spwmap','interp','parang'), ([],[],[],[],params['global']['do_parang'])):
			gaintables[a]=b
	else:
		gaintables=load_json('%s/vp_gaintables.json'%(cwd),Odict=True,casa6=casa6)
	return gaintables

def find_refants(pref_ant,msinfo):
	antennas = msinfo['ANTENNAS']['anttoID'].keys()
	refant=[]
	for i in pref_ant:
		if i in antennas:
			refant.append(i)
	return ",".join(refant)

def calc_edge_channels(value,nspw,nchan):
	func_name = inspect.stack()[0][3]
	if (type(value) == str):
		if value.endswith('%'):
			value=np.round((float(value.split('%')[0])/100.)*float(nchan),0).astype(int)
		else:
			casalog.post(priority='SEVERE',origin=func_name,message='Edge channels either needs to be an integer (number of channels) or a string with a percentage i.e. 5%')
			sys.exit()
	elif (type(value)==int):
		value=value
	else:
		casalog.post(priority='SEVERE',origin=func_name,message='Edge channels either needs to be an integer (number of channels) or a string with a percentage i.e. 5%')
		sys.exit()
	flag_chans=[]
	for i in range(nspw):
		flag_chans.append('%d:0~%d;%d~%d'%(i,value-1,(nchan-1)-(value-1),(nchan-1)))
	return ",".join(flag_chans)

def time_convert(mytime, myunit='s'):
	qa = casatools.quanta()
	if type(mytime) != list: 
		mytime=[mytime]
	myTimestr = []
	for i,time in enumerate(mytime):
		q1=qa.quantity(time,myunit)
		time1=qa.time(q1,form='ymd')[0]
		z=0
		if i!=0:
			if split_str(time1,'/',3)[0] == split_str(myTimestr[z],'/',3)[0]:
				time1 = split_str(time1,'/',3)[1]
			else:
				z=i
		myTimestr.append(time1)
	return myTimestr

def split_str(strng, sep, pos):
	strng = strng.split(sep)
	return sep.join(strng[:pos]), sep.join(strng[pos:])

def clip_bad_solutions(fid, table_array, caltable, solint, passmark):
	TOL=solint/2.01
	tb = casatools.table()
	tb.open(caltable)
	ant = tb.getcol('ANTENNA1')
	value = tb.getcol('FPARAM')
	flag = tb.getcol('FLAG')
	time_a = tb.getcol('TIME')
	time = np.unique(tb.getcol('TIME'))
	time = np.unique(np.floor(time/TOL).astype(int))*TOL
	field_id = tb.getcol('FIELD_ID')
	solns = np.sum(table_array[0],axis=0)
	for z in fid.keys():
		maxsoln = np.max(solns[fid[z][0]:fid[z][1]])
		for j in range(fid[z][0],fid[z][1]+1):
			result = np.isclose(time_a, time[j], atol=TOL,rtol=1e-10)
			if solns[j] < passmark*maxsoln:
				flag[:,0,(result)] = True
	
	tb.open(caltable, nomodify=False)
	tb.putcol('FLAG',np.multiply(flag, 1).astype(int))
	tb.close()

def interpolate_spw(table_array, passmark, caltable, solint):
	table_array=table_array[0]/table_array[1]
	interp_spw = np.where((table_array>=passmark)&(table_array!=1.0))
	tb = casatools.table()
	TOL = solint/2.01
	tb.open(caltable)
	ant = tb.getcol('ANTENNA1')
	value = tb.getcol('FPARAM')
	flag = tb.getcol('FLAG')
	time_a = tb.getcol('TIME')
	time = np.unique(tb.getcol('TIME'))
	time = np.unique(np.floor(time/TOL).astype(int))*TOL
	field_id = tb.getcol('FIELD_ID')
	tb.close()

	for j,i in enumerate(interp_spw[1]):
		k=interp_spw[0][j]
		result = np.isclose(time_a, time[i], atol =TOL,rtol=1e-10)
		for z in range(value.shape[0]):
			value_t=value[z,0,(result)&(ant==k)]
			flag_t=flag[z,0,(result)&(ant==k)]
			x=np.arange(0,8,1)
			yp = value_t[flag_t==False]
			xp = x[flag_t==False]
			inter = np.interp(x=x,xp=xp,fp=yp)
			value[z,0,(result)&(ant==k)] = inter
			flag[z,0,(result)&(ant==k)] = False

	nointerp_spw = np.where((table_array<passmark)&(table_array!=0.0))
	for j,i in enumerate(nointerp_spw[1]):
		k=nointerp_spw[0][j]
		result = np.isclose(time_a, time[i], atol=TOL,rtol=1e-10)
		flag[:,0,(result)&(ant==k)] = True

	tb.open(caltable, nomodify=False)
	tb.putcol('FPARAM',value)
	tb.putcol('FLAG',np.multiply(flag, 1).astype(int))
	tb.close()

def get_caltable_flag_stats(caltable, msinfo, solint, plotonly, plotfile):
	TOL = solint/(2.01)
	tb = casatools.table()
	qa = casatools.quanta()
	tb.open(caltable, nomodify=False)
	ant = tb.getcol('ANTENNA1')
	value = tb.getcol('FPARAM')
	flag = tb.getcol('FLAG')
	time_a = tb.getcol('TIME')
	time = np.unique(tb.getcol('TIME'))
	field_id = tb.getcol('FIELD_ID')
	tb.close()

	nant = len(msinfo['ANTENNAS']['anttoID'])

	time = np.unique(np.floor(time/TOL))*TOL
	numerator=np.zeros([nant,len(time)])
	denominator=np.zeros([nant,len(time)])
	fid = np.zeros([nant,len(time)])
	for k in range(nant):
		for j,i in enumerate(time):
			result = np.isclose(time_a, i, atol=TOL,rtol=1e-10)
			value_t=value[4,0,(result)&(ant==k)]
			flag_t=flag[4,0,(result)&(ant==k)]
			numerator[k][j] = len(value_t[flag_t==False].flatten())
			denominator[k][j] = len(value_t.flatten())
			fid[k][j] = np.average(field_id[(result)&(ant==k)]).astype(int)

	fid = np.average(fid,axis=0).astype(int)
	fid_t = {}
	for i in np.unique(fid):
		fid_t[msinfo['FIELD']['IDtofield'][str(i)]]=[np.min(np.where(fid==i)),np.max(np.where(fid==i))]
	flag_stats = [numerator,denominator]

	if plotfile!='':
		try:
			caltable = caltable.split('/')[-1]
		except:
			caltable=caltable
		Ants=np.arange(0,nant,1)
		Ant = []
		for i,j in enumerate(Ants):
			Ant.append(msinfo['ANTENNAS']['IDtoant'][str(j)])
		Time=time_convert(time.tolist(),'s')
		fig = plt.figure(1,figsize=(9,9))
		ax = fig.add_subplot(111)
		axes2 = ax.secondary_xaxis('top')  # mirror them
		axes3 = ax.secondary_yaxis('right') 
		#im = axes2.imshow(numerator/denominator,cmap='jet',zorder=-1000)
		im = ax.imshow(flag_stats[0]/flag_stats[1],cmap='jet')
		# We want to show all ticks...
		ax.set_xticks(np.arange(len(Time)))
		ax.set_yticks(np.arange(len(Ant)))
		# ... and label them with the respective list entries
		ax.set_xticklabels(Time)
		ax.set_yticklabels(Ant)
		axes2.set_xticks(np.arange(len(Time)))
		# ... and label them with the respective list entries
		axes2.set_xticklabels(np.sum(flag_stats[0],axis=0).astype(int).tolist())
		axes3.set_yticks(np.arange(len(Ant)))
		# ... and label them with the respective list entries
		axes3.set_yticklabels(np.sum(flag_stats[0],axis=1).astype(int).tolist())
		# Rotate the tick labels and set their alignment.
		plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
				 rotation_mode="anchor")
		bbox_props = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.9)
		for i in fid_t.keys():
			rect=patches.Rectangle((fid_t[i][0]-0.4,-0.4),(fid_t[i][1]-fid_t[i][0])+0.8,len(Ant)-0.2,linewidth=1,edgecolor='r',facecolor='none')
			ax.text(((fid_t[i][0]-0.4)+fid_t[i][1])/2., 0.5, '%s'%(i),
							   ha="center", va="center", color="k",size=12,bbox=bbox_props)
			ax.add_patch(rect)
		# Loop over data dimensions and create text annotations.
		for i in range(len(Ant)):
			for j in range(len(Time)):
				text = ax.text(j, i, '%d/%d'%(flag_stats[0][i, j],flag_stats[1][i,j]),
							   ha="center", va="center", color="w")
		ax.set_title("%s"%caltable)
		fig.savefig('%s'%plotfile)
		plt.close()

	if plotonly==True:
		return
	else:
		return flag_stats, fid_t

def auto_modify_sbdcal(msfile,caltable,solint,spw_pass, bad_soln_clip, plot):
	msinfo = get_ms_info(msfile)

	if solint[-1] == 's':
		solint=float(solint.split('s')[0])
	elif solint[-1] == 'm' or solint[-3:]=="min":
		solint=float(solint.split('m')[0])*60.
	#print(solint)

	os.system('cp -r %s %s_original'%(caltable,caltable))

	'''
	flag_stats, fid = get_caltable_flag_stats(caltable=caltable,
											  msinfo=msinfo,
											  solint=solint,
											  plotonly=False,
											  plotfile='test.pdf')
	
	clip_bad_solutions(fid=fid, 
					   table_array=flag_stats,
					   caltable=caltable, 
					   solint=solint, 
					   passmark=bad_soln_clip)
	'''

	os.system('cp -r %s %s.bpasscal'%(caltable,caltable))
	for i in range(20):
		fill_flagged_soln(caltable=caltable,fringecal=True)
	'''
	flag_stats, fid = get_caltable_flag_stats(caltable=caltable,
											  msinfo=msinfo,
											  solint=solint,
											  plotonly=False,
											  plotfile='test2.pdf')

	interpolate_spw(table_array=flag_stats, 
					passmark=spw_pass, 
					caltable=caltable, 
					solint=solint)


	get_caltable_flag_stats(caltable='eg078d.sbd',
							msinfo=msinfo,
							solint=solint,
							plotonly=True,
							plotfile='test3.pdf')

	fill_flagged_soln(caltable='eg078d.sbd', 
					  fringecal=True)

	get_caltable_flag_stats(caltable='eg078d.sbd',
							msinfo=msinfo,
							solint=solint,
							plotonly=True,
							plotfile='test4.pdf')
	'''

def scipy_clipper(data):
	x = np.arange(0,len(data),1)
	b, a = signal.butter(1, 0.25)
	y = signal.filtfilt(b,a, data)
	return y

def fit_autocorrelations(epoch, msinfo, calibrators,calc_auto='mean', renormalise='none', filter_RFI=True):
	'''
	This function will fit to the autocorrelations of each antenna on a spw by spw and pol basis
	'''
	func_name = inspect.stack()[0][3]

	msfile = '%s.ms'%epoch

	rmdirs(['%s.auto.bpass'%(epoch)])
	cb = casatools.calibrater()
	cb.open(msfile,False,False,False)
	cb.createcaltable('%s.auto.bpass'%(epoch), 'Complex', 'B Jones', False)
	cb.close()

	tb = casatools.table()
	nspw = msinfo['SPECTRAL_WINDOW']['nspws']
	npol = msinfo['SPECTRAL_WINDOW']['npol']
	pol_loc = []
	for j,i in enumerate(msinfo['SPECTRAL_WINDOW']['spw_pols']):
		if i[0] == i[1]:
			pol_loc.append(j)
	if npol > 2:
		npol = 2

	nants = len(msinfo['ANTENNAS']['anttoID'])
	nchan = msinfo['SPECTRAL_WINDOW']['nchan']

	tbnrows = len(calibrators)*nspw*nants
	TIME = np.empty(tbnrows)
	FIELD_ID = np.empty(tbnrows)
	SPECTRAL_WINDOW_ID = np.empty(tbnrows)
	ANTENNA1 = np.empty(tbnrows)
	ANTENNA2 = np.zeros(tbnrows)
	INTERVAL = np.zeros(tbnrows)
	OBSERVATION_ID = np.zeros(tbnrows)
	CPARAM = np.empty((npol,nchan,tbnrows),dtype=complex)
	PARAMERR = np.ones((npol,nchan,tbnrows))
	FLAG = np.zeros((npol,nchan,tbnrows))
	SNR =  np.ones((npol,nchan,tbnrows))
	WEIGHT = np.empty(tbnrows)

	runc=0
	tb.open(msfile)
	for h in range(len(calibrators)):
		subt=tb.query('ANTENNA1==ANTENNA2 and FIELD_ID==%s'%(calibrators[h]))
		t_cal = np.average(subt.getcol('TIME'))
		for j in range(nspw):
			x = np.arange(j*nchan,(j+1)*nchan,1)
			for i in range(nants):
				autocorrs = np.empty((npol,nchan),dtype=complex)
				for k,l in enumerate(pol_loc):
					try:
						subt = tb.query('ANTENNA1==%s and ANTENNA2==%s and FIELD_ID==%s and DATA_DESC_ID==%s'%(i,i,calibrators[h],j))
						flag = subt.getcol('FLAG')
						data = np.abs(subt.getcol('DATA'))
						data[flag==True] = np.nan
						if calc_auto == 'mean':
							data_median = np.sqrt(np.nanmean(data,axis=2)[l])
						elif calc_auto=='median':
							data_median = np.sqrt(np.nanmedian(data,axis=2)[l])
						else:
							sys.exit()
						polcol=['r','k']
						polmar=['o','^']
						if filter_RFI == True:
							try:
								quant=np.nanquantile(data_median,[0.25,0.75])
							except:
								quant=np.nanpercentile(data_median,[25.,75.])
							IQR = np.abs(quant[1]-quant[0])
							quant = quant[1]+0.8*IQR
							x_filter = x[(data_median<quant)|(data_median==np.nan)]
							data_median_filter = data_median[(data_median<quant)|(data_median==np.nan)]
							data_median_i = np.interp(x=x,xp=x_filter,fp=data_median_filter,left=data_median_filter[0],right=data_median_filter[-1])
							data_median_i = scipy_clipper(data_median_i)
						if renormalise.startswith('max'):
							if renormalise.split('max')[1] == '':
								data_median_i = data_median_i/np.max(data_median_i)
							else:
								try:
									chan_pc = (100.-float(renormalise.split('max')[1]))/200.
									chan1 = int(nchan*chan_pc)
									chan2 = int(nchan*(1-chan_pc))
									data_median_i = data_median_i/np.max(data_median_i[chan1:chan2])
								except:
									casalog.post(priority='SEVERE',origin=func_name,message='Needs to be in the format maxXX where XX is the percentage of the band to use (from the middle of the spw)')
									sys.exit()
						if renormalise.startswith('median'):
							if renormalise.split('median')[1] == '':
								data_median_i = data_median_i/np.median(data_median_i)
							else:
								try:
									chan_pc = (100.-float(renormalise.split('median')[1]))/200.
									chan1 = int(nchan*chan_pc)
									chan2 = int(nchan*(1-chan_pc))
									data_median_i = data_median_i/np.median(data_median_i[chan1:chan2])
								except:
									casalog.post(priority='SEVERE',origin=func_name,message='Needs to be in the format medianXX where XX is the percentage of the band to use (from the middle of the spw)')
									sys.exit()
						if renormalise.startswith('mean'):
							if renormalise.split('mean')[1] == '':
								data_median_i = data_median_i/np.mean(data_median_i)
							else:
								try:
									chan_pc = (100.-float(renormalise.split('mean')[1]))/200.
									chan1 = int(nchan*chan_pc)
									chan2 = int(nchan*(1-chan_pc))
									data_median_i = data_median_i/np.mean(data_median_i[chan1:chan2])
								except:
									casalog.post(priority='SEVERE',origin=func_name,message='Needs to be in the format meanXX where XX is the percentage of the band to use (from the middle of the spw)')
									sys.exit()
						for p in range(len(data_median_i)):
							autocorrs[k,p] = data_median_i[p]+0j	
					except:
						print('no data for antenna %s'%i)
						autocorrs[k,:] = 1 + 0j
						FLAG[k,:,runc] = 1	
				TIME[runc] = t_cal
				FIELD_ID[runc] = calibrators[h]
				SPECTRAL_WINDOW_ID[runc] = j
				ANTENNA1[runc] = i
				CPARAM[:,:,runc] = autocorrs
				runc+=1
	tb.close()

	tb.open('%s.auto.bpass'%(epoch),nomodify=False)
	tb.addrows(tbnrows)
	tb.putcol('TIME',TIME)
	tb.putcol('CPARAM',CPARAM)
	tb.putcol('PARAMERR',PARAMERR)
	tb.putcol('FLAG',FLAG)
	tb.putcol('SNR',SNR)
	tb.putcol('ANTENNA1',ANTENNA1)
	tb.putcol('SPECTRAL_WINDOW_ID',SPECTRAL_WINDOW_ID)
	tb.putcol('FIELD_ID',FIELD_ID)
	tb.close()

def clip_fitsfile(model,im,snr):
	try:
		from astropy.io import fits
	except:
		import pyfits as fits
		

	model_hdu = fits.open(model,mode='update')
	model_data = model_hdu['PRIMARY'].data
	im_hdu = fits.open(im)
	im_head = im_hdu['PRIMARY'].header
	print(im_hdu['PRIMARY'].data.squeeze().shape)
	rms = np.std(im_hdu['PRIMARY'].data.squeeze()[0:int(im_head['NAXIS1']/4.),0:int(im_head['NAXIS2']/4.)])
	im_hdu.close()
	model_data[model_data<float(snr)*rms] = 0
	model_hdu.flush()
	model_hdu.close()
 
def append_pbcor_info(vis, params):
	pb_data = load_json('%s/data/primary_beams.json'%params['global']['vlbipipe_path'])
	tb = casatools.table()

	tb.open('%s/SPECTRAL_WINDOW'%vis)
	bwidth = np.sum(tb.getcol('TOTAL_BANDWIDTH'))
	freq_range = [tb.getcol('CHAN_FREQ')[0][0],tb.getcol('CHAN_FREQ')[0][0]+bwidth]
	cfreq = np.average(freq_range)/1e9
	tb.close()

	freq_bands =  {'L':[1.35,1.75], 
				   'S':[2.15,2.35], 
				   'C':[3.9,7.9], 
				   'X':[8.0,8.8], 
				   'Ku':[12.0,15.4], 
				   'K':[21.7,24.1], 
				   'Q':[41.0,45.0]}

	band='Unk'
	for k in freq_bands.keys():
		if (cfreq<freq_bands[k][1])&(cfreq>freq_bands[k][0]):
			band=k


	tb.open('%s/ANTENNA'%vis,nomodify=False)
	name = tb.getcol('NAME')
	station = tb.getcol('STATION')

	dish_diam = []
	pb_params = []
	pb_model = []
	pb_source = []
	pb_squint = []
	pb_freq = []
	for i in range(len(name)):
		try:
			if (name[i] in pb_data.keys()):
				dish_diam.append(pb_data[name[i]][band]['diameter'])
				pb_params.append(",".join(np.array(pb_data[station[i]][band]['pb_params']).astype(str).tolist()))
				pb_squint.append(",".join(np.array(pb_data[station[i]][band]['pb_squint']).astype(str).tolist()))
				pb_freq.append(pb_data[name[i]][band]['pb_freq'])
				pb_model.append(pb_data[name[i]][band]['pb_model'])
				pb_source.append(pb_data[name[i]][band]['pb_source'])
			elif (station[i] in pb_data.keys()):
				dish_diam.append(pb_data[station[i]][band]['diameter'])
				pb_params.append(",".join(np.array(pb_data[station[i]][band]['pb_params']).astype(str).tolist()))
				pb_squint.append(",".join(np.array(pb_data[station[i]][band]['pb_squint']).astype(str).tolist()))
				pb_freq.append(pb_data[name[i]][band]['pb_freq'])
				pb_model.append(pb_data[station[i]][band]['pb_model'])
				pb_source.append(pb_data[station[i]][band]['pb_source'])
			else:
				dish_diam.append(0.0)
				pb_params.append('')
				pb_squint.append('')
				pb_freq.append(0.0)
				pb_model.append('NO_INFO')
				pb_source.append("NO_INFO")
		except:
			dish_diam.append(0.0)
			pb_params.append('')
			pb_squint.append('')
			pb_freq.append(0.0)
			pb_model.append('NO_INFO')
			pb_source.append("NO_INFO")

	add_cols = {'PB_MODEL':{'comment'         : 'pbmodel description',
							'dataManagerGroup': 'StandardStMan',
							'dataManagerType' : 'StandardStMan',
							'keywords'        : {'ARRAY_NAME': 'EVN'},
							'maxlen'          : 0,
							'option'          : 0,
							'valueType'       : 'string'},
				'PB_PARAM':{'comment'        : 'pb parameters',
							'dataManagerGroup': 'StandardStMan',
							'dataManagerType' : 'StandardStMan',
							'keywords'        : {},
							'maxlen'          : 0,
							'option'          : 0,
							'valueType'       : 'string'},
				'PB_SQUINT':{'comment'        : 'pb squint',
							'dataManagerGroup': 'StandardStMan',
							'dataManagerType' : 'StandardStMan',
							'keywords'        : {},
							'maxlen'          : 0,
							'option'          : 0,
							'valueType'       : 'string'},
				'PB_FREQ':  {'comment': 'Physical diameter of dish',
							'dataManagerGroup': 'StandardStMan',
							'dataManagerType': 'StandardStMan',
							'keywords': {},
							'maxlen': 0,
							'option': 0,
							'valueType': 'double'},
				'PB_SOURCE':{'comment'        : 'pb references',
							'dataManagerGroup': 'StandardStMan',
							'dataManagerType' : 'StandardStMan',
							'keywords'        : {},
							'maxlen'          : 0,
							'option'          : 0,
							'valueType'       : 'string'}
				}
	try:
		tb.addcols(add_cols)
	except:
		pass
	tb.putcol('DISH_DIAMETER',dish_diam)
	tb.putcol('PB_MODEL',pb_model)
	tb.putcol('PB_PARAM',pb_params)
	tb.putcol('PB_SOURCE',pb_source)
	tb.putcol('PB_FREQ',pb_freq)
	tb.putcol('PB_SQUINT',pb_squint)
	tb.close()

def pad_antennas(caltable='',ants=[],gain=False):
	tb = casatools.table()
	tb.open('%s'%caltable,nomodify=False)
	flg=tb.getcol('FLAG')
	ant=tb.getcol('ANTENNA1')
	if gain == True:
		g_col = 'CPARAM'
		gain=tb.getcol(g_col)
		repl_val = 1+0j
	else:
		g_col = 'FPARAM'
		gain=tb.getcol(g_col)
		repl_val = 0
	for i in ants:
		flg[:,:,(ant==i)] = 0
		gain[:,:,(ant==i)] = repl_val

	tb.putcol('FLAG', flg)
	tb.putcol(g_col, gain)

	tb.close()

def empty_f(x,mult=1.):
	return x*mult

def correct_phases(x,units):
	x = (x+ np.pi) % (2 * np.pi) - np.pi
	if units =='deg':
		return x*(180./np.pi)
	elif units =='rad':
		return x
	else:
		sys.exit()

def plotcaltable(caltable='',yaxis='',xaxis='',plotflag=False,msinfo='',figfile='temp.pdf'):
	func_name = inspect.stack()[0][3]
	tb=casatools.table()
	tb.open(caltable)
	if 'CPARAM' in tb.colnames():
		if yaxis in ['amp','phase']:
			gaincol = 'CPARAM'
		else:
			casalog.post(priority='SEVERE',origin=func_name,message='Wrong thing to plot for table')
			sys.exit()
	elif 'FPARAM' in tb.colnames():
		if yaxis in ['delay','phase','tsys','rate','disp','tec']:
			gaincol='FPARAM'
		else:
			casalog.post(priority='SEVERE',origin=func_name,message='Wrong thing to plot for table')
			sys.exit()
	else:
		casalog.post(priority='SEVERE',origin=func_name,message='Table cannot be plotted by this function')
		sys.exit()

	col_params = {
				'FPARAM':{
					'tsys':[0,empty_f,'Tsys (K)'],
					'delay':[1,empty_f,'Delay (nsec)'],
					'phase':[0,empty_f, 'Phase (deg)'],
					'rate':[2,empty_f, 'Rate (psec/sec)'],
					'disp':[3,empty_f, 'Disp. Delay (TEC)'],
					'tec' : [0,empty_f, 'TEC']
					},
				'CPARAM':{
					'amp':[0,np.real, 'Amplitude'],
					'phase':[1,np.angle, 'Phase (deg)']
					}
				}
	row_params = {'freq':['Frequency (GHz)'],
				  'time':['Time (hr since ']}

	ant = np.unique(tb.getcol('ANTENNA1'))
	spw = np.unique(tb.getcol('SPECTRAL_WINDOW_ID'))
	pol_cols = ['r','k','b','g']
	pol_symbols = ['o','^','*','+']
	pol_names=[]
	for i in msinfo['SPECTRAL_WINDOW']['spw_pols']:
		if i[0] == i[1]:
			pol_names.append(i)
	polrange = len(msinfo['SPECTRAL_WINDOW']['spw_pols'])

	casalog.post(priority='INFO',origin=func_name,message='Plotting %s vs %s from cal table - %s to file %s'%(yaxis,xaxis,caltable,figfile))

	with PdfPages('%s'%figfile) as pdf:

		if xaxis == 'time':
			time=tb.getcol('TIME')
			min_time = time.min()
			time = (time - min_time)/3600.
			t_range = [np.min(time),np.max(time)]
			for a in range(len(ant)):
				fig = plt.figure(figsize=(9,9))
				gs00 = gridspec.GridSpec(nrows=len(spw), ncols=1,hspace=0,figure=fig)
				ax1 = fig.add_subplot(gs00[:])
				ax1.set_ylabel('%s'%(col_params[gaincol][yaxis][2]),labelpad=35)
				ax1.set_xlabel('%s%s )'%(row_params[xaxis][0],time_convert(min_time)[0]),labelpad=25)
				ax1.set_title('%s against %s for antenna %s (%d)'%(yaxis, xaxis, msinfo['ANTENNAS']['IDtoant'][str(ant[a])],ant[a]))
				if len(spw) >1:
					ax1.set_xticks([],minor=True)
					ax1.set_xticks([])
					ax1.set_xticklabels([])
					ax1.set_yticks([],minor=True)
					ax1.set_yticks([])
					ax1.set_yticklabels([])
				for s in range(len(spw)):
					subt = tb.query('ANTENNA1==%s and SPECTRAL_WINDOW_ID==%s'%(ant[a],spw[s]))
					gain = subt.getcol(gaincol)
					flag = subt.getcol('FLAG')
					time = subt.getcol('TIME')
					min_time = time.min()
					time = (time - min_time)/3600.
					ax = fig.add_subplot(gs00[s])
					if yaxis == 'tec':
						polrange=1
						pol_names=['']
					for pol in range(polrange):
						#print(polrange)
						if gaincol == 'FPARAM':
							if yaxis == 'tsys':
								gain_t = col_params[gaincol][yaxis][1](gain[pol,col_params[gaincol][yaxis][0],:])
								flag_t = flag[pol,col_params[gaincol][yaxis][0],:]
								ax.plot(time[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(time[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
							else:
								if (gain.shape[0] == 2) | (gain.shape[0] == 1):
									increm = 1
									col_params[gaincol][yaxis][0] = 0
								else:
									increm = 4
								if yaxis=='tec':
									gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:],1./1.e16)
								elif yaxis=='disp':
									gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:],1./1.e3)
								else:
									gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:])
								flag_t = flag[col_params[gaincol][yaxis][0]+int(increm*pol),0,:]
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									#ax.set_ylim([-180,180])
								ax.plot(time[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								try:
									if np.max(gain_t[flag_t==0])-np.min(gain_t[flag_t==0])>1e5:
										ax.set_yscale('symlog')
								except:
									pass
								if plotflag == True:
									ax.plot(time[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
						elif gaincol == 'CPARAM':
							if gain.shape[1] == msinfo['SPECTRAL_WINDOW']['nchan']:
								gain_t = col_params[gaincol][yaxis][1](gain[pol,:,:]).flatten()
								flag_t = flag[pol,:,:].flatten()
								time_t = np.repeat(time,gain.shape[1])
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									ax.set_ylim([-180,180])
								ax.plot(time_t[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(time_t[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
							else:
								gain_t = col_params[gaincol][yaxis][1](gain[pol,0,:])
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									#ax.set_ylim([-180,180])
								flag_t = flag[pol,0,:]
								ax.plot(time[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(time[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
					ax.set_xlim(t_range)
					if s != len(spw)-1:
						ax.xaxis.set_ticklabels([])
					if s == 0:
						handles=[]
						for i in range(polrange):
							handles.append(mlines.Line2D([], [], color='%s'%pol_cols[i], marker='%s'%pol_symbols[i], linestyle='None', markersize=10, label='%s'%pol_names[i]))
						ax.legend(handles=handles)
					else:
						pass
				pdf.savefig(bbox_inches='tight')
				plt.close()
		elif xaxis == 'freq':
			for a in range(len(ant)):
				fig = plt.figure(figsize=(9,9))
				gs00 = gridspec.GridSpec(nrows=1, ncols=1,hspace=0,figure=fig)
				ax = fig.add_subplot(gs00[:])
				ax.set_ylabel('%s'%(col_params[gaincol][yaxis][2]),labelpad=35)
				ax.set_xlabel('%s'%(row_params[xaxis][0]),labelpad=25)
				ax.set_title('%s against %s for antenna %s (%d)'%(yaxis, xaxis, msinfo['ANTENNAS']['IDtoant'][str(ant[a])],ant[a]))
				for s in range(len(spw)):
					subt = tb.query('ANTENNA1==%s and SPECTRAL_WINDOW_ID==%s'%(ant[a],spw[s]))
					gain = subt.getcol(gaincol)
					#print(gain.shape)
					flag = subt.getcol('FLAG')
					if gain.shape[1] == 1:
						ch0 = msinfo['SPECTRAL_WINDOW']['freq_range'][0]
						spwbw = msinfo['SPECTRAL_WINDOW']['spw_bw']
						spw_average = (ch0+(spwbw/2.))+(s*spwbw)
						if len(spw) == 1:
							spw_average = (msinfo['SPECTRAL_WINDOW']['freq_range'][0]+msinfo['SPECTRAL_WINDOW']['freq_range'][1])/2.
						freqs = (np.ones(gain.shape[2])*(spw_average))/1.0e9
						if yaxis == 'tec':
							polrange=1
							pol_names=['']
						for pol in range(polrange):
							if gaincol == 'FPARAM':
								if yaxis == 'tsys':
									gain_t = col_params[gaincol][yaxis][1](gain[pol,col_params[gaincol][yaxis][0],:])
									flag_t = flag[pol,col_params[gaincol][yaxis][0],:]
									ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
									if plotflag == True:
										ax.plot(freqs[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
								else:
									if (gain.shape[0] == 2) | (gain.shape[0] == 1):
										increm = 1
										col_params[gaincol][yaxis][0] = 0
									else:
										increm = 4
									if yaxis=='tec':
										gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:],1./1.e16)
									elif yaxis=='disp':
										gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:],1./1.e3)
									else:
										gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:])
									flag_t = flag[col_params[gaincol][yaxis][0]+int(increm*pol),0,:]
									if yaxis == 'phase':
										gain_t = correct_phases(gain_t,units='deg')
										#ax.set_ylim([-180,180])
									ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
									try:
										if np.max(gain_t[flag_t==0])-np.min(gain_t[flag_t==0])>1e5:
											ax.set_yscale('symlog')
									except:
										pass
									if plotflag == True:
										ax.plot(freqs[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
							elif gaincol == 'CPARAM':
								gain_t = col_params[gaincol][yaxis][1](gain[pol,0,:])
								flag_t = flag[pol,0,:]
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									#ax.set_ylim([-180,180])
								ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(freqs[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
					elif gain.shape[1] == msinfo['SPECTRAL_WINDOW']['nchan']:
						ch0 = msinfo['SPECTRAL_WINDOW']['freq_range'][0]
						spwbw = msinfo['SPECTRAL_WINDOW']['spw_bw']
						chan_width = msinfo['SPECTRAL_WINDOW']['chan_width']
						freqs = np.arange(ch0+(s*spwbw),ch0+((s+1)*spwbw),chan_width)/1.0e9
						for pol in range(polrange):
							if gaincol == 'FPARAM':
								gain_t = col_params[gaincol][yaxis][1](gain[pol,col_params[gaincol][yaxis][0],:]).flatten()
								flag_t = flag[pol,col_params[gaincol][yaxis][0],:].flatten()
								freqs = np.repeat(freqs,gain_t.shape[2])
								ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(freqs[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
							elif gaincol == 'CPARAM':
								gain_t = col_params[gaincol][yaxis][1](gain[pol,:,:])
								flag_t = flag[pol,:,:].flatten()
								freqs_t = np.repeat(freqs,gain_t.shape[1])
								gain_t = gain_t.flatten()
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									#ax.set_ylim([-180,180])
								ax.plot(freqs_t[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(freqs_t[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
					if s == 0:
						handles=[]
						for i in range(polrange):
							handles.append(mlines.Line2D([], [], color='%s'%pol_cols[i], marker='%s'%pol_symbols[i], linestyle='None', markersize=10, label='%s'%pol_names[i]))
						ax.legend(handles=handles)
				ax.set_xlim(np.array(msinfo['SPECTRAL_WINDOW']['freq_range'])/1e9)
				pdf.savefig(bbox_inches='tight')
				plt.close()
		else:
			casalog.post(priority='SEVERE',origin=func_name,message='Table cannot be plotted by this function')
			sys.exit()

		tb.close()

def clip_model(model, im, snr):
	ia = casatools.image()
	ia.open(im)
	image_data = ia.getchunk().squeeze()
	max_pix = [np.where(image_data == image_data.max())[0][0],np.where(image_data == image_data.max())[1][0]]
	rest_beam = np.array([ia.restoringbeam()['major']['value'],ia.restoringbeam()['minor']['value']])
	incr = np.abs(ia.summary()['incr'][0:2])*60.*60.*(180./np.pi)
	pix_scale = np.floor((rest_beam/incr)/2.).astype(int)
	ia.close()
	if model != list:
		model = [model]
	for i in model:
		ia.open(i)
		model_data = ia.getchunk()
		if i.endswith('tt0'):
			model_data[model_data<0] = 0
		model_data[:max_pix[0]-pix_scale[1],:,:,:] = 0
		model_data[max_pix[0]+pix_scale[1]:,:,:,:] = 0
		model_data[:,:max_pix[1]-pix_scale[0],:,:] = 0
		model_data[:,max_pix[1]+pix_scale[0]:,:,:] = 0
		ia.putchunk(model_data)
		ia.close()

def make_tarfile(output_filename, source_dir):
	func_name = inspect.stack()[0][3]
	casalog.post(priority='INFO',origin=func_name,message='Tarring %s to form %s' % (source_dir,output_filename))
	with tarfile.open(output_filename, "w:gz") as tar:
		tar.add(source_dir, arcname=os.path.basename(source_dir))
  
def extract_tarfile(tar_file,cwd,delete_tar):
	func_name = inspect.stack()[0][3]
	tar = tarfile.open("%s"%tar_file)
	files = tar.getnames()
	for member in tar.getmembers():
		casalog.post(priority='INFO',origin=func_name,message='Extracting: %s' % member.name)
		tar.extract(member, path=cwd)
	if delete_tar == True:
		rmdirs(["%s"%tar_file])
	for i in range(len(files)):
		files[i] = cwd+files[i]
	return files

def get_target_files(target_dir='./',telescope='',project_code='',idifiles=[]):
	func_name = inspect.stack()[0][3]
	if idifiles == []:
		idifiles={}
		if telescope == 'EVN':
			check_arr = []
			files = []
			for i in os.listdir('%s'%target_dir):
				files.append(i)
				check_arr.append(i.startswith(project_code)&('IDI'in i))
			if np.all(check_arr) == True:
				tar=False
				unique_files = np.unique([i.split('.IDI')[0] for i in files])
				for k in unique_files:
					idifiles[k] = glob.glob('%s/%s*'%(target_dir,k))
			elif np.all(check_arr) == False:
				check_arr = []
				files = []
				for i in os.listdir('%s'%target_dir):
					files.append(i)
					check_arr.append(i.startswith(project_code)&(i.endswith('.tar.gz')))
				if np.all(check_arr) == True:
					tar=True
					unique_files = np.unique([i.split('.tar.gz')[0] for i in files])
					for k in unique_files:
						idifiles[k] = glob.glob('%s/%s*'%(target_dir,k))
				else:
					casalog.post(priority='SEVERE',origin=func_name,message='Target files must all be .tar.gz or .idi files')
					sys.exit()
			else:
				sys.exit()
		idifiles['tar'] = tar
		return idifiles
	else:
		return idifiles

def do_eb_fringefit(vis, caltable, field, solint, timerange, zerorates, niter, append, minsnr, msinfo, gaintable_dict, casa6):
	try:
		if casa6 == True:	
			from casampi.MPICommandClient import MPICommandClient
			from casampi import MPIEnvironment
			servers = MPIEnvironment.MPIEnvironment.mpi_server_rank_list()
			servers = cycle(servers)
		else:
			from mpi4casa.MPICommandClient import MPICommandClient
			from mpi4casa import MPIEnvironment
			servers = MPIEnvironment.MPIEnvironment.mpi_server_rank_list()
			servers = cycle(servers)

		client = MPICommandClient()
		client.set_log_mode('redirect')
		client.start_services()
		parallel=True
		cmd = []
	except:
		parallel=False
	refants = []
	err_array = []
	for i in msinfo['ANTENNAS']['anttoID'].keys():
		if i not in err_array:
			ant_temp = copy.deepcopy(list(msinfo['ANTENNAS']['IDtoant'].values()))
			ant_temp.remove(i)
			random.shuffle(ant_temp)
			ant_temp.insert(0,i)
			refants.append(ant_temp)

	fields = field.split(',')
	scans = []
	for i,j in enumerate(fields):
		f_id = msinfo['FIELD']['fieldtoID'][j]
		scans = scans + msinfo['SCANS'][str(f_id)]
	scans = np.sort(np.array(scans))
	print(scans)


	
	if parallel==True:
		cmd=[]
		for i in range(len(refants)):
			current_server = next(servers)
			append=True
			for j in range(len(scans)):
				#cmd0 = "import os; os.system('touch eb_ff_error.%s');"%(refants[i][0])
				cmd1 = "fringefit(vis='%s', caltable='%s_eb/%s_%s', field='%s', solint='%s', timerange='%s', refant='%s', zerorates=%s, niter=%d, append=%s, minsnr=%s, gaintable=%s, gainfield=%s, interp=%s, spwmap=%s, parang=%s, scan='%s');"%(vis, caltable, caltable, refants[i][0], field, solint, timerange, refants[i][0], zerorates, niter, append, minsnr, gaintable_dict['gaintable'],gaintable_dict['gainfield'],gaintable_dict['interp'],gaintable_dict['spwmap'],gaintable_dict['parang'],scans[j])
				cmd2 = "import os; os.system('touch %s_eb/eb_ff_complete%s')"%(caltable,refants[i][0])
				try:
					cmdId = client.push_command_request(command=cmd1+cmd2,block=False,target_server=[current_server])
					#cmdId = client.push_command_request(command=cmd1,parameters=params,block=False)
					#cmdId = client.push_command_request(command=cmd2,target_server=cmdId,block=False)
					cmd.append(cmdId[0])
				except:
					print('fringefit failed for refant - %s'%(refants[i][0]))
					pass
		resultList = client.get_command_response(cmd,block=True)

def generate_ff_full_table(msinfo):
	tb = casatools.table()
	t = np.array([])
	for i in msinfo['ANTENNAS']['IDtoant'].values():
		try:
			tb.open('eg078b.sbd_eb/eg078b.sbd_%s'%i)
			t2 = tb.getcol('TIME')
			print(len(t2))
			t = np.hstack([t,t2])
			tb.close()
		except:
			print('no ant %s'%i)
	times = np.unique(t)
	#for i in 
	
def progressbar(it, prefix="", size=60, file=sys.stdout):
	count = len(it)
	def show(j):
		x = int(size*j/count)
		file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
		file.flush()        
	show(0)
	for i, item in enumerate(it):
		yield item
		show(i+1)
	file.write("\n")
	file.flush()

def plot_tec_maps(msfile,tec_image,plotfile):
	try:
		from casatasks.private import simutil
	except:
		import simutil
	try:
		from astropy.io import fits
	except:
		import pyfits as fits
	try:
		from astropy import wcs
	except:
		sys.exit()

	tb = casatools.table()
	tb.open('%s/ANTENNA'%msfile)
	pos = tb.getcol('POSITION')
	u = simutil.simutil()
	lon = []
	lat = []
	for i in range(pos.shape[1]):
		longitude, latitude, altitude = u.xyz2long(pos[0][i], pos[1][i], pos[2][i], 'WGS84')
		lon.append(longitude*(180./np.pi))
		lat.append(latitude*(180./np.pi))
	if tec_image.endswith('.im'):
		rmfiles([tec_image+'.fits'])
		exportfits(imagename=tec_image,fitsimage=tec_image+'.fits')

	hdu = fits.open(tec_image+'.fits')
	wcs = wcs.WCS(hdu[0].header,naxis=2)

	nplo = 5
	hr = np.ones(nplo+1)
	hr[0] = 1/20.
	gs = gridspec.GridSpec(nrows=nplo+1,ncols=nplo,hspace=0.05,wspace=0.05,height_ratios=hr)
	data = hdu[0].data
	with PdfPages('%s'%plotfile) as pdf:
		nplo2=nplo**2
		time = hdu[0].header['CRVAL3']
		minmax = [np.min(data),np.max(data)]
		for j in range(np.ceil(data.shape[0]/nplo2).astype(int)):
			fig = plt.figure(1,figsize=(18,18))
			for i in range(nplo2):
				nco = j*nplo2 + i
				if nco < data.shape[0]:
					ax = fig.add_subplot(gs[i+nplo],projection=wcs)
					t = time_convert(time+(nco*hdu[0].header['CDELT3']))
					im = ax.imshow(data[nco],vmin=minmax[0],vmax=minmax[1],rasterized=True)
					ax.coords[0].set_ticks_visible(True)
					ax.coords[1].set_ticks_visible(True)
					ax.coords[0].set_axislabel(' ')
					ax.coords[1].set_axislabel(' ')
					if i%nplo!=0:
						ax.coords[1].set_ticklabel_visible(False)
					if i < nplo2-nplo:
						ax.coords[0].set_ticklabel_visible(False)
					ax.text(0.05,0.05,t[0],ha='left',va='bottom',transform=ax.transAxes,bbox=dict(boxstyle='round', fc="w", ec="k"))
					ax.scatter(lon,lat,transform=ax.get_transform('world'),c='w',ec='k',marker='o')
			ax = fig.add_subplot(gs[0,:])
			cb = plt.colorbar(mappable=im,cax=ax,orientation='horizontal')
			ax.xaxis.set_ticks_position('top')
			fig.text(0.5,0.915,r'TECU',ha='center',va='top')
			fig.text(0.085,0.5,r'Latitude (deg)',rotation=90,ha='left',va='center')
			fig.text(0.5,0.07,r'Longitude (deg)',ha='center',va='bottom')
			pdf.savefig(bbox_inches='tight')
			plt.close()

def interpgain(caltable,obsid,field,interp,extrapolate,fringecal=False):

	#
	#    interpgain
	# 
	#
	#    Interpolate missing gain solutions,
	#    overwriting the input caltable.  Optionally
	#    perform extrapolation.
	#    Christopher A. Hales (and now heavily modified by J. Radcliffe)
	#
	#    Version 2 (tested with CASA Version 5.7.0 & 6.1)
	#    Changelog - 08-09-2020 (Jack Radcliffe)
	#    * uses scipy interp1d to provide multiple interpolation methods
	#    * added support for fringe tables
	
	casalog.origin('interpgain')

	kind = interp
	if field == '*':
		selection0='OBSERVATION_ID=='+obsid
	else:
		selection0='OBSERVATION_ID=='+obsid+'&&FIELD_ID=='+field

	tb = casatools.table()
	tb.open(caltable,nomodify=False)
	
	subt=tb.query(selection0)
	spw=subt.getcol('SPECTRAL_WINDOW_ID')
	ant=subt.getcol('ANTENNA1')
	subt.done()
	
	if fringecal == False:
		gaincol = 'CPARAM'
	else:
		gaincol = 'FPARAM'
	for a in np.unique(ant):
		for s in np.unique(spw):
			selection=selection0+'&&ANTENNA1=='+str(a)+'&&SPECTRAL_WINDOW_ID=='+str(s)
			subt=tb.query(selection)
			timecol=subt.getcol('TIME')
			cparam=subt.getcol(gaincol)
			gainshape = cparam.shape
			flag=subt.getcol('FLAG')
			if fringecal == False:
				for p in range(gainshape[0]):
					for ch in range(gainshape[1]):
						if (np.sum(flag[p,ch])>0) & (np.sum(flag[p,ch])<=len(timecol)-2):
							# interpolate amp and phase separately

							amp   = np.abs(cparam[p,ch])
							phase = np.angle(cparam[p,ch])

							if extrapolate:
								bounds_error=False
								fill_value='extrapolate'
							else:
								bounds_error=False
								fill_value=np.nan
							f = interp1d(timecol[flag[p,ch]==False], amp[flag[p,ch]==False],kind=kind,bounds_error=bounds_error,fill_value=fill_value)
							amp[flag[p,ch]==True]   =  f(timecol[flag[p,ch]==True])
							f = interp1d(timecol[flag[p,ch]==False], np.unwrap(phase[flag[p,ch]==False]),kind=kind,bounds_error=bounds_error,fill_value=fill_value)
							phase[flag[p,ch]==True] = (f(timecol[flag[p,ch]==True]) + np.pi) % \
													 (2 * np.pi ) - np.pi
							if extrapolate:
								cparam[p,ch] = amp * np.exp(phase*1j)
								flag[p,ch]   = False
								flag[cparam==np.nan]=True
							else:
								indxMIN = np.where(flag[p,ch]==False)[0][0]
								indxMAX = np.where(flag[p,ch]==False)[0][-1]
								cparam[p,ch,indxMIN+1:indxMAX] = amp[indxMIN+1:indxMAX] * \
																np.exp(phase[indxMIN+1:indxMAX]*1j)
								flag[p,ch,indxMIN+1:indxMAX]   = False
								flag[cparam==np.nan]=True
			if fringecal == True:
				for p in range(gainshape[0]):
					for ch in range(gainshape[1]):
						if (np.sum(flag[p,ch])>0) & (np.sum(flag[p,ch])<=len(timecol)-2):
							gain   = cparam[p,ch]
							if extrapolate:
								bounds_error=False
								fill_value='extrapolate'
							else:
								bounds_error=False
								fill_value=np.nan
							f = interp1d(timecol[flag[p,ch]==False],gain[flag[p,ch]==False],kind=kind,bounds_error=bounds_error,fill_value=fill_value)
							gain[flag[p,ch]==True]   =  f(timecol[flag[p,ch]==True])

							if extrapolate:
								cparam[p,ch] = gain
								flag[p,ch]   = False
								flag[cparam==np.nan]=True
							else:
								indxMIN = np.where(flag[p,ch]==False)[0][0]
								indxMAX = np.where(flag[p,ch]==False)[0][-1]
								cparam[p,ch,indxMIN+1:indxMAX] = gain[indxMIN+1:indxMAX]
								flag[p,ch,indxMIN+1:indxMAX]   = False
								flag[cparam==np.nan]=True
			
			subt.putcol(gaincol,cparam)
			subt.putcol('FLAG',flag)
			subt.done()
	
	tb.done()

def apply_to_all(prefix,files,tar,params,casa6,parallel):
	func_name = inspect.stack()[0][3]

	cwd = params['global']['cwd']
	p_c=params['global']['project_code']
	i = prefix
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))
	gaintables = load_gaintables(params, casa6=casa6)
	target_dir = params['prepare_apply_all']['target_path']
	
	if tar == 'True':
		files = extract_tarfile(tar_file='%s'%files[0],cwd=target_dir,delete_tar=False)
	
	rmdirs(['%s/%s_presplit.ms'%(cwd,i),'%s/%s_presplit.ms.flagversions'%(cwd,i)])
	importfitsidi(fitsidifile=files,
		          vis='%s/%s_presplit.ms'%(params['global']['cwd'],i),
		          constobsid=params['import_fitsidi']["const_obs_id"],
		          scanreindexgap_s=params['import_fitsidi']["scan_gap"])
	if tar == 'True':
		rmfiles(files)
	
	msfile = '%s/%s_presplit.ms'%(params['global']['cwd'],i)

	if parallel == True:
		msfile2='%s/%s_presplit2.ms'%(params['global']['cwd'],i)
		os.system('mv %s %s'%(msfile,msfile2))
		partition(vis=msfile2,\
				  outputvis=msfile)
		rmdirs([msfile2])

	append_pbcor_info(vis='%s/%s_presplit.ms'%(cwd,i),params=params)
	
	if params['apriori_cal']["do_observatory_flg"] == True:
		if os.path.exists('%s/%s_casa.flags'%(cwd,params['global']['project_code'])):
			flagdata(vis=msfile,mode='list',inpfile='%s/%s_casa.flags'%(cwd,params['global']['project_code']))
	if params['init_flag']['flag_edge_chans']['run'] == True:

		ec=calc_edge_channels(value=params['init_flag']['flag_edge_chans']['edge_chan_flag'],
							  nspw=msinfo['SPECTRAL_WINDOW']['nspws'],
							  nchan=msinfo['SPECTRAL_WINDOW']['nchan'])

		flagdata(vis=msfile,
				 mode='manual',
				 spw=ec)

	if params['init_flag']['flag_autocorrs'] == True:
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
		quack_ints = params['init_flag']['quack_data']['quack_time']
		quack_mode = params['init_flag']['quack_data']['quack_mode']
		if type(quack_ints)==dict:
			for j in quack_ints.keys():
				if j == '*':
					flagdata(vis=msfile,
						     field=j,
						     mode='quack',
						     quackinterval=quack_ints[j],
						     quackmode=quack_mode)
		elif type(quack_ints)==float:
			flagdata(vis=msfile,
				     mode='quack',
				     quackinterval=quack_ints,
				     quackmode=quack_mode)

	if params['init_flag']['manual_flagging']['run'] == True:
		flagdata(vis=msfile,
				 mode='list',
				 inpfile='%s/%s'%(params['global']['cwd'],params['init_flag']['manual_flagging']['flag_file']))
	
	if params['apply_to_all']['pbcor']['run'] == True:
		pbcor_table = primary_beam_correction(msfile=msfile,prefix=i,params=params)
		gaintables = append_gaintable(gaintables,[pbcor_table,'',[],'nearest'])
		if params['apply_to_all']['pbcor']['backup_caltables'] == True:
			archive = tarfile.open("%s_caltables.tar"%p_c, "a")
			archive.add(pbcor_table, arcname=pbcor_table.split('/')[-1])
			archive.close()
	
	applycal(vis='%s/%s_presplit.ms'%(cwd,i),
			 field='*',
		     gaintable=gaintables['gaintable'],
			 gainfield=gaintables['gainfield'],
			 interp=gaintables['interp'],
			 spwmap=gaintables['spwmap'],
			 parang=gaintables['parang'])

	rmdirs(['%s/%s.ms'%(cwd,i),'%s/%s.ms.flagversions'%(cwd,i)])
	split(vis='%s/%s_presplit.ms'%(cwd,i),
			  outputvis='%s/%s.ms'%(cwd,i))
	rmdirs(['%s/%s_presplit.ms'%(cwd,i),'%s/%s_presplit.ms.flagversions'%(cwd,i)])

	

def apply_tar_output(prefix,params):
	i = prefix
	cwd = params['global']['cwd']
	msfile ='%s/%s.ms'%(cwd,i)
	if params['apply_to_all']['tar_output'] == True:
		make_tarfile(output_filename=msfile+'.tar.gz', source_dir='%s'%(msfile))
		rmdirs([msfile])
		if params['apply_to_all']['target_outpath'] !='':
			os.system('mv %s.tar.gz %s/'%(msfile,params['apply_to_all']['target_outpath']))
	else:
		if params['apply_to_all']['target_outpath'] !='':
			os.system('mv %s %s/'%(msfile,params['apply_to_all']['target_outpath']))

def angsep(ra1,dec1,ra2rad,dec2rad):
	qa = casatools.quanta()
	ra1rad=qa.convert(qa.quantity(ra1),'rad')['value']
	dec1rad=qa.convert(qa.quantity(dec1),'rad')['value']


	x=math.cos(ra1rad)*math.cos(dec1rad)*math.cos(ra2rad)*math.cos(dec2rad)
	y=math.sin(ra1rad)*math.cos(dec1rad)*math.sin(ra2rad)*math.cos(dec2rad)
	z=math.sin(dec1rad)*math.sin(dec2rad)

	rad=math.acos(x+y+z)

	# use Pythargoras approximation if rad < 1 arcsec
	if rad<0.000004848:
	    rad=math.sqrt((math.cos(dec1rad)*(ra1rad-ra2rad))**2+(dec1rad-dec2rad)**2)
	    
	# Angular separation
	return rad
	
def primary_beam_correction(msfile,prefix,params):
	func_name = inspect.stack()[0][3]
	import vex
	cb = casatools.calibrater()
	tb = casatools.table()
	qa = casatools.quanta()
	cwd = params['global']['cwd']

	#save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],prefix), array=get_ms_info('%s/%s_presplit.ms'%(params['global']['cwd'],prefix)), append=False)
	#msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],prefix))
	msinfo = get_ms_info('%s/%s_presplit.ms'%(params['global']['cwd'],prefix))
	nspw = msinfo['SPECTRAL_WINDOW']['nspws']
	npol = msinfo['SPECTRAL_WINDOW']['npol']
	nants = len(msinfo['ANTENNAS']['anttoID'])
	calibrators = np.unique(params['global']['fringe_finders']+params['global']['phase_calibrators'])

	tb.open(msfile+'/ANTENNA')
	ant_name = tb.getcol('NAME')
	pb_freq = tb.getcol('PB_FREQ')
	pb_model = tb.getcol('PB_MODEL')
	pb_params = list(tb.getcol('PB_PARAM'))
	pb_squint = list(tb.getcol('PB_SQUINT'))
	tb.close()
	pb_parameters = {}
	for i,j in enumerate(ant_name):
		pb_parameters[j] = {'freq':pb_freq[i],'model':pb_model[i],'params':np.array(pb_params[i].split(',')).astype(float),'squint':np.array(pb_squint[i].split(',')).astype(float)}

	if params['apply_to_all']['pbcor']['implementation'] == 'aproject':
		casalog.post(priority="SEVERE",origin=func_name,message='IDG not implemented just yet')
		sys.exit()
	elif params['apply_to_all']['pbcor']['implementation'] == 'aprojectdiff':
		casalog.post(priority="SEVERE",origin=func_name,message='IDG differential not implemented just yet')
		sys.exit()
	elif params['apply_to_all']['pbcor']['implementation'] == 'uvcorr':
		rmdirs(['%s.pbcor'%(prefix)])

		if params['apply_to_all']['pbcor']['vex_file'] == '':
			tbnrows = nspw*nants
			run_vex = False
		else:
			run_vex = True
			if os.path.exists(params['apply_to_all']['pbcor']['vex_file']) == False:
				casalog.post(origin=func_name,message='Vex file %s does not exist, please correct'%params['apply_to_all']['pbcor']['vex_file'],priority='SEVERE')
				sys.exit()
			else:
				vex_params = vex.Vex(params['apply_to_all']['pbcor']['vex_file'])
				scans = vex_params.sched
				source = vex_params.source
				re_sched = []
				for i in range(len(scans)):
					if scans[i]['source'] not in calibrators:
						re_sched.append(scans[i])
					else:
						pass
				tbnrows = nspw*nants*len(re_sched)

		targets=[]
		for i in msinfo['FIELD']['fieldtoID'].keys():
			if i not in calibrators:
				targets.append(i)
		tb = casatools.table()
		tb.open(msfile+'/FIELD')
		radec = tb.getcol('PHASE_DIR').T
		fie = tb.getcol('NAME')
		target = {}
		for i in targets:
			target[i] = radec[np.where(fie==i)[0][0]].squeeze()
		if len(target) == 1:
				radec_target = target[list(msinfo['FIELD']['IDtofield'].values())[0]]
		else:
			casalog.post(origin=func_name,message='Multiple targets .. it will mess up at the moment',priority='SEVERE')
			sys.exit()


		if run_vex == False:
			casalog.post(origin=func_name,message='Non-vex implementation not written yet',priority='SEVERE')
			IDtoant = msinfo['ANTENNAS']['IDtoant']
			offset = angsep(params['apply_to_all']['pbcor']['pointing_centre'][0],params['apply_to_all']['pbcor']['pointing_centre'][1],radec_target[0],radec_target[1])
			antenna_list = list(msinfo['ANTENNAS']['anttoID'].values())
			for k in range(msinfo['SPECTRAL_WINDOW']['nspws']):
				atten = []
				for j in antenna_list:
					obs_freq = msinfo['SPECTRAL_WINDOW']['freq_range'][0] + ((float(k)+1.0)-0.5)*msinfo['SPECTRAL_WINDOW']['spw_bw']
					attenuation = pb_model_uvcorr(parameters=pb_parameters[IDtoant[str(j)]]['params'],model=pb_parameters[IDtoant[str(j)]]['model'], obs_freq=obs_freq,angsep=offset)
					atten.append(attenuation)
				gencal(vis=msfile, caltable='%s/%s.pbcor'%(cwd,prefix), caltype='amp', antenna=','.join(str(e) for e in antenna_list), spw='%d'%k, parameter=atten)
		else:
			cb.open(msfile,False,False,False)
			cb.createcaltable('%s/%s.pbcor'%(cwd,prefix), 'Complex', 'G Jones', True)
			cb.close()
			TIME = np.empty(tbnrows)
			FIELD_ID = np.zeros(tbnrows)
			SPECTRAL_WINDOW_ID = np.empty(tbnrows)
			ANTENNA1 = np.empty(tbnrows)
			ANTENNA2 = np.zeros(tbnrows)
			INTERVAL = np.zeros(tbnrows)
			OBSERVATION_ID = np.zeros(tbnrows)
			CPARAM = np.empty((npol,1,tbnrows),dtype=complex)
			PARAMERR = np.ones((npol,1,tbnrows))
			FLAG = np.zeros((npol,1,tbnrows))
			SNR =  np.ones((npol,1,tbnrows))
			WEIGHT = np.empty(tbnrows)
			runc=0
			for i in range(len(re_sched)):
				## get scan lengths and times
				scan_l = []
				for j in re_sched[i]['scan'].keys():
					scan_l.append(re_sched[i]['scan'][j]['scan_sec'])
				scan_l = np.average(scan_l)/2./3600.
				time = (re_sched[i]['mjd_floor'] + (re_sched[i]['start_hr']+scan_l) / 24.)
				q = qa.quantity('%s d'%time)
				time = qa.convert(q,'s')['value']

				radec_teles = source[re_sched[i]['source']]
				offset = angsep(radec_teles['ra'],radec_teles['dec'],radec_target[0],radec_target[1])

				## get pb_params
				IDtoant = msinfo['ANTENNAS']['IDtoant']
				for j in list(msinfo['ANTENNAS']['anttoID'].values()):
					for k in range(msinfo['SPECTRAL_WINDOW']['nspws']):
						obs_freq = msinfo['SPECTRAL_WINDOW']['freq_range'][0] + ((k+1)-0.5)*msinfo['SPECTRAL_WINDOW']['spw_bw']
						attenuation = pb_model_uvcorr(parameters=pb_parameters[IDtoant[str(j)]]['params'],model=pb_parameters[IDtoant[str(j)]]['model'], obs_freq=obs_freq,angsep=offset)
						ANTENNA1[runc] = int(j)
						SPECTRAL_WINDOW_ID[runc] = int(k)
						TIME[runc] = time
						CPARAM[:,:,runc] = attenuation+0j
						runc+=1

			tb.open('%s/%s.pbcor'%(cwd,prefix),nomodify=False)
			tb.addrows(tbnrows)
			tb.putcol('TIME',TIME)
			tb.putcol('CPARAM',CPARAM)
			tb.putcol('PARAMERR',PARAMERR)
			tb.putcol('FLAG',FLAG)
			tb.putcol('SNR',SNR)
			tb.putcol('ANTENNA1',ANTENNA1)
			tb.putcol('ANTENNA2',ANTENNA2)
			tb.putcol('SPECTRAL_WINDOW_ID',SPECTRAL_WINDOW_ID)
			tb.putcol('FIELD_ID',FIELD_ID)
			tb.close()
	return '%s/%s.pbcor'%(cwd,prefix)

def pb_model_uvcorr(parameters,model,obs_freq,angsep):
	from scipy import constants as c
	if model == 'G':
		P = 1
		attenuation = P*np.e**(-1*((angsep**2)*4*np.log(2)*(parameters[0]**2))/((c.c/obs_freq)**2))
	elif model == 'B':
		print('hi')
	return np.sqrt(attenuation)

