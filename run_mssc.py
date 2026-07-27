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
casalog.origin('vp_mssc')

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
target_outpath = os.path.join(params['apply_to_all']['target_outpath'],"")
msfile= '%s.ms'%(params['global']['project_code'])
p_c=params['global']['project_code']

if os.path.exists('%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))==False:
	casalog.post(origin=filename,message='No cached msinfo found ... generating %s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']),priority='INFO')
	save_json(filename='%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']), array=get_ms_info('%s%s.ms'%(params['global']['cwd'],params['global']['project_code'])), append=False)
else:
	msinfo = load_json('%s%s_msinfo.json'%(params['global']['cwd'],params['global']['project_code']))

if steps_run['make_mms'] == 1:
	parallel = True
else:
	parallel = False

reader = csv.reader(open("%starget_files.txt"%cwd), delimiter=" ")
target_files = list(reader)
casalog.post(origin=filename,message='Preparing %d target dataset(s) for source-subtracted self-cal (tar_ms_only=%s)'%(len(target_files),params["apply_to_all"]["tar_ms_only"]),priority='INFO')
## First step is to convert to fits
for i in len(target_files):
	casalog.post(origin=filename,message='Extracting pre-mssc images/data for target: %s'%target_files[i][1],priority='INFO')
	if params["apply_to_all"]["tar_ms_only"] == True:
		os.system("cp -r %s%s*_initial.image %s"%(target_outpath,target_files[i][1],cwd))
		image = glob.glob('%s%s*image'%(cwd,target_files[i][1]))
		for j in len(image):
			exportfits(imagename=image[j], fitsimage='%s%s_premssc_%d.fits'%(cwd,target_files[i][1],j),overwrite=True)
		rmdirs(image)
	else:
		files = extract_tarfile(tar_file='%s%s.ms.tar.gz'%(target_outpath,target_files[i][1]), cwd=cwd,delete_tar=False)
		image = glob.glob('%s%s*image'%(cwd,target_files[i][1]))
		for j in len(image):
			exportfits(imagename=image[j], fitsimage='%s%s_premssc_%d.fits'%(cwd,target_files[i][1],j),overwrite=True)
		rmdirs(image)
		rmdirs(files)

## Then catalogue
if params['mssc']['source_finder'] == "pybdsf":
	casalog.post(origin=filename,message='Running PyBDSF source cataloguing (detection_thresh=%s)'%params['mssc']['detection_thresh'],priority='INFO')
	run_cataloger_pybdsf(sn_ratio=params['mssc']['detection_thresh'],postfix='premssc')
else:
	casalog.post(origin=filename,message='Unsupported source_finder %s ... exiting'%params['mssc']['source_finder'],priority='SEVERE')
	sys.exit()

## Then to image all of the data sets and uvsub the uv data

## Then to concat data sets and image again.