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
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import casalog

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json',Odict=True)
gaintables = load_gaintables(params)

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

msinfo = get_ms_info(msfile)

refant = find_refants(params['global']['refant'],msinfo)


timerange=params['sub_band_delay']['time_range']
if timerange == ['','']:
	timerange=''
else:
	timerange='%s~%s'%(timerange[0],timerange[1])

print(gaintables['spwmap'])
rmdirs(['%s/%s.sbd'%(cwd,p_c)])
fringefit(vis=msfile,
		  caltable='%s/%s.sbd'%(cwd,p_c),
		  field=",".join(params['sub_band_delay']['calibrators']),
		  solint=params['sub_band_delay']['sol_interval'],
		  antenna='',
		  spw='',
		  timerange=timerange,
		  zerorates=True,
		  refant=refant,
		  minsnr=params['sub_band_delay']['min_snr'],
		  gaintable=gaintables['gaintable'],
		  gainfield=gaintables['gainfield'],
		  interp=gaintables['interp'],
		  spwmap=gaintables['spwmap'],
		  parang=gaintables['parang'])
fill_flagged_soln(caltable='%s/%s.sbd'%(cwd,p_c),fringecal=True)
