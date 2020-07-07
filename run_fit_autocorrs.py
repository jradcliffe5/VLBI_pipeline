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


if params['fit_autocorrs']['select_calibrators'] == ['default']:
	fields=params['global']['fringe_finders']
else:
	fields=params['fit_autocorrs']['select_calibrators']

for i,j in enumerate(fields):
	fields[i] = str(msinfo['FIELD']['fieldtoID'][j])

fit_autocorrelations(epoch=params['global']['project_code'], msinfo=msinfo,calc_auto='median', calibrators=fields, renormalise='median', filter_RFI=True)

if params['fit_autocorrs']["interp_bad_solutions"] == True:
	fill_flagged_soln(caltable='%s/%s.auto.bpass'%(cwd,p_c),fringecal=False)

gaintables = append_gaintable(gaintables,['%s/%s.auto.bpass'%(cwd,p_c),'',[],'linear'])


save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['fit_autocorrs'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
