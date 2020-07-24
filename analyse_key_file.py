import inspect, os, sys, json
import copy
## Python 2 will need to adjust for casa 6
import collections, optparse

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from VLBI_pipe_functions import *
from casavlbitools import key

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

try:
	# Python 2
	from StringIO import StringIO
except:
	# Python 3
	from io import StringIO

## Imports input_file
try:
	i = sys.argv.index("-c") + 2
except:
	i = 1
	pass

usage = "usage casa [options] -c / python analyse_keyfile.py <antab_file>"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i:])

print(args[0])
res = args[0]

keys = StringIO()
fp = open(args[0], 'r')
for line in fp:
    if line.startswith('!'):
        continue
    keys.write(line)
    if line.strip().endswith('/'):
        keys.seek(0)
        try:
            tsys = key.read_keyfile(keys)
        except RuntimeError:
            print("\n", keys.getvalue(), file=sys.stderr)
            sys.exit(1)
            pass
        print(tsys)
        keys = StringIO()
        continue
    continue