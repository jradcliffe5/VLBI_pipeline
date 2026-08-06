import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections

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
casalog.origin('vp_run_vlbi_pipe')

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

## Optional: override which steps run directly on the command line instead of
## hand-editing the "Steps to run" block of the inputs file, e.g.
##   python run_vlbi_pipe.py vlbi_pipe_inputs.txt --steps bandpass_cal phase_referencing
##   casa -c run_vlbi_pipe.py vlbi_pipe_inputs.txt --steps bandpass_cal phase_referencing
## Any step not named after --steps is switched off for this run only; the
## inputs file itself is left untouched. Two convenience aliases are also
## accepted in place of (or alongside) individual step names:
##   all       - every step
##   phaseref  - every step except the wide-field apply_to_all and mssc steps
## Keep this list/these aliases in sync with the "## Steps to run ##" block
## in vlbi_pipe_inputs.txt and with STEP_KEYS/STEP_ALIASES in
## helper_scripts/set_pipeline_steps.py.
STEP_KEYS = [
	'prepare_data','import_fitsidi','make_mms','apriori_cal','init_flag',
	'fit_autocorrs','sub_band_delay','bandpass_cal','phase_referencing',
	'apply_target','qa','apply_to_all','mssc',
]
STEP_ALIASES = {
	'all': STEP_KEYS,
	'phaseref': [s for s in STEP_KEYS if s not in ('apply_to_all','mssc')],
}
step_override = None
extra_args = sys.argv[i+1:]
if '--steps' in extra_args:
	idx = extra_args.index('--steps')
	step_override = []
	for a in extra_args[idx+1:]:
		if a.startswith('--'):
			break
		if a in STEP_ALIASES:
			for s in STEP_ALIASES[a]:
				if s not in step_override:
					step_override.append(s)
		elif a in STEP_KEYS:
			if a not in step_override:
				step_override.append(a)
		else:
			sys.exit('Unknown step passed to --steps: %s (choose from: %s, or alias: %s)'%(a, ', '.join(STEP_KEYS), ', '.join(STEP_ALIASES)))
	if not step_override:
		sys.exit('--steps given with no step names')

## Load global inputs
inputs = headless(sys.argv[i])


steps = copy.deepcopy(inputs)
for i in inputs:
	if i in ['parameter_file_path','make_scripts','run_jobs']:
		del steps[i]

if step_override is not None:
	casalog.post(priority='INFO',origin=filename,message='Overriding steps to run from --steps: %s'%", ".join(step_override))
	for k in steps:
		steps[k] = 1 if k in step_override else 0

## Load parameters
params=load_json(inputs['parameter_file_path'])

save_json(filename='%s/vp_inputs.json'%(params['global']['cwd']),array=inputs,append=False)

casalog.post(priority='INFO',origin=filename,message='Initialising VLBI pipeline run')

if os.path.exists('%s/%s'%(params['global']['cwd'],'vp_steps_run.json')) == False:
	casalog.post(priority='INFO',origin=filename,message='No previous steps have been run - creating logger')
	for j in ['logs','plots','caltables','images']:
		rmdirs(['%s/%s'%(params['global']['cwd'],j)])
		os.system('mkdir %s/%s'%(params['global']['cwd'],j))
	init_pipe_run(steps,params)
	steps_run=load_json('vp_steps_run.json')
else:
	casalog.post(priority='INFO',origin=filename,message='A previous run has been detected')
	casalog.post(priority='WARN',origin=filename,message='If you dont mean to do this please delete vp_steps_run.json')
	steps_run=load_json('vp_steps_run.json')

## Time to build all scripts
for j,i in enumerate(steps.keys()):
	if steps[i]==1:
		casalog.post(priority='INFO',origin=filename,message='Writing script for step: %s'%i)
		if i == 'apply_to_all':
			if os.path.exists('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
				save_json(filename='%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s/%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
				msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))			
			else:
				msinfo = load_json('%s/%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

			target_path = os.path.join(params['apply_to_all']['target_path'],"")

			target_files = get_target_files(target_dir=target_path,telescope=msinfo['TELE_NAME'],project_code=params['global']['project_code'],idifiles=[])

			tar = str(target_files['tar'])
			with open('target_files.txt', 'w') as f:
				for k in target_files.keys():
					if k != 'tar':
						f.write(tar+" "+k+" "+" ".join(target_files[k])+'\n')
			write_hpc_headers(step=i,params=params)
		else:
			write_hpc_headers(step=i,params=params)
		if i in ['import_fitsidi']:
			parallel=False
		elif ((steps['make_mms'] == 1)|(steps_run['make_mms']==1)):
			parallel=True
		elif i in ['prepare_data']:
			parallel=True
		else:
			parallel=False
		if i=='init_flag':
			if params['init_flag']['run_AOflag'] == False:
				write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag=False,casa6=casa6)
			else:
				write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag='both',casa6=casa6)
		elif i == 'apply_to_all':
			if (params["apply_to_all"]["hpc_options"]["nodes"] == 1)&(params["apply_to_all"]["hpc_options"]["cpus"] == 1):
				parallel = False
			write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag='apply_to_all',casa6=casa6)
		else:
			write_commands(step=i,inputs=inputs,params=params,parallel=parallel,aoflag=False,casa6=casa6)
		high_step = j

for j,i in enumerate(steps_run.keys()):
	if steps_run[i]==1:
		if (steps[i]==1) or (j>high_step):
			remove_gaintable(i,params,casa6)


jobs_to_run = []
for i in steps.keys():
	if steps[i]==1:
		jobs_to_run.append(i)
casalog.post(priority='INFO',origin=filename,message='Writing runfile script for steps: %s'%", ".join(jobs_to_run))
write_job_script(steps=jobs_to_run,job_manager=params['global']['job_manager'])