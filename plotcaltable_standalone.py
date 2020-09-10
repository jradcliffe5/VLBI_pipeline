import numpy as np
import matplotlib.pyplot as plt
import optparse, inspect, os, sys
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import gridspec
import json
import matplotlib.lines as mlines

try:
	# CASA 6
	import casatools
	from casatasks import *
	casalog.showconsole(False)
	casalog.origin('plotcaltable')
	casa6=True
except:
	casalog.post(priority='SEVERE',origin='ERROR',message='Can only work for CASA v6...')
	sys.exit()

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
		if yaxis in ['delay','phase','tsys','rate','disp']:
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
					'disp':[3,empty_f, 'Disp. Delay (milliTEC)']
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
					#print(gain.shape)
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

parser = optparse.OptionParser()
parser.add_option("-x","--xaxis", dest="xaxis", help="what to plot for xaxis (can be time/freq)")
parser.add_option("-y","--yaxis", dest="yaxis", help="what to plot for xaxis (can be amp/phase/delay/rate/disp)")
parser.add_option("-m","--msinfo", dest="msinfo", help="msinfo file from vlbi pipeline")
parser.add_option("-o","--outfile", dest="outfile", default=False)
parser.add_option("-c","--caltab", dest="caltable", help="caltable")
parser.add_option("-f","--flag",dest="flag",action="store_true",default=False)

(options, args) = parser.parse_args()
options = vars(options)
msinfo = load_json('%s'%options['msinfo'])

if options['outfile'] == False:
	figfile = '%s_%s_vs_%s.pdf'%(options['caltable'],options['yaxis'],options['xaxis'])
else:
	figfile = options['outfile']
plotcaltable(caltable=options['caltable'],yaxis=options['yaxis'],xaxis=options['xaxis'],plotflag=options['flag'],msinfo=msinfo,figfile=figfile)