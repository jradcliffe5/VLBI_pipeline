import inspect, os, sys, json, re
from collections import OrderedDict

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

try:
	# CASA 6
	import casatools
	from casatasks import *
	from casatasks.private import tec_maps
	casalog.showconsole(True)
	casa6=True
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import casalog
	casa6=False
version=casatools.version()

casalog.origin('vp_apriori_cal')
inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_json('vp_gaintables.json', Odict=True, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['apriori_cal'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']
os.system('mkdir -p %s/plots/caltables'%cwd)

if steps_run['apriori_cal'] == 1:
	flagmanager(vis=msfile,mode='restore',versionname='vp_apriori_cal')
else:
	flagmanager(vis=msfile,mode='save',versionname='vp_apriori_cal')

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))


if params['apriori_cal']['correlator'] !='default':
	if re.match(params['apriori_cal']['correlator'], 'difx', re.IGNORECASE) == True:
		doaccor=True
	else:
		doaccor=False
else:
	if (msinfo['TELE_NAME'] == 'VLBA')|(msinfo['TELE_NAME'] == 'LBA'):
		doaccor=True
	else:
		doaccor=False

if doaccor==True:
	## DiFX correlator sampling corrections
	casalog.post(origin=filename,message='Applying DiFX correlator sampling correction (accor)',priority='INFO')
	rmdirs(['%s/caltables/%s.accor'%(cwd,p_c)])
	accor(vis=msfile,
	      caltable='%s/caltables/%s.accor'%(cwd,p_c),
	      solint=params['apriori_cal']['accor_options']['solint'])
	gaintables = append_gaintable(gaintables,['%s/caltables/%s.accor'%(cwd,p_c),'',[],params['apriori_cal']['accor_options']['interp']])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/caltables/%s.accor'%(cwd,p_c),'',[],params['apriori_cal']['accor_options']['interp']])
	if params['apriori_cal']['accor_options']['smooth'] == True:
		casalog.post(origin=filename,message='Smoothing accor solutions (smoothtime=%s)'%params['apriori_cal']['accor_options']['smoothtime'],priority='INFO')
		smoothcal(vis=msfile,
		          tablein='%s/caltables/%s.accor'%(cwd,p_c),
		          caltable='%s/caltables/%s.accor'%(cwd,p_c),
			      smoothtime=params['apriori_cal']['accor_options']['smoothtime'])

### Run prior-cals
if params['apriori_cal']["do_observatory_flg"] == True:
	if os.path.exists('%s/%s_casa.flags'%(cwd,p_c)):
		casalog.post(origin=filename,message='Applying observatory flags from %s/%s_casa.flags'%(cwd,p_c),priority='INFO')
		if steps_run['apriori_cal'] == 1:
			flagmanager(vis=msfile,mode='restore',versionname='original_flags')
		else:
			flagmanager(vis=msfile,mode='save',versionname='original_flags')
		flagdata(vis=msfile,mode='list',inpfile='%s/%s_casa.flags'%(cwd,p_c))
	else:
		casalog.post(origin=filename,message='Observatory flag file %s/%s_casa.flags not found ... skipping'%(cwd,p_c),priority='WARN')

casalog.post(origin=filename,message='Generating Tsys calibration table',priority='INFO')
rmdirs(['%s/%s.tsys'%(cwd,p_c)])
gencal(vis=msfile,\
       caltype='tsys',\
       spw='',\
       antenna='',\
       caltable='%s/caltables/%s.tsys'%(cwd,p_c),\
       uniform=False)

if casa6 == True:
	plotcaltable(caltable='%s/caltables/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s/plots/caltables/%s-tsys_vs_time.pdf'%(cwd,p_c))
	plotcaltable(caltable='%s/caltables/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s/plots/caltables/%s-tsys_vs_freq.pdf'%(cwd,p_c))

gaintables = append_gaintable(gaintables,['%s/caltables/%s.tsys'%(cwd,p_c),'',[],params['apriori_cal']['tsys_options']['interp']])
gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/caltables/%s.tsys'%(cwd,p_c),'',[],params['apriori_cal']['tsys_options']['interp']])

if params['apriori_cal']['tsys_options']['interp_flags'] == True:
	casalog.post(origin=filename,message='Interpolating flagged Tsys solutions',priority='INFO')
	interpgain(caltable='%s/caltables/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
	interpgain(caltable='%s/caltables/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)

if params['apriori_cal']['tsys_options']['algorithm'] != "":
	casalog.post(origin=filename,message='Post-processing Tsys table with algorithm(s): %s'%params['apriori_cal']['tsys_options']['algorithm'],priority='INFO')
	rmdirs(['%s/caltables/%s.tsys_original'%(cwd,p_c)])
	os.system('cp -r %s/caltables/%s.tsys %s/caltables/%s.tsys_original'%(cwd,p_c,cwd,p_c))
	if "smooth" in params['apriori_cal']['tsys_options']['algorithm']:
		casalog.post(origin=filename,message='Smoothing Tsys table (smoothtype=%s, smoothtime=%s)'%(params['apriori_cal']['tsys_options']["smooth_type"],params['apriori_cal']['tsys_options']["smooth_time"]),priority='INFO')
		smoothcal(vis=msfile,
				  tablein='%s/caltables/%s.tsys'%(cwd,p_c),
				  smoothtype=params['apriori_cal']['tsys_options']["smooth_type"],
				  smoothtime=params['apriori_cal']['tsys_options']["smooth_time"])
	if "filt" in params['apriori_cal']['tsys_options']['algorithm']:
		casalog.post(origin=filename,message='Filtering Tsys outliers (nsig=%s, jump_pc=%s)'%(params['apriori_cal']['tsys_options']["filt_outlierSN"],params['apriori_cal']['tsys_options']["filt_jump_pc"]),priority='INFO')
		filter_tsys_auto(caltable='%s/caltables/%s.tsys'%(cwd,p_c),
		nsig=params['apriori_cal']['tsys_options']["filt_outlierSN"],
		jump_pc=params['apriori_cal']['tsys_options']["filt_jump_pc"])
	if params['apriori_cal']['tsys_options']["interp_flags"] == True:
		interpgain(caltable='%s/caltables/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
		interpgain(caltable='%s/caltables/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)

if casa6 == True:
	plotcaltable(caltable='%s/caltables/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s/plots/caltables/%s-tsysfiltered_vs_time.pdf'%(cwd,p_c))
	plotcaltable(caltable='%s/caltables/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s/plots/caltables/%s-tsysfiltered_vs_freq.pdf'%(cwd,p_c))

if params['apriori_cal']["make_gaincurve"] == True:
	casalog.post(origin=filename,message='Generating gaincurve calibration table (prep_type=%s)'%params['prepare_data']['gaincurve']['prep_type'],priority='INFO')
	if params['prepare_data']['gaincurve']['prep_type'] == 'append':
		rmdirs(['%s/caltables/%s.gcal'%(cwd,p_c)])
		gencal(vis=msfile,
			caltype='gc',
			spw='',
			antenna='',
			caltable='%s/caltables/%s.gcal'%(cwd,p_c))
	elif params['prepare_data']['gaincurve']['prep_type'] == 'convert':
		gencal(vis=msfile,
			   caltype='gc',
			   spw='',
			   antenna='',
			   infile='%s/caltables/%s.gc'%(cwd,p_c),
			   caltable='%s/caltables/%s.gcal'%(cwd,p_c))

	gaintables = append_gaintable(gaintables,['%s/caltables/%s.gcal'%(cwd,p_c),'',[],'nearest'])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/caltables/%s.gcal'%(cwd,p_c),'',[],'nearest'])

if params['apriori_cal']['do_eops'] == True:
	if ((version[0]*100)+(version[1]*10)+(version[2]))>664:
		casalog.post(origin=filename,message='Fetching earth orientation parameters (EOPs) from USNO',priority='INFO')
		rmdirs(['%s/caltables/%s.eop'%(cwd,p_c)])
		rmfiles(['%s/usno_finals.erp'%cwd])
		os.system('curl -u anonymous:daip@nrao.edu --ftp-ssl ftp://gdc.cddis.eosdis.nasa.gov/vlbi/gsfc/ancillary/solve_apriori/usno_finals.erp > %s/usno_finals.erp' %cwd)
		if os.path.exists('%s/usno_finals.erp'%cwd):
			gencal(vis=msfile,
				caltable='%s/caltables/%s.eop'%(cwd,p_c),
				caltype='eop',
				infile='%s/usno_finals.erp'%(cwd))
			gaintables = append_gaintable(gaintables,['%s/caltables/%s.eop'%(cwd,p_c),'',[],''])
			gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/caltables/%s.eop'%(cwd,p_c),'',[],''])
		else:
			casalog.post(priority='SEVERE',origin=filename,message='EOP parameters have failed. Please ensure that curl is installed on your system')
			pass
	else:
		casalog.post(origin=filename,message='CASA version <= 6.6.4 ... skipping EOP correction',priority='WARN')

if params['apriori_cal']['ionex_options']['run'] == True:
	casalog.post(origin=filename,message='Generating ionospheric TEC calibration table',priority='INFO')
	rmdirs(['%s/caltables/%s.tecim'%(cwd,p_c),
		    '%s/%s.ms.IGS_RMS_TEC.im'%(cwd,p_c),
		    '%s/%s.ms.IGS_TEC.im'%(cwd,p_c)])

	tec_image, tec_rms_image, plotname = tec_maps.create(vis=msfile,doplot=False)
	if casa6 == True:
		try:
			plot_tec_maps(msfile=msfile,
				          tec_image=tec_image,
				          plotfile='%s/plots/%s_TEC.pdf'%(cwd,p_c))
			plot_tec_maps(msfile=msfile,
				          tec_image=tec_rms_image,
				          plotfile='%s/plots/%s_TEC_RMS.pdf'%(cwd,p_c))
		except:
			casalog.post(origin=filename,message='TEC plot generation failed ... continuing without plots',priority='WARN')
			pass

	casalog.post(origin=filename,message='Converting TEC image %s into gaincal table'%tec_image,priority='INFO')
	gencal(vis=msfile,
		   caltable='%s/caltables/%s.tecim'%(cwd,p_c),
	       caltype='tecim',
	       infile=tec_image+'/',
	       uniform=False)
	rmdirs(['%s/%s.ms.IGS_RMS_TEC.im'%(cwd,p_c),
		    '%s/%s.ms.IGS_TEC.im'%(cwd,p_c)])
	rmfiles(['%s/%s.ms.IGS_RMS_TEC.im.fits'%(cwd,p_c),
		    '%s/%s.ms.IGS_TEC.im.fits'%(cwd,p_c)])
	gaintables = append_gaintable(gaintables,['%s/caltables/%s.tecim'%(cwd,p_c),'',[],'linear'])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/caltables/%s.tecim'%(cwd,p_c),'',[],'linear'])

casalog.post(origin=filename,message='Applying %d a-priori gaintable(s) to the data'%len(gaintables['gaintable']),priority='INFO')
applycal(vis=msfile,
	     field='',
	     gaintable=gaintables['gaintable'],
	     interp=gaintables['interp'],
	     gainfield=gaintables['gainfield'],
	     spwmap=gaintables['spwmap'],
	     parang=gaintables['parang'],
	     calwt=params['apriori_cal']['cal_weights'])

rmfiles(['%s/%s.listobs.txt'%(cwd,p_c)])
listobs(vis=msfile,listfile='%s/%s.listobs.txt'%(cwd,p_c))
casalog.post(origin=filename,message='apriori_cal complete',priority='INFO')

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['apriori_cal'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
