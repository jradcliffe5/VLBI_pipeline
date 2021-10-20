import inspect, os, sys, json, re
from collections import OrderedDict

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions_AIPS import *

from AIPS import AIPS, AIPSDisk
from AIPSTask import AIPSTask, AIPSList
from AIPSData import AIPSUVData, AIPSImage, AIPSCat
from Wizardry.AIPSData import AIPSUVData as WizAIPSUVData

casa6=True

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['bandpass_cal'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

disk = params['global']['AIPS_disk']
AIPS.userno = params['global']['AIPS_user']

cwd = params['global']['cwd']
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']



if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

refant = find_refants(params['global']['refant'],msinfo)


gaintab = []

gaintab=gaintables['gaintable']

#rmdirs(['%s/%s.bpass'%(cwd,p_c)])
if params['bandpass_cal']['same_as_sbd_cal'] == True:
	substep='sub_band_delay'
else:
	substep='bandpass_cal'

uvdata = AIPSUVData(p_c,'UVDATA',disk,1)

f = []
for i in range(len(params[substep]['select_calibrators'])):
	if i==0:
		append=False
	else:
		append=True

	if params[substep]['select_calibrators'][i] == ['default']:
		fields=(params['global']['fringe_finders'])
	else:
		fields=(params[substep]['select_calibrators'][i])
	f.append(fields)
f = [item for sublist in f for item in sublist]


bpass = AIPSTask('BPASS')
bpass.indata = uvdata
bpass.calsour[1:] = f
bpass.docalib = 2
bpass.solint = 1000000
bpass.gainuse = AIPS_get_tab(uvdata,'CL')
bpass.bpassprm[1:] = [0,0,1,0,0,0,0,0,1,1]
bpass.soltype = 'GCON'
bpass.bpver = 1
bpass.go()

for j in f:
	possm = AIPSTask('POSSM')
	possm.indata = uvdata
	possm.sources[1] = j
	possm.docalib = 2
	possm.gainuse = AIPS_get_tab(uvdata,'CL')
	possm.doband = 0
	possm.bpver = 1
	possm.codetype = 'A&P'
	possm.nplots = 9
	possm.go()
	os.system('rm pre-bandpass_POSSM_%s.ps' % j)
	lwpla = AIPSTask('LWPLA')
	lwpla.indata = uvdata
	lwpla.plver = 1
	lwpla.invers = AIPS_get_tab(uvdata,'PL')
	lwpla.outfile = 'PWD:pre-bandpass_POSSM_%s.ps' % j
	lwpla.go()
	for k in range(AIPS_get_tab(uvdata,'PL')):
		uvdata.zap_table('PL',k)
	possm.doband = 1
	possm.go()
	os.system('rm post-bandpass_POSSM_%s.ps' % j)
	lwpla = AIPSTask('LWPLA')
	lwpla.indata = uvdata
	lwpla.plver = 1
	lwpla.invers = AIPS_get_tab(uvdata,'PL')
	lwpla.outfile = 'PWD:post-bandpass_POSSM_%s.ps' % j
	lwpla.go()
	for k in range(AIPS_get_tab(uvdata,'PL')):
		uvdata.zap_table('PL',k)
'''	
	bandpass(vis=msfile,
			 caltable='%s/%s.bpass'%(cwd,p_c),
			 field=fields,
			 solint=params['bandpass_cal']['sol_interval'],
			 antenna='',
			 spw='',
			 combine='scan',
			 solnorm=True,
			 timerange=params[substep]['time_range'][i],
			 refant=refant,
			 append=append,
			 fillgaps=16,
			 minsnr=params['bandpass_cal']['min_snr'],
			 gaintable=gaintab,
			 corrdepflags=True,
			 gainfield=gaintables['gainfield'],
			 interp=gaintables['interp'],
			 spwmap=gaintables['spwmap'],
			 parang=gaintables['parang'])

#interpgain(caltable='%s/%s.bpass'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=False,fringecal=False)
interpgain(caltable='%s/%s.bpass'%(cwd,p_c),obsid='0',field='*',interp='nearest',extrapolate=True,fringecal=False)



if '%s/%s.auto.bpass'%(cwd,p_c) in gaintab:
	tb = casatools.table()
	tb.open('%s/%s.bpass'%(cwd,p_c))
	flags = tb.getcol('FLAG')
	spw = tb.getcol('SPECTRAL_WINDOW_ID')
	ant = tb.getcol('ANTENNA1')
	data = tb.getcol('CPARAM')
	npol = msinfo['SPECTRAL_WINDOW']['npol']
	if npol>2:
		npol=2
	tb.close()
	tb.open('%s/%s.auto.bpass'%(cwd,p_c))
	for i in range(len(msinfo['ANTENNAS']['anttoID'])):
		for j in range(msinfo['SPECTRAL_WINDOW']['nspws']):
			subt = tb.query('ANTENNA1==%s and SPECTRAL_WINDOW_ID==%s'%(i,j))
			for k in range(npol):
				if np.all(subt.getcol('FLAG')[k,:,:]==False):
					subflg = flags[k,:,(spw==j)&(ant==i)]
					subdata = data[k,:,(spw==j)&(ant==i)]
					subdata[subflg==True] = 1+0j
					subflg = False
					data[k,:,(spw==j)&(ant==i)] = subdata
					flags[k,:,(spw==j)&(ant==i)] = subflg
	tb.close()
	tb.open('%s/%s.bpass'%(cwd,p_c),nomodify=False)
	tb.putcol('CPARAM',data)
	tb.putcol('FLAG',flags)
	tb.close()

if casa6 == True:
	for i in ['amp','phase']:
		for j in ['freq','time']:
			plotcaltable(caltable='%s/%s.bpass'%(cwd,p_c),yaxis='%s'%i,xaxis='%s'%j,plotflag=True,msinfo=msinfo,figfile='%s-bpass_%s_vs_%s.pdf'%(p_c,i,j))

flagmanager(vis=msfile,mode='restore',versionname='temp_bpass')
'''
#gaintables = append_gaintable(gaintables,['%s/%s.bpass'%(cwd,p_c),'',[],'linear,linear'])
gaintables = append_gaintable(gaintables,['AIPS_BP%d'%(AIPS_get_tab(uvdata,'BP')),'',[],'linear'])
gt_r['bandpass_cal'] = append_gaintable(gaintables,['AIPS_BP%d'%(AIPS_get_tab(uvdata,'BP')),'',[],'linear'])

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['bandpass_cal'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
