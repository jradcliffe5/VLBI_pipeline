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


timerange=params['sub_band_delay']['time_range']
if timerange == ['','']:
	timerange=''
else:
	timerange='%s~%s'%(timerange[0],timerange[1])

if params['sub_band_delay']['select_calibrators'] == ['']:
	fields=",".join(params['global']['fringe_finders'])
else:
	fields=",".join(params['sub_band_delay']['select_calibrators'])

rmdirs(['%s/%s.sbd'%(cwd,p_c)])
fringefit(vis=msfile,
		  caltable='%s/%s.sbd'%(cwd,p_c),
		  field=fields,
		  solint=params['sub_band_delay']['sol_interval'],
		  antenna='',
		  spw='',
		  timerange=timerange,
		  zerorates=True,
		  niter=100,
		  refant=refant,
		  minsnr=params['sub_band_delay']['min_snr'],
		  gaintable=gaintables['gaintable'],
		  gainfield=gaintables['gainfield'],
		  interp=gaintables['interp'],
		  spwmap=gaintables['spwmap'],
		  parang=gaintables['parang'])


if params['sub_band_delay']['modify_sbd']['run'] == True:
	rmdirs(['%s/%s.sbd.bpass'%(cwd,p_c)])
	auto_modify_sbdcal(msfile=msfile,
		               caltable='%s/%s.sbd'%(cwd,p_c),
		               solint=params['sub_band_delay']['sol_interval'],
		               spw_pass=params['sub_band_delay']['modify_sbd']['spw_passmark'],
		               bad_soln_clip=params['sub_band_delay']['modify_sbd']['clip_badtimes'],
		               plot=False)

gaintables = append_gaintable(gaintables,['%s/%s.sbd'%(cwd,p_c),'',[],'linear'])
'''
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['sub_band_delay'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
#fill_flagged_soln(caltable='%s/%s.sbd'%(cwd,p_c),fringecal=True)
'''