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

casalog.origin('vp_phase_referencing')

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
			if params['phase_referencing']['do_disp_delays'] == True:
				paramactive = [True,True,True]
			else:
				paramactive = [True,True,False]
			fringefit(vis=msfile,
					  caltable=caltable,
					  field=fields[i],
					  solint=params['phase_referencing']['sol_interval'][i][j],
					  zerorates=False,
					  niter=params['phase_referencing']['fringe_niter'],
					  refant=refant,
					  combine=params['phase_referencing']['combine'][i][j],
					  minsnr=params['phase_referencing']['min_snr'],
					  paramactive=paramactive,
					  gaintable=gaintables['gaintable'],
					  gainfield=gaintables['gainfield'],
					  interp=gaintables['interp'],
					  spwmap=gaintables['spwmap'],
					  parang=gaintables['parang'])
			if params['phase_referencing']["interp_flagged"][i][j] == True:
				interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
				interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)
			if params['phase_referencing']['pass_ants'][i] != []:
				pass_ants = []
				for l in range(len(params['phase_referencing']['pass_ants'][i])):
					pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
				pad_antennas(caltable=caltable,ants=pass_ants,gain=False)
			if casa6 == True:
				if 'spw' not in params['phase_referencing']['combine'][i][j]:
					xax = ['freq','time']
				else:
					xax = ['time']
				for k in ['delay','phase','rate']:
					for l in xax:
						plotcaltable(caltable=caltable,yaxis='%s'%k,xaxis='%s'%l,plotflag=True,msinfo=msinfo,figfile='%s-%s_vs_%s.pdf'%(caltable,k,l))

		elif cal_type[i][j] == 'p' or cal_type[i][j] == 'ap' or cal_type[i][j] == 'k' or cal_type[i][j] == 'a':
			if cal_type[i][j] == 'k':
				gaintype='K'
				calmode = 'ap'
			else:
				gaintype='G'
				calmode = cal_type[i][j]
			gaincal(vis=msfile,
					caltable=caltable,
					field=fields[i],
					solint=params['phase_referencing']['sol_interval'][i][j],
					calmode=calmode,
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
				if cal_type[i][j] == 'k':
					interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
					interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)
				else:
					interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=False)
					interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=False)
			if params['phase_referencing']['pass_ants'][i] != []:
				pass_ants = []
				for l in range(len(params['phase_referencing']['pass_ants'][i])):
					pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
				if cal_type[i][j] == 'k':
					pad_antennas(caltable=caltable,ants=pass_ants,gain=False)
				else: 
					pad_antennas(caltable=caltable,ants=pass_ants,gain=True)
			if casa6 == True:
				if 'spw' not in params['phase_referencing']['combine'][i][j]:
					xax = ['freq','time']
				else:
					xax = ['time']
				if cal_type[i][j] == 'ap':
					yax = ['amp','phase']
				elif cal_type[i][j] == 'k':
					yax = ['delay']
				else:
					yax = ['phase']
				for k in yax:
					for l in xax:
						plotcaltable(caltable=caltable,yaxis='%s'%k,xaxis='%s'%l,plotflag=True,msinfo=msinfo,figfile='%s-%s_vs_%s.pdf'%(caltable,k,l))
		else:
			casalog.post(origin=filename, priority='SEVERE',message='Wrong sort of caltype - can only be f - fringe fit, p - phase, ap - amp and phase, a - amp, or k - delay')
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
		
		## Establish image parameters
		imsize = [1024,1024]
		weight = 'natural'
		if msinfo['SPECTRAL_WINDOW']['bwidth']/msinfo['SPECTRAL_WINDOW']['cfreq'] > 0.1:
			deconvolver_tclean = ['mtmfs',2]
			mtmfs_wsclean = '-join-channels -channels-out %d -fit-spectral-pol 2 -deconvolution-channels %d'%(params['SPECTRAL_WINDOW']['nchan']/4,params['SPECTRAL_WINDOW']['nchan']/8)
		else:
			deconvolver_tclean = ['clarkstokes',1]
			mtmfs_wsclean = ''
		if params['phase_referencing']["imager"] == 'wsclean':
			rmfiles(['%s-%s%s-*'%(fields[i],cal_type[i][j],j)])
			os.system('%s -name %s-%s%s -scale %.3fmas -size %d %d -weight %s -auto-threshold 0.1 -auto-mask 4 -niter 1000000 -mgain 0.8 %s -field %s %s'%
				(";".join(params['global']["wsclean_command"]),
					fields[i],
					cal_type[i][j],
					j,
					msinfo["IMAGE_PARAMS"][fields[i]],
					imsize[0],
					imsize[1],
					weight,
					mtmfs_wsclean,
					msinfo['FIELD']['fieldtoID'][fields[i]],
					msfile))
			clip_fitsfile(model='%s-%s%s-model.fits'%(fields[i],cal_type[i][j],j), 
				          im='%s-%s%s-image.fits'%(fields[i],cal_type[i][j],j),
				          snr=10.0)
			os.system('%s -name %s-%s%s -predict -weight natural -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i],cal_type[i][j],j,msinfo['FIELD']['fieldtoID'][fields[i]],msfile))
			if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
				os.system('%s -name %s-initmodel -scale %.3fmas -size %d %d -weight %s -auto-threshold 0.1 -auto-mask 4 -niter 1000000 -mgain 0.8 %s -field %s %s'%
				(";".join(params['global']["wsclean_command"]),
					fields[i+1],
					msinfo["IMAGE_PARAMS"][fields[i+1]],
					imsize[0],
					imsize[1],
					weight,
					mtmfs_wsclean,
					msinfo['FIELD']['fieldtoID'][fields[i+1]],
					msfile))
				clip_fitsfile(model='%s-initmodel.fits'%(fields[i+1]), 
				          im='%s-initmodel.fits'%(fields[i+1]),
				          snr=10.0)
				os.system('%s -name %s-initmodel -predict -weight natural -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i+1],msinfo['FIELD']['fieldtoID'][fields[i+1]],msfile))
		if params['phase_referencing']['imager'] == 'tclean':
			delims = []
			for z in ['.psf','.image','.sumwt','.mask','.residual','.pb']:
				delims.append('%s-%s%s%s*'%(fields[i], cal_type[i][j], j,z))
			rmdirs(delims)
			if steps_run['make_mms'] == 1:
				parallel=True
			else:
				parallel = False
			tclean(vis=msfile,
				   imagename='%s-%s%s'%(fields[i], cal_type[i][j], j),
				   field='%s'%fields[i],
				   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i]]/1000.),
				   imsize=imsize,
				   deconvolver='%s'%deconvolver_tclean[0],
				   nterms=deconvolver_tclean[1],
				   niter = int(1e5),
				   weighting=weight,
				   nsigma=1.2,
				   usemask='auto-multithresh',
				   noisethreshold=4.0,
				   sidelobethreshold=1.0,
				   parallel=parallel
				   )
			if deconvolver_tclean[1]>1:
				model = []
				for k in range(deconvolver_tclean[1]):
					model.append('%s-%s%s.model.tt%s'%(fields[i], cal_type[i][j], j,k))
					image = '%s-%s%s.model.tt0'%(fields[i], cal_type[i][j], j)
			else:
				model = '%s-%s%s.model'%(fields[i], cal_type[i][j], j)
				image = '%s-%s%s.image'%(fields[i], cal_type[i][j], j)
			clip_model(model=model, 
				          im=image,
				          snr=10.0)
			ft(vis=msfile,
			   field='%s'%fields[i],
			   nterms=deconvolver_tclean[1],
			   model=model,
			   usescratch=True)
			if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
				delims = []
				for z in ['.psf','.image','.sumwt','.mask','.residual','.pb']:
					delims.append('%s-initmodel%s*'%(fields[i+1],z))
				rmdirs(delims)
				if params['phase_referencing']['pass_ants'][i] != []:
					antennas = ''
					for k in params['phase_referencing']['pass_ants'][i]:
						antennas = antennas+'!%s;'%k
					if antennas.endswith(';'):
						antennas = antennas[:-1]
				tclean(vis=msfile,
					   imagename='%s-initmodel'%(fields[i+1]),
					   field='%s'%fields[i+1],
					   antenna=antennas,
					   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i]]/1000.),
					   imsize=imsize,
					   deconvolver='%s'%deconvolver_tclean[0],
					   nterms=deconvolver_tclean[1],
					   niter = int(1e5),
					   weighting=weight,
					   nsigma=1.2,
					   usemask='auto-multithresh',
					   noisethreshold=4.0,
					   sidelobethreshold=1.0,
					   parallel=parallel
					   )
				if deconvolver_tclean[1]>1:
					model = []
					for k in range(deconvolver_tclean[1]):
						model.append('%s-initmodel.model.tt%s'%(fields[i+1],k))
						image = '%s-initmodel.image.tt0'%(fields[i+1])
				else:
					model = '%s-initmodel.model'%(fields[i+1])
					image = '%s-initmodel.image'%(fields[i+1])
				clip_model(model=model, 
				          im=image,
				          snr=10.0)
				ft(vis=msfile,
				   field='%s'%fields[i+1],
				   nterms=deconvolver_tclean[1],
				   model=model,
				   usescratch=True)



save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['phase_referencing'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
