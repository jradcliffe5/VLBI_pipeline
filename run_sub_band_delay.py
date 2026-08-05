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
casalog.origin('vp_sub_band_delay')

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['sub_band_delay'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']
os.system('mkdir -p %s/plots/caltables'%cwd)

if os.path.exists('%s/%s_msinfo.json'%(cwd,p_c))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(cwd,p_c), array=get_ms_info('%s/%s.ms'%(cwd,p_c)), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(cwd,p_c))

refant = find_refants(params['global']['refant'],msinfo)
casalog.post(origin=filename,message='Using reference antenna(s): %s'%refant,priority='INFO')

rmdirs(['%s/caltables/%s.sbd'%(cwd,p_c)])
for i in range(len(params['sub_band_delay']['select_calibrators'])):
	if i==0:
		append=False
	else:
		append=True

	if params['sub_band_delay']['select_calibrators'][i] == ['default']:
		fields=",".join(params['global']['fringe_finders'])
	else:
		fields=",".join(params['sub_band_delay']['select_calibrators'][i])

	casalog.post(origin=filename,message='Sub-band delay pass %d/%d: tfcrop flagging field(s) %s'%(i+1,len(params['sub_band_delay']['select_calibrators']),fields),priority='INFO')
	flagdata(vis=msfile,
		 mode='tfcrop',
		 field=fields,
		 datacolumn='corrected',
		 combinescans=False,
		 winsize=3,
		 timecutoff=4.5,
		 freqcutoff=4.5,
		 maxnpieces=7,
		 halfwin=1,
		 extendflags=True,
		 action='apply',
		 display='',
		 flagbackup=False)

	#params['sub_band_delay']['extensive_search'] = False
	if params['sub_band_delay']['do_disp_delays'] == True:
		paramactive = [True,True,True]
	else:
		paramactive = [True,True,False]
	if params['sub_band_delay']['extensive_search'] == False:
		casalog.post(origin=filename,message='Fringe-fitting field(s) %s (solint=%s, niter=%s, minsnr=%s)'%(fields,params['sub_band_delay']['sol_interval'][i],params['sub_band_delay']['fringe_niter'],params['sub_band_delay']['min_snr'][i]),priority='INFO')
		fringefit(vis=msfile,
				  caltable='%s/caltables/%s.sbd'%(cwd,p_c),
				  field=fields,
				  solint=params['sub_band_delay']['sol_interval'][i],
				  antenna='',
				  spw='',
				  timerange=params['sub_band_delay']['time_range'][i],
				  zerorates=True,
				  paramactive=paramactive,
				  niter=params['sub_band_delay']['fringe_niter'],
				  refant=refant,
				  append=append,
				  corrdepflags=True,
				  minsnr=params['sub_band_delay']['min_snr'][i],
				  gaintable=gaintables['gaintable'],
				  gainfield=gaintables['gainfield'],
				  interp=gaintables['interp'],
				  spwmap=gaintables['spwmap'],
				  parang=gaintables['parang'])

	elif params['sub_band_delay']['extensive_search'] == True:
		'''
		if i == 0:
			if os.path.exists('%s.sbd_eb'%p_c):
				rmdirs(['%s.sbd_eb'%p_c])
			os.system('mkdir %s.sbd_eb'%p_c)
		do_eb_fringefit(vis=msfile,
						caltable='%s.sbd'%(p_c),
						field=fields,
						solint=params['sub_band_delay']['sol_interval'][i],
						timerange=params['sub_band_delay']['time_range'][i],
						zerorates=True,
						niter=params['sub_band_delay']['fringe_niter'],
						append=append,
						minsnr=params['sub_band_delay']['min_snr'][i],
						msinfo=msinfo,
						gaintable_dict=gaintables,
						casa6=casa6)
		'''
		casalog.post(origin=filename,message='Extensive-search fringe fitting is not yet implemented ... skipping field(s) %s'%fields,priority='WARN')
	else:
		casalog.post(origin=filename,message='Wrong parameter for extensive baseline (true/false)',priority='SEVERE')
		sys.exit()
if params['sub_band_delay']['extensive_search'] == True:
	casalog.post(origin=filename,message='Generating full fringe-fit table across all antennas/scans',priority='INFO')
	generate_ff_full_table(msinfo)


if params['sub_band_delay']['modify_sbd']['run'] == True:
	#rmdirs(['%s/%s.sbd.bpass'%(cwd,p_c)])
	#auto_modify_sbdcal(msfile=msfile,
	#	               caltable='%s/%s.sbd'%(cwd,p_c),
	#	               solint=params['sub_band_delay']['sol_interval'],
	#	               spw_pass=params['sub_band_delay']['modify_sbd']['spw_passmark'],
	#	               bad_soln_clip=params['sub_band_delay']['modify_sbd']['clip_badtimes'],
	#	               plot=False)
	casalog.post(origin=filename,message='Interpolating flagged sub-band delay solutions',priority='INFO')
	interpgain(caltable='%s/caltables/%s.sbd'%(cwd,p_c),obsid='0',field='*',interp='linear',extrapolate=False,fringecal=True)
	interpgain(caltable='%s/caltables/%s.sbd'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=True)

remove_flagged_scans('%s/caltables/%s.sbd'%(cwd,p_c))

if casa6 == True:
	casalog.post(origin=filename,message='Plotting sub-band delay solutions',priority='INFO')
	for i in ['delay','phase']:
		for j in ['freq','time']:
			plotcaltable(caltable='%s/caltables/%s.sbd'%(cwd,p_c),yaxis='%s'%i,xaxis='%s'%j,plotflag=True,msinfo=msinfo,figfile='%s/plots/caltables/%s-sbd_%s_vs_%s.pdf'%(cwd,p_c,i,j))

gaintables = append_gaintable(gaintables,['%s/caltables/%s.sbd'%(cwd,p_c),'',[],'linear'])
gt_r['sub_band_delay'] = append_gaintable(gt_r['sub_band_delay'],['%s/caltables/%s.sbd'%(cwd,p_c),'',[],'linear'])
casalog.post(origin=filename,message='sub_band_delay complete: registered %s/caltables/%s.sbd as a gaintable'%(cwd,p_c),priority='INFO')

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['sub_band_delay'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
