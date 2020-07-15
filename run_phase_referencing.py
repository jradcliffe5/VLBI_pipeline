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

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))


refant = find_refants(params['global']['refant'],msinfo)

if params['phase_referencing']['select_calibrators'] == 'default':
		fields = params['global']['phase_calibrators']
else:
		fields = list(params['phase_referencing']['select_calibrators'])


cal_type = params['phase_referencing']["cal_type"]

print(len(fields))
for i in range(len(fields)):
	for j in range(len(cal_type[i])):
		caltable = '%s/%s-%s.%s%s'%(cwd,p_c,fields[i],cal_type[i][j],j)
		
		rmdirs([caltable])
		if cal_type[i][j] == 'f':
			fringefit(vis=msfile,
					  caltable=caltable,
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
				fill_flagged_soln(caltable=caltable,fringecal=True)
			if params['phase_referencing']['pass_ants'][i] != []:
				pass_ants = []
				for l in range(len(params['phase_referencing']['pass_ants'][i])):
					pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
				pad_antennas(caltable=caltable,ants=pass_ants,gain=False)
		elif cal_type[i][j] == 'p' or cal_type[i][j] == 'ap' or cal_type[i][j] == 'k' or cal_type[i][j] == 'a':
			if cal_type[i][j] == 'k':
				gaintype='K'
			else:
				gaintype='G'
			gaincal(vis=msfile,
					caltable=caltable,
					field=fields[i],
					solint=params['phase_referencing']['sol_interval'][i][j],
					calmode=cal_type[i][j],
					solnorm=True,
					refant=refant,
					gaintype=gaintype,
					combine=params['phase_referencing']['combine'][i][j],
					minsnr=params['phase_referencing']['min_snr'],
					gaintable=gaintables['gaintable'],
					gainfield=gaintables['gainfield'],
					interp=gaintables['interp'],
					spwmap=gaintables['spwmap'],
					parang=gaintables['parang'])
			if params['phase_referencing']["interp_flagged"][i][j] == True:
				fill_flagged_soln(caltable=caltable,fringecal=False)
			if params['phase_referencing']['pass_ants'][i] != []:
				pass_ants = []
				for l in range(len(params['phase_referencing']['pass_ants'][i])):
					pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
				pad_antennas(caltable=caltable,ants=pass_ants,gain=True)
		else:
			casalog.post(origin=filename, priority='SEVERE',message='Wrong sort of caltype - can only be F - fringefit, P - phase, AP - amp and phase, A - amp, or K - delay')
			sys.exit()
		if 'spw' in params['phase_referencing']['combine'][i][j]:
			spwmap = msinfo['SPECTRAL_WINDOW']['nspws']*[0]
		else:
			spwmap=[]
		gaintables = append_gaintable(gaintables,[caltable,'',spwmap,'linear'])
		applycal(vis=msfile,
			     field=fields[i],
			     gaintable=gaintables['gaintable'],
				 gainfield=gaintables['gainfield'],
				 interp=gaintables['interp'],
				 spwmap=gaintables['spwmap'],
				 parang=gaintables['parang'])
		if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
			applycal(vis=msfile,
			     field=fields[i+1],
			     gaintable=gaintables['gaintable'],
				 gainfield=gaintables['gainfield'],
				 interp=gaintables['interp'],
				 spwmap=gaintables['spwmap'],
				 parang=gaintables['parang'])
		
		if params['phase_referencing']["imager"] == 'wsclean':
			os.system('rm %s-%s%s-*'%(fields[i],cal_type[i][j],j))
			os.system('%s -name %s-%s%s -scale 0.0007asec -size 1024 1024 -weight natural -auto-threshold 0.1 -auto-mask 4 -niter 1000000 -mgain 0.8 -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i],cal_type[i][j],j,msinfo['FIELD']['fieldtoID'][fields[i]],msfile))
			clip_fitsfile(model='%s-%s%s-model.fits'%(fields[i],cal_type[i][j],j), 
				          im='%s-%s%s-image.fits'%(fields[i],cal_type[i][j],j),
				          snr=5.0)
			os.system('%s -name %s-%s%s -predict -weight natural -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i],cal_type[i][j],j,msinfo['FIELD']['fieldtoID'][fields[i]],msfile))
			if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
				os.system('%s -name %s-initmodel -scale 0.0007asec -size 1024 1024 -weight natural -auto-threshold 0.1 -auto-mask 4 -niter 1000000 -mgain 0.8 -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i+1],msinfo['FIELD']['fieldtoID'][fields[i+1]],msfile))


save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['phase_referencing'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
