import re, os
import numpy as np
import json
import inspect
import sys
import collections
import copy
from scipy.interpolate import interp1d
import numpy
from collections import OrderedDict

try:
	# CASA 6
	import casatools
	from casatasks import *
	casalog.showconsole(True)
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import casalog

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

def json_load_byteified_dict(file_handle):
	return convert(_byteify(
		json.load(file_handle, object_hook=_byteify, object_pairs_hook=OrderedDict),
		ignore_dicts=True
	))

def json_loads_byteified_dict(json_text):
	return convert(_byteify(
		json.loads(json_text, object_hook=_byteify, object_pairs_hook=OrderedDict),
		ignore_dicts=True)
	)

def convert(data):
	try:
		basestring
	except:
		basestring=str
	if isinstance(data, basestring):
		return str(data)
	elif isinstance(data, collections.Mapping):
		try:
			return OrderedDict(map(convert, data.iteritems()))
		except:
			return OrderedDict(map(convert, data.items()))
	elif isinstance(data, collections.Iterable):
		return type(data)(map(convert, data))
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

def load_json(filename,Odict=False):
	if Odict==False:
		with open(filename, "r") as f:
			json_data = json_load_byteified(f)
		f.close()
	else:
		with open(filename, "r") as f:
			json_data = json_load_byteified_dict(f)
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
		if os.path.exists(i) == True:
			casalog.post(priority="INFO",origin=func_name,message='File %s found - deleting'% i)
			os.system('rm %s'%i)
	return

def rmdirs(dirs):
	func_name = inspect.stack()[0][3]
	for i in dirs:
		if os.path.exists(i) == True:
			casalog.post(priority="INFO",origin=func_name,message='Directory/table %s found - deleting'% i)
			os.system('rm -r %s'%i)
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
		if (i.startswith(project_code.lower())|i.startswith(project_code.upper()))&(('IDI' in i)|(i.endswith("idifile"))):
			fitsidifiles.append('%s/%s'%(idifilepath,i))
			casalog.post(priority="INFO",origin=func_name,message='FOUND - %s'% i)
	if fitsidifiles == []:
		for i in os.listdir(idifilepath):
			if ('IDI' in i)|i.endswith('idifiles'):
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
		msinfo = get_ms_info(msfile)
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
		msinfo = get_ms_info(msfile)
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
	tb.close()
	msinfo['SPECTRAL_WINDOW'] = spw
	## Get field information
	tb.open('%s/FIELD'%msfile)
	fields = tb.getcol('NAME')
	field = {}
	field['fieldtoID'] =dict(zip(fields, np.arange(0,len(fields),1)))
	field['IDtofield'] = dict(zip(np.arange(0,len(fields),1).astype(str),fields))
	msinfo['FIELD'] = field
	save_json('vp_fields_to_id.json',field)
	tb.close()
	## Get telescope_name
	tb.open('%s/OBSERVATION'%msfile)
	msinfo['TELE_NAME'] = tb.getcol('TELESCOPE_NAME')[0]
	tb.close()

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
						flg[:,:,(ant==k) & (dd==j)]=subflg
						#sol[:,:,(ant==k) & (dd==j)]=subsol
						gain[:,:,(ant==k) & (dd==j)]=subgain


		print('numflag', numflag)
		 
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
				t_temp=t[((ant==i)&(dd==j))][flg_temp==0] 
				gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 41 ,n_sigmas=nsig[0])
				gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 10 ,n_sigmas=nsig[1])
				#gain_uflg,detected_outliers = hampel_filter(np.array([t_temp,gain_uflg]), 5 ,n_sigmas=2.5)
				gain_uflg,jump = detect_jump_and_smooth(gain_uflg,jump_pc=jump_pc)
				if jump == False:
					gain_uflg = smooth_series(gain_uflg, 21)
				gain_uflg2[flg_temp==0] = gain_uflg
				gain_edit[k,0,((ant==i)&(dd==j))]= gain_uflg2

	tb.putcol('FPARAM',gain_edit)
	tb.flush()
	tb.close()

def smooth_series(y, box_pts):
	box = np.ones(box_pts)/box_pts
	#print(box_pts)
	y_smooth = np.convolve(y, box, mode='valid')
	y_smooth = np.hstack([np.ones(box_pts/2)*y_smooth[0],y_smooth])
	y_smooth = np.hstack([y_smooth,np.ones(box_pts/2)*y_smooth[-1]])
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
	return array, jump

def append_gaintable(gaintables,caltable_params):
	for i,j in enumerate(gaintables.keys()):
		if j != 'parang':
			gaintables[j].append(caltable_params[i])
	return gaintables

def load_gaintables(params):
	cwd=params['global']['cwd']
	if os.path.exists('%s/vp_gaintables.json'%(cwd)) == False:
		gaintables=OrderedDict({})
		for a,b in zip(('gaintable','gainfield','spwmap','interp','parang'), ([],[],[],[],params['global']['do_parang'])):
			gaintables[a]=b
	else:
		gaintables=load_json('%s/vp_gaintables.json'%(cwd),Odict=True)
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

