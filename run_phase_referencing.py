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

if params['phase_referencing']['select_calibrators'] == 'default':
		fields = params['global']['phase_calibrators']
else:
		fields = params['phase_referencing']['select_calibrators']


cal_type = params['phase_referencing']["cal_type"]

for i in range(len(fields)):
	for j in range(len(cal_type[i])):
		if cal_type[i][j] == 'F':
			fringefit(vis=msfile,
					  caltable='%s/%s-%s.%s'%(cwd,p_c,fields[i],cal_type[i][j]),
					  field=fields[i],
					  solint=params['phase_referencing']['sol_interval'][i][j],
					  zerorates=False,
					  niter=params['phase_referencing']['fringe_niter'],
					  refant=refant,
					  combine=params['phase_referencing']['combine'][i][j],
					  minsnr=params['phase_referencing']['min_snr'],
					  gaintable=gaintables['gaintable'],
					  gainfield=gaintables['gainfield'],
					  interp=gaintables['interp'],
					  spwmap=gaintables['spwmap'],
					  parang=gaintables['parang'])
			if params['phase_referencing']["interp_flagged"][i][j] == True:
				fill_flagged_soln(caltable='%s/%s-%s.%s'%(cwd,p_c,fields[i],cal_type[i][j]),fringecal=True)
		elif cal_type[i][j] == 'P' or cal_type[i][j] == 'AP' or cal_type[i][j] == 'K' or cal_type[i][j] == 'A':
			gaincal()
			if params['phase_referencing']["interp_flagged"][i][j] == True:
				fill_flagged_soln(caltable='%s/%s-%s.%s'%(cwd,p_c,fields[i],cal_type[i][j]),fringecal=False)
		else:
			casalog.post(origin=filename, priority='SEVERE',message='Wrong sort of caltype - can only be F - fringefit, P - phase, AP - amp and phase, A - amp, or K - delay')
			sys.exit()
		

#fill_flagged_soln(caltable='%s/%s.mbd'%(cwd,p_c),fringecal=True)