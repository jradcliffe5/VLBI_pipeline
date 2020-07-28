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
	rmdirs(['rm -r %s/%s.accor'%(cwd,p_c)])
	accor(vis=msfile,
	      caltable='%s/%s.accor'%(cwd,p_c),
	      solint=params['apriori_cal']['accor_options']['solint'])
	append_gaintable(gaintables,['%s/%s.accor'%(cwd,p_c),'',[],params['apriori_cal']['accor_options']['interp']])
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

if params['apriori_cal']['tsys_options']['interp_flags'] == True:
	fill_flagged_soln(caltable='%s/%s.tsys'%(cwd,p_c),fringecal=True)
if params['apriori_cal']['tsys_options']['smooth'] == True:
	rmdirs(['%s/%s.tsys_original'%(cwd,p_c)])
	os.system('cp -r %s/%s.tsys %s/%s.tsys_original'%(cwd,p_c,cwd,p_c))
	filter_tsys_auto(caltable='%s/%s.tsys'%(cwd,p_c),nsig=params['apriori_cal']['tsys_options']['outlier_SN'],jump_pc=params['apriori_cal']['tsys_options']['jump_ident_pc'])
	fill_flagged_soln(caltable='%s/%s.tsys'%(cwd,p_c),fringecal=True)

if casa6 == True:
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='time',plotflag=True,msinfo=msinfo,figfile='%s-tsysfiltered_vs_time.pdf'%p_c)
	plotcaltable(caltable='%s/%s.tsys'%(cwd,p_c),yaxis='tsys',xaxis='freq',plotflag=True,msinfo=msinfo,figfile='%s-tsysfiltered_vs_freq.pdf'%p_c)

rmdirs(['%s/%s.gcal'%(cwd,p_c)])
gencal(vis=msfile,\
       caltype='gc',\
       spw='',\
       antenna='',\
       caltable='%s/%s.gcal'%(cwd,p_c),\
       infile='%s/%s.gc'%(cwd,p_c))
gaintables = append_gaintable(gaintables,['%s/%s.gcal'%(cwd,p_c),'',[],'nearest'])

applycal(vis=msfile,
	     field='',
	     gaintable=gaintables['gaintable'],
	     interp=gaintables['interp'],
	     gainfield=gaintables['gainfield'],
	     spwmap=gaintables['spwmap'],
	     parang=gaintables['parang'])

rmfiles(['%s/%s.listobs.txt'%(cwd,p_c)])
listobs(vis=msfile,listfile='%s/%s.listobs.txt'%(cwd,p_c))

save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['apriori_cal'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)