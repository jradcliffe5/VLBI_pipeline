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
	from AIPS import AIPS, AIPSDisk
	from AIPSTask import AIPSTask, AIPSList
	from AIPSData import AIPSUVData, AIPSImage, AIPSCat
	from Wizardry.AIPSData import AIPSUVData as WizAIPSUVData
except:
	print('AIPS functions not found..exiting')
	sys.exit()

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
			print('Files matching with %s - deleting'% i)
			for j in files_to_die:
				if os.path.exists(j) == True:
					print('File %s found - deleting'% j)
					os.system('rm %s'%j)
				else:
					pass
		elif os.path.exists(i) == True:
			print('File %s found - deleting'% i)
			os.system('rm %s'%i)
		else:
			print('No file found - %s'% i)
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

def load_gaintables(params,casa6):
	cwd=params['global']['cwd']
	if os.path.exists('%s/vp_gaintables.json'%(cwd)) == False:
		gaintables=OrderedDict({})
		for a,b in zip(('gaintable','gainfield','spwmap','interp','parang'), ([],[],[],[],params['global']['do_parang'])):
			gaintables[a]=b
	else:
		gaintables=load_json('%s/vp_gaintables.json'%(cwd),Odict=True,casa6=casa6)
	return gaintables

def convert_solint(solint):
	if type(solint) == str:
		solint = [solint]
		sing_val = True
	else:
		sing_val = False
	for i in range(len(solint)):
		x = re.findall(r"[^\W\d_]+|\d+", solint[i])
		if x[-1] == 's':
			solint[i] = float(x[0])/60.
		elif x[-1] == 'm':
			solint[i] = float(x[0])
		elif x[-1] == 'h':
			solint[i] = float(x[0])*60.
		elif solint[i] == 'inf':
			solint[i] = 0
		else:
			print('wrong answer')
			sys.exit()
	if sing_val==True:
		return solint[0]
	else:
		return solint

def find_refants(pref_ant,msinfo):
	antennas = msinfo['ANTENNAS']['anttoID'].keys()
	refant=[]
	for i in pref_ant:
		if i in antennas:
			refant.append(i)
	return refant

def AIPS_get_tab(uvdata, table):
	# find the number of tables of a certain type
	ver = 0
	for i in range(len(uvdata.tables)):
		if table in uvdata.tables[i][1]:
			ver = uvdata.tables[i][0]
	print("HIGHEST TABLE OF TYPE", table, "is", ver)
	return ver

def AIPS_run_load_sort(pwd,data_prefix,delete,disk):
	## Load the data into AIPS
	fitld = AIPSTask('FITLD')
	fitld.datain = "%s/%s.ms.uvfits"%(pwd,data_prefix)
	fitld.outdisk = disk
	fitld.digicor = -1
	fitld.doconcat = 0
	fitld.outname = data_prefix
	fitld.ncount = 0
	fitld.go()

	#sort the data into time-baseline order
	uvdata = WizAIPSUVData(data_prefix,'UVDATA',disk,1)

	uvsrt = AIPSTask('UVSRT')
	uvsrt.indata = uvdata
	uvsrt.outdata = uvdata
	uvsrt.sort = 'TB'
	uvsrt.go()

	dqual = AIPSTask('DQUAL')
	dqual.indata = uvdata
	dqual.fqcenter = -1
	dqual.go()
	if delete == True:
		uvdata.zap()
	uvdata = AIPSUVData(data_prefix,'DQUAL',disk,1)

	indxr = AIPSTask('INDXR')
	#uvdata.zap_table('CL',1)
	indxr.indata = uvdata
	indxr.cparm[3] = 0.25
	indxr.go()
	if delete == True:
		uvdata.rename(data_prefix,'UVDATA',1)
	else:
		uvdata.rename(data_prefix,'UVDATA',2)
	return uvdata

def append_gaintable(gaintables,caltable_params):
	for i,j in enumerate(gaintables.keys()):
		if j != 'parang':
			gaintables[j].append(caltable_params[i])
	return gaintables