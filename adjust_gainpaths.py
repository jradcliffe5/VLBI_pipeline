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
casalog.origin('vp_adjust_gainpaths')

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

try:
	i = sys.argv[i]
except:
	params = load_json(inputs['parameter_file_path'])
	i = params['global']['cwd']
if i.endswith('/'):
		i = i[:-1]
		print(i)
gaintables = load_json('vp_gaintables.json', Odict=True, casa6=casa6)
save_json(filename='%s/vp_gaintables.old.json'%(params['global']['cwd']), array=gaintables, append=False)

for k,j in enumerate(gaintables['gaintable']):
	gaintables['gaintable'][k] = "%s/%s"%(i,j.split('/')[-1])

save_json(filename='%s/vp_gaintables.json'%(params['global']['cwd']), array=gaintables, append=False)
