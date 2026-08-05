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
casalog.origin('vp_qa')

## Runs shadeMS (https://github.com/ratt-ru/shadeMS - must be installed into this CASA first, see
## helper_scripts/install_shadems.sh) over the current project MS to produce a fixed/configurable
## set of QA rasters. This step produces no gaintables and can be toggled on in
## vlbi_pipe_inputs.txt wherever a QA snapshot of the data is wanted - move it in the step list to
## change when it runs relative to the other steps.
##
## Follows the same before/after, per-field QA idea as the e-MERLIN CASA pipeline's plot_data/
## plot_corrected steps (github.com/e-merlin/eMERLIN_CASA_pipeline): each entry in
## params['qa']['columns'] present in the MS gets its own labelled set of plots (typically
## DATA = "before" and CORRECTED_DATA = "after" calibration/flagging), so a single run of this step,
## called once CORRECTED_DATA exists, gives an instant before/after comparison. Unlike plotms (which
## eMCP has to iterate per-baseline to stay legible), shadeMS rasterises via datashader, so all
## baselines/antennas are overlaid in one panel and per-field separation is handled natively with
## --iter-field rather than one MS scan per field. The default plot set mirrors eMCP's make_4plots
## (amp/phase vs time/freq) plus its make_uvcov; eMCP's elevation-vs-time plot isn't included since
## elevation isn't an MS column - it needs ephemeris, not something shadeMS (or this step) does.
##
## params['qa']['row_chunk_size'] (blank by default) maps to shadeMS's --row-chunk-size: dask-ms
## splits the MS into this many rows per task, so a large MS with the default (5000) can fan out
## into thousands of concurrent dask tasks/file reads - on a networked filesystem under metadata
## pressure this can stall for a long time on a single stuck request rather than erroring, which
## looks like a hang (ps -T on the shadems PID will show every thread idle except one blocked in
## the kernel, e.g. wchan ceph_mdsc_wait_request on CephFS). Set this to something larger (e.g.
## 50000-100000) on large MSs/busy filesystems to cut the task count down.
##
## shadeMS indexes/builds its dataframes once per invocation, then reuses that for every
## --xaxis/--yaxis pair given in that same call (repeated flags, not separate calls) - and on a
## large MS over a networked filesystem, that indexing pass is what dominates the runtime, not the
## actual plotting. So per column, plots that share the same corr/field/per_field selection and
## either all want a --colour-by or all skip it are batched into a single shadeMS call (repeated
## --xaxis/--yaxis/--colour-by), rather than one call per plot - the indexing cost is then paid
## once per batch instead of once per plot. Columns are kept as separate calls regardless (shadeMS
## can embed a column directly in an axis spec, e.g. 'amp:CORRECTED_DATA', but two plots that only
## differ by column can then produce the same default output filename, silently overwriting one
## another - --suffix per column-call sidesteps that instead).

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['qa'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = params['global']['cwd']
p_c = params['global']['project_code']
qa = params['qa']

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

## Correlations: default to whatever parallel-hand pols are present (RR,LL or XX,YY) - routine
## amp/phase QA doesn't need cross-hand (RL,LR), and on full-Stokes/polarimetric VLBI data
## including it roughly doubles the bytes shadeMS has to read for no QA benefit. Cross-hand is
## still available via an explicit params['qa']['corr'] (or per-plot 'corr') override, e.g. for a
## polarization-calibration-specific check.
if qa['corr'] in ['default','']:
	spw_pols = set(msinfo['SPECTRAL_WINDOW']['spw_pols'])
	parallel_hand = sorted(p for p in ('RR','LL','XX','YY') if p in spw_pols)
	default_corr = ",".join(parallel_hand) if parallel_hand else ",".join(sorted(spw_pols))
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

casalog.post(origin=filename,message='Running QA plots (shadeMS) on %s -> %s (columns: %s)'%(msfile,outdir,", ".join(columns)),priority='INFO')

n_ok = 0
n_batches = 0
n_plots = 0
for column in columns:
	## Resolve each plot's selection, then group plots that can share one shadeMS invocation:
	## same (corr, field, per_field), and either all wanting a --colour-by or all skipping it
	## (skipping is done by omitting the flag entirely, which only works cleanly when every
	## plot in the call agrees on that).
	groups = OrderedDict()
	for plot in qa['plots']:
		corr = plot.get('corr', default_corr) or default_corr
		field = plot.get('field', default_field)
		per_field = plot.get('per_field', qa.get('per_field',True))
		colour_by = plot.get('colour_by', qa.get('colour_by','CORR'))
		has_colour_by = colour_by not in ['',None,'none']
		key = (corr, field, per_field, has_colour_by)
		groups.setdefault(key, []).append((plot['xaxis'], plot['yaxis'], colour_by if has_colour_by else None))

	for (corr, field, per_field, has_colour_by), plots in groups.items():
		n_batches += 1
		n_plots += len(plots)

		cmd = '%s --col %s --dir %s --suffix %s'%(shadems_cmd,column,outdir,column.lower())
		for xaxis, yaxis, colour_by in plots:
			cmd += ' --xaxis %s --yaxis %s'%(xaxis,yaxis)
			if colour_by is not None:
				cmd += ' --colour-by %s'%colour_by
		if corr not in ['',None]:
			cmd += ' --corr %s'%corr
		if field not in ['',None]:
			cmd += ' --field %s'%field
		if per_field == True:
			cmd += ' --iter-field'
		if qa.get('row_chunk_size',''):
			cmd += ' --row-chunk-size %s'%qa['row_chunk_size']
		if qa.get('extra_args',''):
			cmd += ' %s'%qa['extra_args']
		cmd += ' %s'%msfile

		casalog.post(origin=filename,message='shadeMS (%d plot(s) in one pass): %s'%(len(plots),cmd),priority='INFO')
		ret = os.system(cmd)
		if ret != 0:
			casalog.post(origin=filename,message='shadeMS returned a non-zero exit code (%s) for column=%s, plots=%s - continuing with remaining batches'%(ret,column,[(x,y) for x,y,_ in plots]),priority='WARN')
		else:
			n_ok += 1

steps_run['qa'] = 1
save_json(filename='%s/vp_steps_run.json'%(cwd), array=steps_run, append=False)
save_json(filename='%s/vp_gaintables.last.json'%(cwd), array=gt_r, append=False)
save_json(filename='%s/vp_gaintables.json'%(cwd), array=gaintables, append=False)
casalog.post(origin=filename,message='qa complete: %d/%d shadeMS call(s) succeeded (%d plot(s) total) written to %s'%(n_ok,n_batches,n_plots,outdir),priority='INFO')
