import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections, optparse
import numpy as np

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

usage = "usage casa [options] -c / python check_antab.py <antab_file>"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i:])

comments = ('!','*')

try:
	file = open(args[0], 'r') 
except:
	casalog.post(origin=filename,priority='SEVERE',message='usage casa [options] -c / python check_antab.py <antab_file>')
	sys.exit()

data = []
data_head = {}
tsys = []
errorm=[]
ants = []
ncount = 0
for line in file:
	line = line.rstrip().lstrip()
	if line.endswith('/'):
		ncount+=1
		if line !="":
			data.append(line.replace("/",""))
		data = list(filter(None, data))
		for i in data:
			temp = i.split(' ')
			temp = list(filter(None, temp))
			if i.startswith('GAIN'):
				data_head['TELESCOPE'] = temp[1]
				ants.append([temp[1],ncount])
				for j in temp:
					if j.startswith('DPFU'):
						data_head['DPFU'] = np.array(j.split("DPFU=")[1].split(",")).astype(float)
					if j.startswith('POLY'):
						if j.rstrip().endswith(','):
							errorm.append('Delete errant , on POLY on antenna %s (line %d)'%(data_head['TELESCOPE'],ncount))
			elif i.startswith(('INDEX','TSYS')):
				pass
			elif i.startswith('POLY'):
				if i.rstrip().endswith(','):
					errorm.append('Delete errant , on POLY on antenna %s (line %d)'%(data_head['TELESCOPE'],ncount))
			else:
				tsys.append(temp[2:])
		tsys = np.array(tsys).astype(float)
		if np.all(tsys) == 1.0:
			data_head['TSYS'] = False
			### this is where to add in the DPFU comparisons
		else:
			data_head['TSYS'] = True
			if np.any(tsys==999.0)|np.any(tsys==999.9):
				print(data_head['TELESCOPE'])
				errant_lines = (ncount-tsys.shape[0]) + np.where(np.any((tsys==999.9)|(tsys==(999.0)), axis=1))[0]
				errorm.append('Change values of 999.9/999.9 on telescope %s to -999.9 (lines %s)'%(data_head['TELESCOPE'],', '.join(errant_lines.astype(str).tolist())))
		tsys=[]
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