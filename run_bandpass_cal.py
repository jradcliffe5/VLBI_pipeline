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
casalog.origin('vp_bandpass_cal')

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['bandpass_cal'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

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
'''
for i in gaintables['gaintable']:
	print(i)
	if i.endswith('.sbd'):
		gaintab.append('%s.bpasscal'%i)
	else:
		gaintab.append(i)
'''
gaintab=gaintables['gaintable']

if steps_run['bandpass_cal'] == 1:
	flagmanager(vis=msfile,mode='restore',versionname='vp_bpass_cal')
else:
	flagmanager(vis=msfile,mode='save',versionname='vp_bpass_cal')
applycal(vis=msfile,
		 field=",".join(params['global']["fringe_finders"])+','+",".join(params['global']['phase_calibrators']),
	     gaintable=gaintab,
	     interp=gaintables['interp'],
	     gainfield=gaintables['gainfield'],
	     spwmap=gaintables['spwmap'],
	     parang=gaintables['parang'])

rmdirs(['%s/%s.bpass'%(cwd,p_c)])
if params['bandpass_cal']['same_as_sbd_cal'] == True:
	substep='sub_band_delay'
else:
	substep='bandpass_cal'

for i in range(len(params[substep]['select_calibrators'])):
	if i==0:
		append=False
	else:
		append=True
	

	if params[substep]['select_calibrators'][i] == ['default']:
		fields=",".join(params['global']['fringe_finders'])
	else:
		fields=",".join(params[substep]['select_calibrators'][i])
		
	bandpass(vis=msfile,
			 caltable='%s/%s.bpass'%(cwd,p_c),
			 field=fields,
			 solint=params['bandpass_cal']['sol_interval'],
			 antenna='',
			 spw='',
			 combine=params['bandpass_cal']["bpass_combine"],
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
remove_flagged_scans('%s/%s.bpass'%(cwd,p_c))
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

gaintables = append_gaintable(gaintables,['%s/%s.bpass'%(cwd,p_c),'',[],'linear,linear'])
gt_r['bandpass_cal'] = append_gaintable(gt_r['bandpass_cal'],['%s/%s.bpass'%(cwd,p_c),'',[],'linear,linear'])

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['bandpass_cal'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
