import inspect, os, sys, json, re, csv, glob
from collections import OrderedDict
import tarfile

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
mpipath = os.path.dirname(os.path.realpath(filename))

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
casalog.origin('vp_apply_to_all')

try:
	if casa6 == True:
		from casampi.MPICommandClient import MPICommandClient
	else:
		from mpi4casa.MPICommandClient import MPICommandClient
	client = MPICommandClient()
	client.set_log_mode('redirect')
	client.start_services()
	parallel=True
	cmd = []
except:
	parallel=False


inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file_path'])
steps_run = load_json('vp_steps_run.json', Odict=True, casa6=casa6)
gaintables = load_gaintables(params, casa6=casa6)
gt_r = load_json('vp_gaintables.last.json', Odict=True, casa6=casa6)
gt_r['apply_to_all'] = {'gaintable':[],'gainfield':[],'spwmap':[],'interp':[]}

cwd = os.path.join(params['global']['cwd'],"")
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	save_json(filename='%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

if steps_run['make_mms'] == 1:
	parallel = True
else:
	parallel = False

reader = csv.reader(open("%starget_files.txt"%cwd), delimiter=" ")
target_files = list(reader)
## First step is to convert to fits
for i in len(target_files):
	if params["apply_to_all"]["tar_ms_only"] == True:
		os.system("cp -r %s*_initial.image %s"%(target_files[i][1],cwd))
		image = glob.glob('%s%s*image'%(cwd,target_files[i][1]))
		for j in len(image):
			exportfits(imagename=image[j], fitsimage='%s%s_premssc_%d.fits'%(cwd,target_files[i][1],j),overwrite=True)
			os.system('rm -r %s'%image[j])
	else:
		os.system("cp -r %s.ms.tar.gz %s"%(target_files[i][1],cwd))

## Then catalogue

## Then to image all of the data sets and uvsub the uv data

## Then to concat data sets and image again.