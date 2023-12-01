import inspect, os, sys, json, re 
import copy
## Python 2 will need to adjust for casa 6
import collections, optparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *
from casavlbitools import key

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

try:
	# Python 2
	from StringIO import StringIO
except:
	# Python 3
	from io import StringIO

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

usage = " python / casa -c check_antab.py -a <antab_file> [-p plot tsys] [-r <ant> replace with nominal DPFU]"
parser = optparse.OptionParser(usage=usage)

parser.add_option("-a", "--antab", action="store", type="string", dest="antab_file")
parser.add_option("-r", "--replace", action="store", dest="replace", default=False)
parser.add_option("-p","--plot",dest="plot",action="store_true",default=False)
parser.add_option("-c",dest="c")

(options, args) = parser.parse_args()
options = vars(options)

if options['replace']!=False:
	replace_vals = options['replace'].split(',')
else:
	replace_vals = []


def map_index_to_tsys(tsys_pl,index_pl):
	indexes = []
	sorted_tsys = {}
	for i in index_pl.keys():
		temp = index_pl[i].replace("\'",'').replace(" ","").split('=')[1].strip()
		indexes = indexes + re.split(',|\|',temp)
	indexes = np.unique(indexes)
	idxes={}
	for i in tsys_pl.keys():
		temp = np.array(index_pl[i].replace("\'",'').replace(" ","").split('=')[1].strip().split(','))
		temp_idx = []
		temp_tsys = np.array([])
		for m,k in enumerate(indexes):
			try:
				res = [x for x in temp if re.search(k, x)][0]
				temp_idx.append(k)
				idx = np.where(res==temp)[0][0]
				if temp_tsys.size == 0:
					temp_tsys = tsys_pl[i][:,idx]
				else:
					temp_tsys = np.vstack([temp_tsys,tsys_pl[i][:,idx]])
			except:
				pass
		idxes[i] = np.array(temp_idx)
		sorted_tsys[i] = temp_tsys
	return sorted_tsys, indexes, idxes

def convert_time(time):
	conv_time = []
	for i in time:
		temp = i.split(',')
		if temp[1].count(":") == 2:
			conv_time.append((float(temp[0])*24)+float(temp[1].split(':')[0])+(float(temp[1].split(':')[1])/60.)+(float(temp[1].split(':')[2])/3600.))
		else:
			conv_time.append((float(temp[0])*24)+float(temp[1].split(':')[0])+(float(temp[1].split(':')[1])/60.)+(float(temp[1].split('.')[1])/3600.))
	return conv_time

comments = ('!','*')

try:
	file = open(options['antab_file'], 'r') 
except:
	casalog.post(origin=filename,priority='SEVERE',message=usage)
	sys.exit()

data = []
data_head = {}
replace_lines = {}
dpfurepl = {}
tsys_pl = {}
index_pl = {}
time_pl = {}
tsys = []
time = []
errorm=[]
ants = []
time_min_max = [1e9,-1e9,'']
ncount = 0
repl = 1
for line in file:
	line = line.rstrip().lstrip()
	if line.endswith('/'):
		ncount+=1
		if line !="":
			data.append(line.replace("/",""))
		data = list(filter(None, data))
		if (len(data)>1):
			if "GAIN" in data[0]:
				data = [" ".join(data)]
			else:
				pass
		if data !=[]:
			data[0] = data[0].replace(" = ","=").replace(', ',',')
		for i in data:
			temp = i.split(' ')
			temp = list(filter(None, temp))
			if i.startswith('GAIN'):
				data_head['TELESCOPE'] = temp[1].upper()
				ants.append([temp[1],ncount])
				for j in temp:
					if j.startswith('DPFU'):
						#print(j)
						data_head['DPFU'] = np.array(j.split("DPFU=")[1].split(",")).astype(float)
						if data_head['TELESCOPE'] in replace_vals:
							dpfurepl[data_head['TELESCOPE']] = ncount
					if j.startswith('POLY'):
						if j.rstrip().endswith(','):
							errorm.append('Delete errant , on POLY on antenna %s (line %d)'%(data_head['TELESCOPE'],ncount))
			elif i.startswith('INDEX'):
				index_pl[data_head['TELESCOPE']] = i
				if data_head['TELESCOPE'] in replace_vals:
					repl=ncount+1
			elif i.startswith('TSYS'):
				pass
			elif i.startswith('POLY'):
				if i.rstrip().endswith(','):
					errorm.append('Delete errant , on POLY on antenna %s (line %d)'%(data_head['TELESCOPE'],ncount))
			else:
				time.append(",".join(temp[:2]))
				tsys.append(temp[2:])
		tsys = np.array(tsys,dtype=object).astype(float) 
		if (tsys != [])&(options['plot']==True):
			tsys_pl[data_head['TELESCOPE']] = tsys
			conv_time = convert_time(time)
			time_pl[data_head['TELESCOPE']] = conv_time
			if np.max(conv_time) > time_min_max[1]:
				time_min_max[1] = np.max(conv_time)
			if np.min(conv_time) < time_min_max[0]:
				time_min_max[0] = np.min(conv_time)
				time_min_max[2] = time[np.where(conv_time==np.min(conv_time))[0][0]]

		if data_head['TELESCOPE'] in replace_vals:
			if tsys !=[]:
				replace_lines['%d'%repl] = np.ones(tsys.shape)
		if np.all(tsys) == 1.0:
			data_head['TSYS'] = False
			### this is where to add in the DPFU comparisons
		else:
			data_head['TSYS'] = True
			if np.any(tsys==999.0)|np.any(tsys==999.9):
				errant_lines = (ncount-tsys.shape[0]) + np.where(np.any((tsys==999.9)|(tsys==(999.0)), axis=1))[0]
				errorm.append('Change values of 999.9/999.9 on telescope %s to -999.9 (lines %s)'%(data_head['TELESCOPE'],', '.join(errant_lines.astype(str).tolist())))
		tsys=[]
		time = []
		data = []
	elif line.startswith(comments) == False:
		ncount+=1
		data.append(line)
	else:
		ncount+=1


## Check for duplicate ants
ants = np.array(ants).T
unq, unq_idx, unq_cnt = np.unique(ants[0], return_inverse=True, return_counts=True)
cnt_mask = unq_cnt > 1
dup_ids = unq[cnt_mask]

if dup_ids.tolist() != []:
	for i in dup_ids:
		errorm.append('Duplicate antenna entry, please check carefully and adjust - %s on lines %s'%(i,", ".join(ants[1][ants[0]==i].tolist())))

if errorm == []:
	casalog.post(origin=filename,priority='INFO',message='No errors found in the antab file - please proceed with your calibration')
	casalog.post(origin=filename,priority='INFO',message='If you find an error when using this file that has not been picked up here please raise an issue on the github')
else:
	casalog.post(origin=filename,priority='SEVERE',message='ERRORS FOUND - please correct the following in the antab file')
	for i in errorm:
		casalog.post(origin=filename,priority='WARN',message=i)


## Replace Tsys with bad values
if options['replace']!=False:
	replace_starts = []
	for i in replace_lines.keys():
		replace_starts.append(int(i))
	with open(options['antab_file'], "r") as input:
		with open("%s.edited"%options['antab_file'], "w") as output: 
			ncount=0
			ntsys=0
			replace_end=0
			shap=-1
			x=0
			for line in input:
				ncount+=1
				if ncount in replace_starts:
					if line.rstrip().lstrip().startswith('!') == True:
						for k in np.where(ncount in replace_starts)[0]:
							replace_starts[k]=ncount+1
							replace_lines['%s'%(ncount+1)] = replace_lines.pop('%s'%ncount)
						output.write(line)
					else:
						rpl = ncount
						ntsys=0
						replace_end = ncount+replace_lines['%s'%ncount].shape[0]
						line = line.rstrip().lstrip()
						line = " ".join(line.split(" ")[0:2]) + " " + " ".join(replace_lines['%s'%ncount][ntsys].astype(str))
						shap = replace_lines['%s'%rpl].shape[0]
						output.write(line+'\n')
				elif ntsys<shap-1:
					if line.rstrip().lstrip().startswith('!') == True:
						output.write(line)
					else:
						ntsys+=1
						line = line.rstrip().lstrip()
						line = " ".join(line.split(" ")[0:2]) + " " + " ".join(replace_lines['%s'%rpl][ntsys].astype(str))
						output.write(line+'\n')
				else:
					output.write(line)
	for i in dpfurepl.keys():
		try:
			dpfus = load_json('VLBI_pipeline/data/expected_dpfu.json')[i]['L'][-2:]
			casalog.post(origin=filename,priority='INFO',message='Please replace %s on line %s with nominal DPFUs (%s , %s)'%(i,dpfurepl[i],dpfus[0],dpfus[1]))
		except:
			casalog.post(origin=filename,priority='INFO',message='Please replace %s on line %s with nominal DPFUs'%(i,dpfurepl[i]))


if options['plot'] == True:
	figfile='%s_tsys.pdf'%options['antab_file']
	casalog.post(priority='INFO',origin=filename,message='Plotting Tsys values, will be saved to %s_tsys.pdf'%options['antab_file'])
	from matplotlib.backends.backend_pdf import PdfPages
	sorted_tsys, indexes, idxmap = map_index_to_tsys(tsys_pl=tsys_pl,index_pl=index_pl)
	print(idxmap)
	pols = []
	spw = []
	for i in indexes:
		pols.append(i[0])
		spw.append(int(i[1]))
	pols = np.unique(pols)
	spw = np.unique(spw)
	with PdfPages('%s'%figfile) as pdf:
		for a in sorted_tsys.keys():
			casalog.post(priority='INFO',origin=filename,message='Plotting Tsys for %s'%a)
			gs = gridspec.GridSpec(nrows=len(spw),ncols=1,hspace=0.0)
			fig = plt.figure(1)
			ax1 = fig.add_subplot(gs[:])
			ax1.set_ylabel('Tsys',labelpad=38)
			ax1.set_xlabel('Time (hr from %s)'%" ".join(time_min_max[2].split(',')),labelpad=28)
			ax1.set_title('Tsys against time for antenna %s'%(a))
			if len(spw) >1:
				ax1.set_xticks([],minor=True)
				ax1.set_xticks([])
				ax1.set_xticklabels([])
				ax1.set_yticks([],minor=True)
				ax1.set_yticks([])
				ax1.set_yticklabels([])
			tsys_vals = sorted_tsys[a]
			time_vals = time_pl[a] - time_min_max[0]
			marker_symbol = ['o','s']
			marker_color = ['k','r']
			for n,s in enumerate(spw):
				ax = fig.add_subplot(gs[s-1])
				for m,p in enumerate(pols):
					polar = '%s%s'%(p,s)
					try:
						idx = np.where(polar==idxmap[a])[0][0]
						ax.plot(time_vals[tsys_vals[idx]>0],tsys_vals[idx][tsys_vals[idx]>0],'%s%s'%(marker_symbol[m],marker_color[m]),label='%s'%p,rasterized=True)
					except:
						pass
				if n == 0:
					ax.legend()
				if n < len(spw)-1:
					ax.xaxis.set_ticklabels([])
				ax.set_xlim(0,time_min_max[1]-time_min_max[0])
			pdf.savefig(bbox_inches='tight')
			plt.close()


