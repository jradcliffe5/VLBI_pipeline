import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections
from taskinit import casalog
import optparse

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

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
	tb.open(msfile+'/POLARIZATION')
	pol_code = tb.getcol('CORR_TYPE')
	pol=np.where(pol_code==pol)[0][0]
	newpol=np.where(pol_code==newpol)[0][0]
	t = tbtool()

	t.open(msfile, nomodify=False)
	ram_restrict = 100000
	ranger = list(range(0,t.nrows(),ram_restrict))
	
	for j in ranger:
		if j == ranger[-1]:
			ram_restrict = t.nrows()%ram_restrict
		gain = t.getcol('DATA',startrow=j, nrow=ram_restrict, rowincr=1)
		ant1 = t.getcol('ANTENNA1',startrow=j, nrow=ram_restrict, rowincr=1)
		ant2 = t.getcol('ANTENNA2',startrow=j, nrow=ram_restrict, rowincr=1)
		gain[newpol,:,((ant1==ant)|(ant2==ant))]=gain[pol,:,((ant1==ant)|(ant2==ant))]
		t.putcol('DATA',gain,startrow=j, nrow=ram_restrict, rowincr=1)
	t.close()

usage = "usage casa [options] -c copy_ms_pols.py <measurement set> <pol_copy_inputs>"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i:])

with open(args[1]) as f:
	content = f.readlines()
print(content)

msinfo=get_ms_info(args[0])

for i in content:
	if i.startswith('#') == False:
		ant=msinfo['ANTENNAS']['anttoID'][i.split(':')[0]]
		pol_o=pol_to_ID[i.split(':')[1].split('->')[0]]
		pol_n=pol_to_ID[i.split(':')[1].split('->')[1]]
		print(ant,pol_o,pol_n)
		copy_pols(msfile=args[0],antenna=ant,pol=pol_o,newpol=pol_n)

#append_tsys(args[0], args[1:])