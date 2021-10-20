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
gt_r['sub_band_delay'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
msfile= '%s.ms.uvfits'%(params['global']['project_code'])
p_c=params['global']['project_code']

disk = params['global']['AIPS_disk']
AIPS.userno = params['global']['AIPS_user']

if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

refant = find_refants(params['global']['refant'],msinfo)
for j in range(len(refant)):
	refant[j] = msinfo['ANTENNAS']['anttoID'][refant[j]]+1

if steps_run['sub_band_delay'] == 1:
	uvdata = AIPSUVData(p_c,'UVDATA',disk,1)
	uvdata.zap()

uvdata = AIPS_run_load_sort(pwd=cwd,data_prefix=p_c,delete=True,disk=disk)
#uvdata = AIPSUVData(p_c,'UVDATA',disk,1)
for i in range(len(params['sub_band_delay']['select_calibrators'])):
	if i==0:
		sn_tab=1
	else:
		sn_tab=AIPS_get_tab(uvdata,'SN')

	if params['sub_band_delay']['select_calibrators'][i] == ['default']:
		fields=(params['global']['fringe_finders'])
	else:
		fields=(params['sub_band_delay']['select_calibrators'][i])

	#params['sub_band_delay']['extensive_search'] = False
	if params['sub_band_delay']['do_disp_delays'] == True:
		paramactive = 1
	else:
		paramactive = 0
	if params['sub_band_delay']['extensive_search'] == False:
		aparm9 = 1
	else:
		aparm9 = 0
	if params['sub_band_delay']["do_disp_delays"] == True:
		aparm10 = 1
	else:
		aparm10 = 0
	timerange=params['sub_band_delay']['time_range'][i]

	fring = AIPSTask('FRING')
	fring.indata = uvdata
	fring.calsour[1:] = fields
	#fring.timerang[1:] = timerange
	fring.docalib = 2
	fring.gainuse = 0
	fring.refant = refant[0]
	fring.search[1:] = refant[1:]
	fring.solint = convert_solint(params['sub_band_delay']['sol_interval'][i])
	fring.aparm[1:] = [3,0]
	fring.aparm[7] = params['sub_band_delay']['min_snr'][i]
	fring.aparm[9] = aparm9
	fring.aparm[10] = aparm10
	fring.dparm[8] = 1
	fring.snver = sn_tab
	fring.go()

snplt = AIPSTask('SNPLT')
snplt.indata = uvdata
snplt.inext = 'SN'
snplt.invers = AIPS_get_tab(uvdata,'SN')
snplt.nplots = 9
snplt.optype = 'DELA'
snplt.go()

rmfiles(['instrumental_delay.ps'])
lwpla = AIPSTask('LWPLA')
lwpla.indata = uvdata
lwpla.plver = 1
lwpla.invers = AIPS_get_tab(uvdata,'PL')
lwpla.outfile = 'PWD:instrumental_delay.ps'
lwpla.go()
for j in range(AIPS_get_tab(uvdata,'PL')):
	uvdata.zap_table('PL',j)

clcal = AIPSTask('CLCAL')
clcal.indata = uvdata
clcal.invers = AIPS_get_tab(uvdata,'SN')
clcal.snver  = AIPS_get_tab(uvdata,'SN')
clcal.gainver = AIPS_get_tab(uvdata,'CL')
clcal.gainuse = AIPS_get_tab(uvdata,'CL')+1
clcal.interpol = '2PT'
clcal.doblank = 1
clcal.dobtween = 1
clcal.opcode = 'CALP'
clcal.refant = 0
clcal.go()

gaintables = append_gaintable(gaintables,['AIPS_SN%d->CL%d'%(AIPS_get_tab(uvdata,'SN'),AIPS_get_tab(uvdata,'CL')),'',[],'linear'])
#gaintables = append_gaintable(gaintables,['%s/%s.sbd'%(cwd,p_c),'',[],'linear'])
'''
def AIPS_instrumental_delay(uvdata,disk,refant,bpass,phase_cal): ## Makes SN4 and CL3
	## first fring is short timerange on DA193 as all telescopes see this source
	

	snplt = AIPSTask('SNPLT')
	snplt.indata = uvdata
	snplt.inext = 'SN'
	snplt.invers = get_tab(uvdata,'SN')
	snplt.nplots = 8
	snplt.optype = 'DELA'
	snplt.go()

	os.system('rm instrumental_delay.ps')
	lwpla = AIPSTask('LWPLA')
	lwpla.indata = uvdata
	lwpla.plver = 1
	lwpla.invers = get_tab(uvdata,'PL')
	lwpla.outfile = 'PWD:instrumental_delay.ps'
	lwpla.go()
	for j in range(get_tab(uvdata,'PL')):
		uvdata.zap_table('PL',j)

	clcal = AIPSTask('CLCAL')
	clcal.indata = uvdata
	clcal.invers = get_tab(uvdata,'SN')
	clcal.snver  = get_tab(uvdata,'SN')
	clcal.gainver = get_tab(uvdata,'CL')
	clcal.gainuse = get_tab(uvdata,'CL')+1
	clcal.interpol = '2PT'
	clcal.opcode = 'CALP'
	clcal.refant = refant
	clcal.go()

for i in range(len(params['sub_band_delay']['select_calibrators'])):
	if i==0:
		append=False
	else:
		append=True

	if params['sub_band_delay']['select_calibrators'][i] == ['default']:
		fields=",".join(params['global']['fringe_finders'])
	else:
		fields=",".join(params['sub_band_delay']['select_calibrators'][i])

	#params['sub_band_delay']['extensive_search'] = False
	if params['sub_band_delay']['do_disp_delays'] == True:
		paramactive = [True,True,True]
	else:
		paramactive = [True,True,False]
	if params['sub_band_delay']['extensive_search'] == False:

		fringefit(vis=msfile,
				  caltable='%s/%s.sbd'%(cwd,p_c),
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
'''
gt_r['sub_band_delay'] = append_gaintable(gaintables,['AIPS_SN%d->CL%d'%(AIPS_get_tab(uvdata,'SN'),AIPS_get_tab(uvdata,'CL')),'',[],'linear'])

save_json(filename='%s/vp_gaintables.last.json'%(params['global']['cwd']), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
steps_run['sub_band_delay'] = 1
save_json(filename='%s/vp_steps_run.json'%(params['global']['cwd']), array=steps_run, append=False)
