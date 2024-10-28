import inspect, os, sys, json, re
from collections import OrderedDict

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *
import tec_maps

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
	if msinfo['TELE_NAME'] == 'VLBA':
		doaccor=True
	else:
		doaccor=False

if doaccor==True:
	## DiFX correlator sampling corrections
	rmdirs(['%s/%s.accor'%(cwd,p_c)])
	accor(vis=msfile,
	      caltable='%s/%s.accor'%(cwd,p_c),
	      solint=params['apriori_cal']['accor_options']['solint'])
	gaintables = append_gaintable(gaintables,['%s/%s.accor'%(cwd,p_c),'',[],params['apriori_cal']['accor_options']['interp']])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/%s.accor'%(cwd,p_c),'',[],params['apriori_cal']['accor_options']['interp']])
	if params['apriori_cal']['accor_options']['smooth'] == True:
		smoothcal(vis=msfile,
		          tablein='%s/%s.accor'%(cwd,p_c),
		          caltable='%s/%s.accor'%(cwd,p_c),
			   smoothtime=params['apriori_cal']['accor_options']['smoothtime'])

### Run prior-cals
if params['apriori_cal']["do_observatory_flg"] == True:
	if os.path.exists('%s/%s_casa.flags'%(cwd,p_c)):
		if steps_run['apriori_cal'] == 1:
			flagmanager(vis=msfile,mode='restore',versionname='original_flags')
		else:
			flagmanager(vis=msfile,mode='save',versionname='original_flags')
		flagdata(vis=msfile,mode='list',inpfile='%s/%s_casa.flags'%(cwd,p_c))

rmdirs(['%s/%s.tsys'%(cwd,p_c)])
gencal(vis=msfile,\
       caltype='tsys',\
       spw='',\
       antenna='',\
       caltable='%s/%s.tsys'%(cwd,p_c),\
       uniform=False)

if casa6 == True:
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s-tsys_vs_time.pdf'%p_c)
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s-tsys_vs_freq.pdf'%p_c)

gaintables = append_gaintable(gaintables,['%s/%s.tsys'%(cwd,p_c),'',[],params['apriori_cal']['tsys_options']['interp']])
gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/%s.tsys'%(cwd,p_c),'',[],params['apriori_cal']['tsys_options']['interp']])

if params['apriori_cal']['tsys_options']['interp_flags'] == True:
	interpgain(caltable='%s/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
	interpgain(caltable='%s/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)

if params['apriori_cal']['tsys_options']['smooth'] == True:
	rmdirs(['%s/%s.tsys_original'%(cwd,p_c)])
	os.system('cp -r %s/%s.tsys %s/%s.tsys_original'%(cwd,p_c,cwd,p_c))
	filter_tsys_auto(caltable='%s/%s.tsys'%(cwd,p_c),nsig=params['apriori_cal']['tsys_options']['outlier_SN'],jump_pc=params['apriori_cal']['tsys_options']['jump_ident_pc'])
	interpgain(caltable='%s/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
	interpgain(caltable='%s/%s.tsys'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)

if casa6 == True:
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s-tsysfiltered_vs_time.pdf'%p_c)
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s-tsysfiltered_vs_freq.pdf'%p_c)

if params['apriori_cal']["make_gaincurve"] == True:
	rmdirs(['%s/%s.gcal'%(cwd,p_c)])
	gencal(vis=msfile,\
	       caltype='gc',\
	       spw='',\
	       antenna='',\
	       caltable='%s/%s.gcal'%(cwd,p_c),\
	       infile='%s/%s.gc'%(cwd,p_c))

	gaintables = append_gaintable(gaintables,['%s/%s.gcal'%(cwd,p_c),'',[],'nearest'])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/%s.gcal'%(cwd,p_c),'',[],'nearest'])

if params['apriori_cal']['do_eops'] == True:
	rmdirs(['%s/%s.eop'%(cwd,p_c),'usno_finals.erp'])
	os.system('curl -u anonymous:daip@nrao.edu --ftp-ssl ftp://gdc.cddis.eosdis.nasa.gov/vlbi/gsfc/ancillary/solve_apriori/usno_finals.erp > %s/usno_finals.erp' %cwd)
	if os.path.exists('%s/usno_finals.erp'%cwd):
		gencal(vis=msfile, 
		   	   caltable='%s/%s.eop'%(cwd,p_c),
	           caltype='eop', 
	           infile='%s/usno_finals.erp'%(cwd))
		gaintables = append_gaintable(gaintables,['%s/%s.eop'%(cwd,p_c),'',[],''])
		gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/%s.eop'%(cwd,p_c),'',[],''])
	else:
		casalog.post(priority='SEVERE',origin=filename,message='EOP parameters have failed. Please ensure that curl is installed on your system')
		pass

if params['apriori_cal']['ionex_options']['run'] == True:
	rmdirs(['%s/%s.tecim'%(cwd,p_c),
		    '%s/%s.ms.IGS_RMS_TEC.im'%(cwd,p_c),
		    '%s/%s.ms.IGS_TEC.im'%(cwd,p_c)])

	tec_image, tec_rms_image, plotname = tec_maps.create0(ms_name=msfile, 
		                                                  plot_vla_tec=False, 
		                                                  username='anonymous',
		                                                  password=params['global']["email_progress"],
		                                                  force_to=params['apriori_cal']["ionex_options"]["ionex_type"])
	if casa6 == True:
		try:
			plot_tec_maps(msfile=msfile,
				          tec_image=tec_image,
				          plotfile='%s/%s_TEC.pdf'%(cwd,p_c))
			plot_tec_maps(msfile=msfile,
				          tec_image=tec_rms_image,
				          plotfile='%s/%s_TEC_RMS.pdf'%(cwd,p_c))
		except:
			print('error')


	gencal(vis=msfile, 
		caltable='%s/%s.tecim'%(cwd,p_c),
	       caltype='tecim', 
	       infile=tec_image+'/',
	       uniform=False)
	gaintables = append_gaintable(gaintables,['%s/%s.tecim'%(cwd,p_c),'',[],'linear'])
	gt_r['apriori_cal'] = append_gaintable(gt_r['apriori_cal'],['%s/%s.tecim'%(cwd,p_c),'',[],'linear'])

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

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['apriori_cal'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
