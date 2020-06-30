import inspect, os, sys, json, re
from collections import OrderedDict

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

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

msinfo = get_ms_info(msfile)

refant = find_refants(params['global']['refant'],msinfo)


gaintab = []
for i in gaintables['gaintable']:
	print(i)
	if i.endswith('.sbd'):
		gaintab.append('%s.bpasscal'%i)
	else:
		gaintab.append(i)

applycal(vis=msfile,
		 field='',
	     gaintable=gaintables['gaintable'],
	     interp=gaintables['interp'],
	     gainfield=gaintables['gainfield'],
	     spwmap=gaintables['spwmap'],
	     parang=gaintables['parang'])

rmdirs(['%s/%s.bpass'%(cwd,p_c)])

if params['bandpass_cal']['same_as_sbd_cal'] == True:
	substep='sub_band_delay'
else:
	substep='bandpass_cal'

for i in range(len(params[substep]['select_calibrators'])):
	if i==0:
		append=False
	else:
		append=True

	if params[substep]['select_calibrators'][i] == ['default']:
		fields=",".join(params['global']['fringe_finders'])
	else:
		fields=",".join(params[substep]['select_calibrators'][i])
	bandpass(vis=msfile,
			 caltable='%s/%s.bpass'%(cwd,p_c),
			 field=fields,
			 solint=params['bandpass_cal']['sol_interval'],
			 antenna='',
			 spw='',
			 combine='field',
			 solnorm=True,
			 timerange=params[substep]['time_range'][i],
			 refant=refant,
			 append=append,
			 fillgaps=16,
			 minsnr=params['bandpass_cal']['min_snr'],
			 gaintable=gaintab,
			 gainfield=gaintables['gainfield'],
			 interp=gaintables['interp'],
			 spwmap=gaintables['spwmap'],
			 parang=gaintables['parang'])