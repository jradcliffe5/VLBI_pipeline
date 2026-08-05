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
casalog.origin('vp_shadems_qa')

## Runs shadeMS (https://github.com/ratt-ru/shadeMS) over the current project MS to produce a
## fixed/configurable set of QA rasters (see helper_scripts/install_shadems.sh for how to install
## shadeMS into this CASA). This step produces no gaintables and can be toggled on in
## vlbi_pipe_inputs.txt wherever a QA snapshot of the data is wanted - move it in the step list to
## change when it runs relative to the other steps.
##
## Follows the same before/after, per-field QA idea as the e-MERLIN CASA pipeline's plot_data/
## plot_corrected steps (github.com/e-merlin/eMERLIN_CASA_pipeline): each entry in
## params['shadems_qa']['columns'] present in the MS gets its own labelled set of plots (typically
## DATA = "before" and CORRECTED_DATA = "after" calibration/flagging), so a single run of this step,
## called once CORRECTED_DATA exists, gives an instant before/after comparison. Unlike plotms (which
## eMCP has to iterate per-baseline to stay legible), shadeMS rasterises via datashader, so all
## baselines/antennas are overlaid in one panel and per-field separation is handled natively with
## --iter-field rather than one MS scan per field.

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['shadems_qa'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
p_c = params['global']['project_code']
qa = params['shadems_qa']

if qa['ms_path'] == 'default':
	msfile = '%s/%s.ms'%(cwd,p_c)
else:
	msfile = qa['ms_path']

if os.path.exists('%s/%s_msinfo.json'%(cwd,p_c))==False:
	casalog.post(origin=filename,message='No cached msinfo found ... generating %s/%s_msinfo.json'%(cwd,p_c),priority='INFO')
	msinfo = get_ms_info(msfile)
	save_json(filename='%s/%s_msinfo.json'%(cwd,p_c), array=msinfo, append=False)
else:
	msinfo = load_json('%s/%s_msinfo.json'%(cwd,p_c))

outdir = qa['outdir'] if os.path.isabs(qa['outdir']) else '%s/%s'%(cwd,qa['outdir'])
os.system('mkdir -p %s'%outdir)

## Which data columns actually exist yet (e.g. CORRECTED_DATA only appears after the first
## applycal) - columns requested but not yet present are skipped with a warning rather than
## failing the step, so 'before' plots still run even if 'after' isn't available yet.
tb = casatools.table()
tb.open(msfile)
ms_columns = tb.colnames()
tb.close()

columns = []
for column in qa['columns']:
	if column in ms_columns:
		columns.append(column)
	else:
		casalog.post(origin=filename,message='Column %s not found in %s - skipping (run this step again once it exists, e.g. after applycal)'%(column,msfile),priority='WARN')

## Correlations: fall back to whatever is actually present in the data (e.g. RR,LL for VLBI)
if qa['corr'] in ['default','']:
	default_corr = ",".join(sorted(set(msinfo['SPECTRAL_WINDOW']['spw_pols'])))
else:
	default_corr = qa['corr']

## Fields: translate field names -> CASA field IDs, same pattern fit_autocorrs uses for calibrators.
## 'default' (the whole list, not a field literally named that) means all fields are included, and
## qa['per_field'] (--iter-field) then splits them out into one plot per field.
if qa['fields'] == ['default']:
	default_field = ''
else:
	ids = [str(msinfo['FIELD']['fieldtoID'][f]) for f in qa['fields']]
	default_field = ",".join(ids)

shadems_cmd = params['global']['shadems_command'][0]

casalog.post(origin=filename,message='Running shadeMS QA plots on %s -> %s (columns: %s)'%(msfile,outdir,", ".join(columns)),priority='INFO')

n_ok = 0
n_total = 0
for column in columns:
	for plot in qa['plots']:
		n_total += 1
		xaxis = plot['xaxis']
		yaxis = plot['yaxis']
		corr = plot.get('corr', default_corr) or default_corr
		field = plot.get('field', default_field)
		colour_by = plot.get('colour_by', qa.get('colour_by','CORR'))
		per_field = plot.get('per_field', qa.get('per_field',True))

		cmd = '%s --xaxis %s --yaxis %s --col %s --dir %s --suffix %s'%(shadems_cmd,xaxis,yaxis,column,outdir,column.lower())
		if corr not in ['',None]:
			cmd += ' --corr %s'%corr
		if field not in ['',None]:
			cmd += ' --field %s'%field
		if colour_by not in ['',None,'none']:
			cmd += ' --colour-by %s'%colour_by
		if per_field == True:
			cmd += ' --iter-field'
		if qa.get('extra_args',''):
			cmd += ' %s'%qa['extra_args']
		cmd += ' %s'%msfile

		casalog.post(origin=filename,message='shadeMS: %s'%cmd,priority='INFO')
		ret = os.system(cmd)
		if ret != 0:
			casalog.post(origin=filename,message='shadeMS returned a non-zero exit code (%s) for column=%s xaxis=%s yaxis=%s - continuing with remaining plots'%(ret,column,xaxis,yaxis),priority='WARN')
		else:
			n_ok += 1

steps_run['shadems_qa'] = 1
save_json(filename='%s/vp_steps_run.json'%(cwd), array=steps_run, append=False)
save_json(filename='%s/vp_gaintables.last.json'%(cwd), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(cwd), array=gaintables, append=False)
casalog.post(origin=filename,message='shadems_qa complete: %d/%d plot batch(es) written to %s'%(n_ok,n_total,outdir),priority='INFO')
