import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections
import optparse

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

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

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

pol_to_ID={'Undefined':0,
	'I':1, 
	'Q':2, 
	'U':3, 
	'V':4, 
	'RR':5, 
	'RL':6, 
	'LR':7, 
	'LL':8, 
	'XX':9, 
	'XY':10, 
	'YX':11, 
	'YY':12, 
	'RX':13, 
	'RY':14, 
	'LX':15, 
	'LY':16, 
	'XR':17, 
	'XL':18, 
	'YR':19, 
	'YL':20, 
	'PP':21, 
	'PQ':22, 
	'QP':23, 
	'QQ':24, 
	'RCircular':25, 
	'LCircular':26, 
	'Linear':27, 
	'Ptotal':28, 
	'Plinear':29, 
	'PFtotal':30, 
	'PFlinear':31, 
	'Pangle':32
}

def copy_pols(msfile,antenna,pol,newpol):
	tb=casatools.table()
	tb.open(msfile+'/POLARIZATION')
	pol_code = tb.getcol('CORR_TYPE')
	pol=np.where(pol_code==pol)[0][0]
	newpol=np.where(pol_code==newpol)[0][0]


	tb.open(msfile, nomodify=False)
	ram_restrict = 100000
	ranger = list(range(0,tb.nrows(),ram_restrict))
	
	for j in ranger:
		if j == ranger[-1]:
			ram_restrict = tb.nrows()%ram_restrict
		gain = tb.getcol('DATA',startrow=j, nrow=ram_restrict, rowincr=1)
		ant1 = tb.getcol('ANTENNA1',startrow=j, nrow=ram_restrict, rowincr=1)
		ant2 = tb.getcol('ANTENNA2',startrow=j, nrow=ram_restrict, rowincr=1)
		gain[newpol,:,((ant1==ant)|(ant2==ant))]=gain[pol,:,((ant1==ant)|(ant2==ant))]
		tb.putcol('DATA',gain,startrow=j, nrow=ram_restrict, rowincr=1)
	tb.close()

usage = "usage casa [options] -c copy_ms_pols.py <measurement set> <pol_copy_inputs>"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i:])

with open(args[1]) as f:
	content = f.readlines()


msinfo=get_ms_info(args[0])

for i in content:
	if i.startswith('#') == False:
		casalog.post(priority='INFO',origin=filename,message='Copying pol %s to %s on antenna %s'%(i.split(':')[1].split('->')[0].rstrip(),i.split(':')[1].split('->')[1].rstrip(),i.split(':')[0].rstrip()))
		ant=msinfo['ANTENNAS']['anttoID'][i.split(':')[0].rstrip()]
		pol_o=pol_to_ID[i.split(':')[1].split('->')[0].rstrip()]
		pol_n=pol_to_ID[i.split(':')[1].split('->')[1].rstrip()]
		casalog.post(priority='INFO',origin=filename,message='This corresponds to pol ID %s to %s on antenna %s'%(pol_o,pol_n,ant))
		copy_pols(msfile=args[0],antenna=ant,pol=pol_o,newpol=pol_n)

#append_tsys(args[0], args[1:])