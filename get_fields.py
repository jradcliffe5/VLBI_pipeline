import inspect, os, sys, json, re
from collections import OrderedDict

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *

inputs = load_json('vp_inputs.json')
params = load_json(inputs['parameter_file'])
f2id_c = load_json('vp_fields_to_id.json')

try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

ids=sys.argv[i].split(',')
fields = []
for i in ids:
	fields.append(str(f2id_c['fieldtoID'][i]))
f = open("aoflag_temp.txt", "w")
f.write(",".join(fields))
f.close()
