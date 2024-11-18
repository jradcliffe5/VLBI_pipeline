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
casalog.origin('vp_fit_autocorrelations')

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['fit_autocorrs'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
p_c=params['global']['project_code']

if os.path.exists('%s/%s_msinfo.json'%(cwd,p_c))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(cwd,p_c), array=get_ms_info('%s/%s.ms'%(cwd,p_c)), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(cwd,p_c))

refant = find_refants(params['global']['refant'], msinfo)


if params['fit_autocorrs']['select_calibrators'] == ['default']:
	fields=params['global']['fringe_finders']
else:
	fields=params['fit_autocorrs']['select_calibrators']

for i,j in enumerate(fields):
	fields[i] = str(msinfo['FIELD']['fieldtoID'][j])

fit_autocorrelations(msfile='%s/%s.ms'%(cwd,p_c), caltable='%s/caltables/%s.auto.bpass'%(cwd,p_c), msinfo=msinfo, calc_auto='median', calibrators=fields, renormalise='median60', filter_RFI=True)

if params['fit_autocorrs']["interp_bad_solutions"] == True:
	#interpgain(caltable='%s/%s.auto.bpass'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=False,fringecal=False)
	interpgain(caltable='%s/caltables/%s.auto.bpass'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=False)

if casa6 == True:
	plotcaltable(caltable='%s/caltables/%s.auto.bpass'%(cwd,p_c),yaxis='amp',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s/plots/%s-autobpass_amp_vs_freq.pdf'%(cwd,p_c))
	plotcaltable(caltable='%s/caltables/%s.auto.bpass'%(cwd,p_c),yaxis='amp',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s/plots/%s-autobpass_amp_vs_time.pdf'%(cwd,p_c))

gaintables = append_gaintable(gaintables,['%s/caltables/%s.auto.bpass'%(cwd,p_c),'',[],'linear,linear'])
gt_r['fit_autocorrs'] = append_gaintable(gt_r['fit_autocorrs'],['%s/caltables/%s.auto.bpass'%(cwd,p_c),'',[],'linear,linear'])

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['fit_autocorrs'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
