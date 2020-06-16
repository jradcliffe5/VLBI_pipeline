import inspect, os, sys, json, re

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
steps_run = load_json('vp_steps_run.json')

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

msinfo = get_ms_info(msfile)

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
	      solint=params['accor_options']['solint'])
	if params['accor_options']['smooth'] == True:
		smoothcal(vis=msfile,
		          tablein='%s/%s.accor'%(cwd,p_c),
		          caltable='%s/%s.accor'%(cwd,p_c),
			      smoothtime=params['accor_options']['smoothtime'])

### Run prior-cals

#flagdata(vis=mmsfile,mode='list',inpfile='%s/%s_casa.flag'%(cwd,epoch))

rmdirs(['%s/%s.tsys'%(cwd,p_c)])
gencal(vis=msfile,\
       caltype='tsys',\
       spw='',\
       antenna='',\
       caltable='%s/%s.tsys'%(cwd,p_c),\
       uniform=False)

if params['tsys_options']['interp_flag'] == True:
	fill_flagged_soln(caltable='%s/%s.tsys'%(cwd,p_c),fringecal=True)
if params['tsys_options']['smooth'] == True:
	rmdirs(['%s/%s.tsys_original'%(cwd,p_c)])
	os.system('mv %s/%s.tsys %s/%s.tsys_original'%(cwd,p_c,cwd,p_c))
	filter_tsys_auto(caltable='%s/%s.tsys'%(cwd,p_c),nsig=[2.5,2.],jump_pc=20)

rmdirs(['%s/%s.gcal'%(cwd,p_c)])
gencal(vis=msfile,\
       caltype='gc',\
       spw='',\
       antenna='',\
       caltable='%s/%s.gcal'%(cwd,p_c),\
       infile='%s/%s.gc'%(cwd,p_c))

rmfiles(['%s/%s.listobs.txt'%(cwd,p_c)])
listobs(vis=msfile,listfile='%s/%s.listobs.txt'%(cwd,p_c))
