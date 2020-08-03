import re, os, json, inspect, sys, copy, glob, tarfile
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
					 'error':'#SBATCH -o %s.sh.stdout.log\n#SBATCH -e %s.sh.stderr.log'%(hpc_opts['error'],hpc_opts['error'])
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
					 'error':'#PBS -o %s.sh.stdout.log\n#PBS -e %s.sh.stderr.log'%(hpc_opts['error'],hpc_opts['error'])
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
	for i in hpc_opts.keys():
		if i != 'job_manager':
			if hpc_opts[i] != '':
				if hpc_dict[hpc_opts['job_manager']][i] !='':
					hpc_header.append(hpc_dict[hpc_opts['job_manager']][i])


	with open('job_%s.%s'%(step,hpc_opts['job_manager']), 'w') as filehandle:
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
		commands[-1] = commands[-1]+'-strategy %s %s'%(params[step]['flag_strategy'],msfile)
	else:
		casalog.post(priority='SEVERE',origin=func_name,message='Error with writing commands.')
		sys.exit()

	with open('job_%s.%s'%(step,params['global']['job_manager']), 'a') as filehandle:
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
			commands.append('%s=$(sbatch %s job_%s.slurm)'%(j,depend,j))
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
	msinfo['FIELD'] = field
	#save_json('vp_fields_to_id.json',field)
	tb.close()
	## Get telescope_name
	tb.open('%s/OBSERVATION'%msfile)
	msinfo['TELE_NAME'] = tb.getcol('TELESCOPE_NAME')[0]
	tb.close()
	image_params = {}
	high_freq = spw['freq_range'][1]
	
	ms.open(msfile)
	for i in field['fieldtoID'].keys():
		ms.selecttaql('FIELD_ID==%s'%field['fieldtoID'][i])
		try:
			max_uv = ms.getdata('uvdist')['uvdist'].max()
			image_params[i] = ((speed_light/high_freq)/max_uv)*(180./np.pi)*(3.6e6/3.)
		except:
			pass
		ms.reset()
	ms.close()
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
	print('maxant', maxant)
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


	print('numflag', numflag)
	 
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

	msfile = '%s.ms'%epoch

	rmdirs(['%s.auto.bpass'%(epoch)])
	bandpass(vis=msfile,
			 caltable='%s.auto.bpass'%(epoch),
			 field=','.join(calibrators),
			 solint='inf',
			 antenna='',
			 spw='',
			 combine='scan',
			 solnorm=False,
			 refant='0,1,2,3,4,5,6,7,8,9,10',
			 fillgaps=0,
			 minsnr=10.)

	tb = casatools.table()
	nspw = msinfo['SPECTRAL_WINDOW']['nspws']
	npol = msinfo['SPECTRAL_WINDOW']['npol']
	if npol > 2:
		npol = 2
	nants = len(msinfo['ANTENNAS']['anttoID'])
	nchan = msinfo['SPECTRAL_WINDOW']['nchan']

	nrows=int(np.ceil(float(nants)/3.))
	gs = gridspec.GridSpec(nrows=nrows,ncols=3, width_ratios=np.ones(3), height_ratios=np.ones(nrows)/3.)
	
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
		#fig = plt.figure(1,figsize=(27,9))
		subt=tb.query('ANTENNA1==ANTENNA2 and FIELD_ID==%s'%(calibrators[h]))
		t_cal = np.average(subt.getcol('TIME'))
		for j in range(nspw):
			x = np.arange(j*nchan,(j+1)*nchan,1)
			for i in range(nants):
				#ax = fig.add_subplot(gs[i])
				autocorrs = np.empty((npol,nchan),dtype=complex)
				for k in range(npol):
					try:
						subt = tb.query('ANTENNA1==%s and ANTENNA2==%s and FIELD_ID==%s and DATA_DESC_ID==%s'%(i,i,calibrators[h],j))
						flag = subt.getcol('FLAG')
						data = np.abs(subt.getcol('DATA'))
						data[flag==True] = np.nan
						#print(data)
						if calc_auto == 'mean':
							data_median = np.sqrt(np.nanmean(data,axis=2)[k])
						elif calc_auto=='median':
							data_median = np.sqrt(np.nanmedian(data,axis=2)[k])
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
						if renormalise == 'max':
							data_median_i = data_median_i/np.max(data_median_i)
						if renormalise == 'median':
							data_median_i = data_median_i/np.median(data_median_i[10:25])
						#ax.scatter(x,data_median_i,c=polcol[k],marker=polmar[k])
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
				#ax2.scatter(x, scipy_clipper(data_median),c=polcol[k])
				#ax3.scatter(x, scipy_clipper(data_median)-data_median,c=polcol[k])

			
			#fig.savefig('%s_autocorr_bpass.png'%epoch,bbox_inches='tight')
			#smart_autocorr_clip(np.mean(np.abs(data),axis=2)[0])

	tb.close()
	tb.open('%s.auto.bpass'%(epoch),nomodify=False)
	tb.removerows(np.arange(0,tb.nrows(),1))
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
		if (name[i] in pb_data.keys()):
			dish_diam.append(pb_data[name[i]]['L']['diameter'])
			pb_params.append(",".join(np.array(pb_data[station[i]]['L']['pb_params']).astype(str).tolist()))
			pb_squint.append(",".join(np.array(pb_data[station[i]]['L']['pb_squint']).astype(str).tolist()))
			pb_freq.append(pb_data[name[i]]['L']['pb_freq'])
			pb_model.append(pb_data[name[i]]['L']['pb_model'])
			pb_source.append(pb_data[name[i]]['L']['pb_source'])
		elif (station[i] in pb_data.keys()):
			dish_diam.append(pb_data[station[i]]['L']['diameter'])
			pb_params.append(",".join(np.array(pb_data[station[i]]['L']['pb_params']).astype(str).tolist()))
			pb_squint.append(",".join(np.array(pb_data[station[i]]['L']['pb_squint']).astype(str).tolist()))
			pb_freq.append(pb_data[name[i]]['L']['pb_freq'])
			pb_model.append(pb_data[station[i]]['L']['pb_model'])
			pb_source.append(pb_data[station[i]]['L']['pb_source'])
		else:
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

def empty_f(x):
	return x

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
		if yaxis in ['delay','phase','tsys','rate']:
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
					'rate':[2,empty_f, 'Rate (psec/sec)']
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
					for pol in range(2):
						if gaincol == 'FPARAM':
							if yaxis == 'tsys':
								gain_t = col_params[gaincol][yaxis][1](gain[pol,col_params[gaincol][yaxis][0],:])
								flag_t = flag[pol,col_params[gaincol][yaxis][0],:]
								ax.plot(time[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
								if plotflag == True:
									ax.plot(time[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
							else:
								if gain.shape[0] == 2:
									increm = 1
									col_params[gaincol][yaxis][0] = 0
								else:
									increm = 4
								gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:])
								flag_t = flag[col_params[gaincol][yaxis][0]+int(increm*pol),0,:]
								if yaxis == 'phase':
									gain_t = correct_phases(gain_t,units='deg')
									#ax.set_ylim([-180,180])
								ax.plot(time[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
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
						for i in range(2):
							handles.append(mlines.Line2D([], [], color='%s'%pol_cols[i], marker='%s'%pol_symbols[i], linestyle='None', markersize=10, label='%s'%msinfo['SPECTRAL_WINDOW']['spw_pols'][i]))
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
					print(gain.shape)
					flag = subt.getcol('FLAG')
					if gain.shape[1] == 1:
						ch0 = msinfo['SPECTRAL_WINDOW']['freq_range'][0]
						spwbw = msinfo['SPECTRAL_WINDOW']['spw_bw']
						spw_average = (ch0+(spwbw/2.))+(s*spwbw)
						if len(spw) == 1:
							spw_average = (msinfo['SPECTRAL_WINDOW']['freq_range'][0]+msinfo['SPECTRAL_WINDOW']['freq_range'][1])/2.
						freqs = (np.ones(gain.shape[2])*(spw_average))/1.0e9
						for pol in range(2):
							if gaincol == 'FPARAM':
								if yaxis == 'tsys':
									gain_t = col_params[gaincol][yaxis][1](gain[pol,col_params[gaincol][yaxis][0],:])
									flag_t = flag[pol,col_params[gaincol][yaxis][0],:]
									ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
									if plotflag == True:
										ax.plot(freqs[flag_t==1],gain_t[flag_t==1],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True,mfc='none',alpha=0.2)
								else:
									if gain.shape[0] == 2:
										increm = 1
										col_params[gaincol][yaxis][0] = 0
									else:
										increm = 4
									gain_t = col_params[gaincol][yaxis][1](gain[col_params[gaincol][yaxis][0]+int(increm*pol),0,:])
									flag_t = flag[col_params[gaincol][yaxis][0]+int(increm*pol),0,:]
									if yaxis == 'phase':
										gain_t = correct_phases(gain_t,units='deg')
										#ax.set_ylim([-180,180])
									ax.plot(freqs[flag_t==0],gain_t[flag_t==0],'%s%s'%(pol_cols[pol],pol_symbols[pol]),rasterized=True)
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
						for pol in range(2):
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
						for i in range(2):
							handles.append(mlines.Line2D([], [], color='%s'%pol_cols[i], marker='%s'%pol_symbols[i], linestyle='None', markersize=10, label='%s'%msinfo['SPECTRAL_WINDOW']['spw_pols'][i]))
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
	with tarfile.open(output_filename, "w:gz") as tar:
		tar.add(source_dir, arcname=os.path.basename(source_dir))
  
def extract_tarfile(tar_file,cwd):
	tar = tarfile.open("%s"%tar_file)
	for member in tar.getmembers():
		print("Extracting %s" % member.name)
		tar.extract(member, path=cwd)

def get_target_files(target_dir='./',telescope='',project_code='',idifiles=[]):
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
					for k in files:
						tarf = tarfile.open("%s/%s"%(target_dir,k), "r:gz")
						idifiles[k.split('.tar.gz')[0]] = tarf.getnames()
						tarf.close()
				else:
					sys.exit()
			else:
				sys.exit()
		idifiles['tar'] = tar
		return idifiles
	else:
		return idifiles

