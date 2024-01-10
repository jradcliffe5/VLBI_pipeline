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
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_json('vp_gaintables.json', Odict=True, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['phase_referencing'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

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

if steps_run['phase_referencing'] == 1:
	flagmanager(vis=msfile,mode='restore',versionname='vp_phase_referencing')
	clearcal(vis=msfile)
	if params['global']['use_initial_model'] != {}:
		for i in params['global']['use_initial_model'].keys():
			ft(vis='%s/%s.ms'%(params['global']['cwd'],params['global']['project_code']),
				field=i,
				nterms=len(params['global']['use_initial_model'][i]),
				model=params['global']['use_initial_model'][i],usescratch=True)
else:
	flagmanager(vis=msfile,mode='save',versionname='vp_phase_referencing')



applycal(vis=msfile,
		 field="",
	     gaintable=gaintables['gaintable'],
	     interp=gaintables['interp'],
	     gainfield=gaintables['gainfield'],
	     spwmap=gaintables['spwmap'],
	     parang=gaintables['parang'])


for i in range(len(fields)):
	flagdata(vis=msfile,
			mode='tfcrop',
			field=','.join(fields[i]),
			datacolumn='residual',
			combinescans=False,
			winsize=3,
			timecutoff=5.0,
			freqcutoff=5.0,
			maxnpieces=7,
			halfwin=1,
			extendflags=False,
			action='apply',
			display='',
			flagbackup=False)
	for j in range(len(cal_type[i])):
		if len(fields[i]) < 2:
			fields[i] = list(fields[i])
		caltable = '%s/%s-%s.%s%s'%(cwd,p_c,'_'.join(fields[i]),cal_type[i][j],j)
		rmdirs([caltable])
		if cal_type[i][j] == 'f':
			if params['phase_referencing']['do_disp_delays'] == True:
				paramactive = [True,True,True]
			else:
				paramactive = [True,True,False]
			if j > 0:
				delaywindow=[-20,20]
				ratewindow=[-20,20]
			else:
				delaywindow=[]
				ratewindow = []
			fringefit(vis=msfile,
					  caltable=caltable,
					  field=','.join(fields[i]),
					  solint=params['phase_referencing']['sol_interval'][i][j],
					  zerorates=False,
					  niter=params['phase_referencing']['fringe_niter'],
					  refant=refant,
					  combine=params['phase_referencing']['combine'][i][j],
					  minsnr=params['phase_referencing']['min_snr'],
					  paramactive=paramactive,
					  delaywindow=delaywindow,
					  ratewindow=ratewindow,
					  gaintable=gaintables['gaintable'],
					  gainfield=gaintables['gainfield'],
					  interp=gaintables['interp'],
					  spwmap=gaintables['spwmap'],
					  corrdepflags=True,
					  parang=gaintables['parang'])
			remove_flagged_scans(caltable)
			if i == 1:
				filter_smooth_delay(caltable,nsig=[2.5,2.])
				smoothcal(vis=msfile,tablein=caltable, smoothtime=6*60.0)
			if casa6 == True:
				if 'spw' not in params['phase_referencing']['combine'][i][j]:
					xax = ['freq','time']
				else:
					xax = ['time']
				for k in ['delay','phase']:
					try:
						for l in xax:
							plotcaltable(caltable=caltable,yaxis='%s'%k,xaxis='%s'%l,plotflag=True,msinfo=msinfo,figfile='%s-%s_vs_%s.pdf'%(caltable,k,l))
					except:
						pass
		elif cal_type[i][j] == 'p' or cal_type[i][j] == 'ap' or cal_type[i][j] == 'k' or cal_type[i][j] == 'a':
			if cal_type[i][j] == 'k':
				gaintype='K'
				calmode = 'ap'
			else:
				gaintype='G'
				calmode = cal_type[i][j]
			gaincal(vis=msfile,
					caltable=caltable,
					field=','.join(fields[i]),
					solint=params['phase_referencing']['sol_interval'][i][j],
					calmode=calmode,
					solnorm=True,
					normtype='median',
					refant=refant,
					gaintype=gaintype,
					corrdepflags=True,
					combine=params['phase_referencing']['combine'][i][j],
					minsnr=params['phase_referencing']['min_snr'],
					gaintable=gaintables['gaintable'],
					gainfield=gaintables['gainfield'],
					interp=gaintables['interp'],
					spwmap=gaintables['spwmap'],
					parang=gaintables['parang'])
			remove_flagged_scans(caltable)
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
		gt_r['phase_referencing'] = append_gaintable(gt_r['phase_referencing'],[caltable,'',spwmap,'linear'])

		applycal(vis=msfile,
			     field=','.join(fields[i]),
			     gaintable=gaintables['gaintable'],
				 gainfield=gaintables['gainfield'],
				 interp=gaintables['interp'],
				 spwmap=gaintables['spwmap'],
				 parang=gaintables['parang'],
				 calwt=params['phase_referencing']['cal_weights'])
		if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
			applycal(vis=msfile,
			     field=','.join(fields[i+1]),
			     gaintable=gaintables['gaintable'],
				 gainfield=gaintables['gainfield'],
				 interp=gaintables['interp'],
				 spwmap=gaintables['spwmap'],
				 parang=gaintables['parang'],
				 calwt=params['phase_referencing']['cal_weights'])
		save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
		
		## Establish image parameters
		imsize = [1024,1024]
		weight = 'natural'
		if msinfo['SPECTRAL_WINDOW']['bwidth']/msinfo['SPECTRAL_WINDOW']['cfreq'] > 0.1:
			deconvolver_tclean = ['mtmfs',2]
			mtmfs_wsclean = '-join-channels -channels-out %d -fit-spectral-pol 2 -deconvolution-channels %d'%(msinfo['SPECTRAL_WINDOW']['nchan']/4,msinfo['SPECTRAL_WINDOW']['nchan']/8)
			mtmfs=True
		else:
			deconvolver_tclean = ['clark',1]
			mtmfs_wsclean = ''
			mtmfs=False

		for k in range(len(fields[i])):
			if params['phase_referencing']["imager"] == 'wsclean':
				rmfiles(['%s-%s%s-*'%(fields[i][k],cal_type[i][j],j)])
				os.system('%s -name %s-%s%s -scale %.3fmas -size %d %d -weight %s -auto-threshold 0.5 -auto-mask 4 -niter 1000000 -mgain 0.8 %s -field %s %s'%
					(";".join(params['global']["wsclean_command"]),
						fields[i][k],
						cal_type[i][j],
						j,
						msinfo["IMAGE_PARAMS"][fields[i][k]],
						imsize[0],
						imsize[1],
						weight,
						mtmfs_wsclean,
						msinfo['FIELD']['fieldtoID'][fields[i][k]],
						msfile))
				clip_fitsfile(model='%s-%s%s-model.fits'%(fields[i][k],cal_type[i][j],j), 
					          im='%s-%s%s-image.fits'%(fields[i][k],cal_type[i][j],j),
					          snr=10.0)
				os.system('%s -name %s-%s%s -predict -weight natural -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i][k],cal_type[i][j],j,msinfo['FIELD']['fieldtoID'][fields[i][k]],msfile))
				if (j == (len(cal_type[i])-1)) and (i<(len(fields[i])-1)) and (k == (len(fields[i])-1)):
					for m in range(len(fields[i+1])):
						os.system('%s -name %s-initmodel -scale %.3fmas -size %d %d -weight %s -auto-threshold 0.1 -auto-mask 4 -niter 1000000 -mgain 0.8 %s -field %s %s'%
						(";".join(params['global']["wsclean_command"]),
							fields[i+1][m],
							msinfo["IMAGE_PARAMS"][fields[i+1][m]],
							imsize[0],
							imsize[1],
							weight,
							mtmfs_wsclean,
							msinfo['FIELD']['fieldtoID'][fields[i+1][m]],
							msfile))
						clip_fitsfile(model='%s-initmodel.fits'%(fields[i+1][m]), 
						          im='%s-initmodel.fits'%(fields[i+1][m]),
						          snr=10.0)
						os.system('%s -name %s-initmodel -predict -weight natural -field %s %s'%(";".join(params['global']["wsclean_command"]),fields[i+1][m],msinfo['FIELD']['fieldtoID'][fields[i+1][m]],msfile))
			if params['phase_referencing']['imager'] == 'tclean':
				delims = []
				for z in ['.psf','.image','.sumwt','.mask','.residual','.pb','.model']:
					delims.append('%s-%s%s%s'%(fields[i][k], cal_type[i][j], j,z))
				rmdirs(delims)
				if steps_run['make_mms'] == 1:
					parallel=False
				else:
					parallel = False
				if params['phase_referencing']['masking'] == 'peak':
					tclean(vis=msfile,
					   imagename='%s-%s%s'%(fields[i][k], cal_type[i][j], j),
					   field='%s'%fields[i][k],
					   stokes='pseudoI',
					   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i][k]]/1000.),
					   imsize=imsize,
					   deconvolver='%s'%deconvolver_tclean[0],
					   nterms=deconvolver_tclean[1],
					   niter = 0,
					   weighting=weight,
					   parallel=parallel
					   )
					imname='%s-%s%s.image'%(fields[i][k], cal_type[i][j], j)
					if mtmfs == True:
						imname = imname+'.tt0'
					peak = imstat(imagename=imname)
					peak = peak['maxpos'][:2]
					beam = imhead(imagename=imname)
					beam = np.ceil(1.2*(beam['restoringbeam']['major']['value']/7.2e3/(np.abs(beam['incr'][1])*(180/np.pi)))).astype(int)
					masking=['user','circle[[%spix, %spix], %spix]'%(peak[0],peak[1],beam),4.0,1.0]
					for z in ['.psf','.image','.sumwt','.mask','.residual','.pb','.model']:
						delims.append('%s-%s%s%s'%(fields[i][k], cal_type[i][j], j,z))
					rmdirs(delims)
				elif params['phase_referencing']['masking'] == 'auto':
					masking = ['auto-multithresh','',4.0,1.0]

				if params['phase_referencing']['thresholding'] == 'offset':
					field_id = msinfo["FIELD"]['fieldtoID'][fields[i][k]]
					tb = casatools.table()
					tb.open(msfile+'/FIELD')
					direction = tb.getcol('PHASE_DIR')[:,:,field_id].squeeze()
					tb.close()
					shift=2.0
					phasecenter = "J2000 %srad %srad"%(direction[0],direction[1]+((shift/3600.)*(np.pi/180.)))
					tclean(vis=msfile,
					   imagename='%s-%s%s_rms'%(fields[i][k], cal_type[i][j], j),
					   field='%s'%fields[i][k],
					   stokes='pseudoI',
					   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i][k]]/1000.),
					   imsize=imsize,
					   deconvolver='%s'%deconvolver_tclean[0],
					   phasecenter=phasecenter,
					   nterms=deconvolver_tclean[1],
					   niter = 0,
					   weighting=weight,
					   parallel=parallel
					   )
					imname='%s-%s%s_rms.image'%(fields[i][k], cal_type[i][j], j)
					if mtmfs == True:
						imname = imname+'.tt0'
					threshold = imstat(imagename=imname)['rms'][0] 
					nsigma=0.0
				else:
					nsigma=1.2
					threshold = 0.0
				tclean(vis=msfile,
					   imagename='%s-%s%s'%(fields[i][k], cal_type[i][j], j),
					   field='%s'%fields[i][k],
					   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i][k]]/1000.),
					   imsize=imsize,
					   stokes='pseudoI',
					   deconvolver='%s'%deconvolver_tclean[0],
					   nterms=deconvolver_tclean[1],
					   niter = int(1e5),
					   weighting=weight,
					   nsigma=nsigma,
					   threshold=threshold,
					   usemask=masking[0],
					   mask=masking[1],
					   noisethreshold=masking[2],
					   sidelobethreshold=masking[3],
					   parallel=parallel
					   )
				if deconvolver_tclean[1]>1:
					model = []
					for p in range(deconvolver_tclean[1]):
						model.append('%s-%s%s.model.tt%s'%(fields[i][k], cal_type[i][j], j, p))
						image = '%s-%s%s.model.tt0'%(fields[i][k], cal_type[i][j], j)
				else:
					model = '%s-%s%s.model'%(fields[i][k], cal_type[i][j], j)
					image = '%s-%s%s.image'%(fields[i][k], cal_type[i][j], j)
				if deconvolver_tclean[1]==1:
					clip_model(model=model, 
						          im=image,
						          snr=7.0)
				ft(vis=msfile,
				   field='%s'%fields[i][k],
				   nterms=deconvolver_tclean[1],
				   model=model,
				   usescratch=True)
				if (j == (len(cal_type[i])-1)) and (i<(len(fields)-1)):
					for m in range(len(fields[i+1])):
						delims = []
						for z in ['.psf','.image','.sumwt','.mask','.residual','.pb']:
							delims.append('%s-initmodel%s'%(fields[i+1][m],z))
						rmdirs(delims)
						if params['phase_referencing']['pass_ants'][i] != []:
							antennas = ''
							for l in params['phase_referencing']['pass_ants'][i]:
								antennas = antennas+'!%s;'%l
							if antennas.endswith(';'):
								antennas = antennas[:-1]
						if params['phase_referencing']['masking'] == 'peak':
							tclean(vis=msfile,
							       imagename='%s-initmodel'%(fields[i+1][m]),
								   field='%s'%fields[i+1][m],
					   		       stokes='pseudoI',
							       cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i+1][m]]/1000.),
							       imsize=imsize,
							       deconvolver='%s'%deconvolver_tclean[0],
							       nterms=deconvolver_tclean[1],
							       niter = 0,
							       weighting=weight,
							       parallel=parallel
							   )
							imname = '%s-initmodel.image'%(fields[i+1][m])
							if mtmfs == True:
								imname = imname+'.tt0'
							peak = imstat(imagename=imname)
							peak = peak['maxpos'][:2]
							beam = imhead(imagename=imname)
							beam = np.ceil(1.2*(beam['restoringbeam']['major']['value']/7.2e3/(np.abs(beam['incr'][1])*(180/np.pi)))).astype(int)
							masking=['user','circle[[%spix, %spix], %spix]'%(peak[0],peak[1],beam),4.0,1.0]
						elif params['phase_referencing']['masking'] == 'auto':
							masking = ['auto-multithresh','',4.0,1.0]
						if params['phase_referencing']['thresholding'] == 'offset':
							field_id = msinfo["FIELD"]['fieldtoID'][fields[i+1][m]]
							tb = casatools.table()
							tb.open(msfile+'/FIELD')
							direction = tb.getcol('PHASE_DIR')[:,:,field_id].squeeze()
							tb.close()
							shift=2.0
							phasecenter = "J2000 %srad %srad"%(direction[0],direction[1]+((shift/3600.)*(np.pi/180.)))
							tclean(vis=msfile,
							       imagename='%s-initmodel'%(fields[i+1][m]),
								   field='%s'%fields[i+1][m],
								   stokes='pseudoI',
							       cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i+1][m]]/1000.),
							       imsize=imsize,
							       phasecenter=phasecenter,
							       deconvolver='%s'%deconvolver_tclean[0],
							       nterms=deconvolver_tclean[1],
							       niter = 0,
							       weighting=weight,
							       parallel=parallel
							   )
							imname='%s-initmodel.image'%(fields[i+1][m])
							if mtmfs == True:
								imname = imname+'.tt0'
							threshold = imstat(imagename=imname)['rms'][0] 
							nsigma=0.0
						else:
							nsigma=1.2
							threshold = 0.0
						tclean(vis=msfile,
							   imagename='%s-initmodel'%(fields[i+1][m]),
							   field='%s'%fields[i+1][m],
							   stokes='pseudoI',
							   cell='%.6farcsec'%(msinfo["IMAGE_PARAMS"][fields[i+1][m]]/1000.),
							   imsize=imsize,
							   deconvolver='%s'%deconvolver_tclean[0],
							   nterms=deconvolver_tclean[1],
							   niter = int(1e5),
							   weighting=weight,
							   nsigma=nsigma,
							   threshold=threshold,
							   usemask=masking[0],
							   mask=masking[1],
							   noisethreshold=masking[2],
							   sidelobethreshold=masking[3],
							   parallel=parallel
							   )

						if deconvolver_tclean[1]>1:
							model = []
							for p in range(deconvolver_tclean[1]):
								model.append('%s-initmodel.model.tt%s'%(fields[i+1][m],p))
								image = '%s-initmodel.image.tt0'%(fields[i+1][m])
						else:
							model = '%s-initmodel.model'%(fields[i+1][m])
							image = '%s-initmodel.image'%(fields[i+1][m])
						if deconvolver_tclean[1]==1:
							clip_model(model=model, 
								          im=image,
								          snr=7.0)
						ft(vis=msfile,
						   field='%s'%fields[i+1][m],
						   nterms=deconvolver_tclean[1],
						   model=model,
						   usescratch=True)


#if params['phase_referencing']["interp_flagged"][i][j] == True:
#	if cal_type[i][j] == 'k':
#		interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
		#interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)
#	else:
#		interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=False)
		#interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=False)
#if params['phase_referencing']['pass_ants'][i] != []:
#	pass_ants = []
#	for l in range(len(params['phase_referencing']['pass_ants'][i])):
#		pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
#	if cal_type[i][j] == 'k':
#		pad_antennas(caltable=caltable,ants=pass_ants,gain=False)
#	else: 
#		pad_antennas(caltable=caltable,ants=pass_ants,gain=True)
#if params['phase_referencing']["interp_flagged"][i][j] == True:
#	interpgain(caltable=caltable,obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
#	#interpgain(caltable=caltable,obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)
#if params['phase_referencing']['pass_ants'][i] != []:
#	pass_ants = []
#	for l in range(len(params['phase_referencing']['pass_ants'][i])):
#		pass_ants.append(msinfo['ANTENNAS']['anttoID'][params['phase_referencing']['pass_ants'][i][l]])
#	pad_antennas(caltable=caltable,ants=pass_ants,gain=False)
save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['phase_referencing'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
