# Copyright (C) 2018
# Joint Institute for VLBI ERIC, Dwingeloo, The Netherlands
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
import inspect
import math
import os
import optparse
import StringIO
import sys
import tempfile
import time

import numpy as np
import scipy
from casac import casac

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
from casavlbitools import key

os.environ['TZ'] = 'UTC'
time.tzset()

i = sys.argv.index("-c")

usage = "usage %prog [options] antabfile measurementset"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i+2:])
if len(args) != 2:
    parser.error("incorrect number of arguments")

antab = args[0]
vis = args[1]

tb = casac.table()

columnnames = [
    "ANTENNA_ID",
    "ARRAY_ID",
    "FEED_ID",
    "INTERVAL",
    "SPECTRAL_WINDOW_ID",
    "TIME",
    "NUM_RECEPTORS",
    "TSYS"
]

datatypes = [
    "I",
    "I",
    "I",
    "D",
    "I",
    "D",
    "I",
    "R2"
]

tsys_values = {}
tsys_times = {}

def update_map(pols, spws, spwmap, index):
    idx = 0
    if not isinstance(index, (list, tuple)):
        index = [index]
        pass
    for labels in index:
        for label in labels.split('|'):
            pol = label[0]
            rng = label[1:].split(':')
            if pol != 'X':
                if not pol in pols:
                    pols.append(pol)
                    pass
                if len(rng) == 1:
                    rng.append(rng[0])
                    pass
                rng = [int(x) - 1 for x in rng]
                for spw in range(rng[0], rng[1] + 1):
                    if not spw in spws:
                        spws.append(spw)
                        pass
                    spwmap[(pol, spw)] = idx
                    continue
                pass
            continue
        idx += 1
        continue
    spws = sorted(spws)
    return

def find_source(time):
    source_id = -1
    i = 0
    try:
        while time >= idx[i][0]:
            source_id = idx[i][1]
            i += 1
            continue
    except:
        pass
    return source_id

def find_antenna(keys, ignore):
    for key in keys[1:]:
        if not type(key[1]) is bool:
            continue
        if key[0] in ignore:
            continue
        return key[0]
    return None

def skip_values(infp):
    for line in infp:
        if line.startswith('!'):
            continue
        if line.strip().endswith('/'):
            break
        continue
    return

def process_values(infp, keys, pols, vis):
    tb.open(vis)
    secs = tb.getcell('TIME') - (40587 * 86400)
    year = time.gmtime(secs).tm_year
    tb.close()
    tb.open(vis + '/ANTENNA')
    namelist = tb.getcol("NAME").tolist()
    tb.close()
    antenna_name = find_antenna(keys[0], ['SRC/SYS'])
    if not antenna_name:
        print 'Antenna missing from TSYS group'
        skip_values(infp)
        return
    try:
        antenna = namelist.index(antenna_name)
    except:
        print 'Antenna %s not present in MeasurementSet' % antenna_name
        skip_values(infp)
        return
    keys = dict(keys[0])
    scan = 0
    spws = []
    spwmap = {}
    update_map(pols, spws, spwmap, keys['INDEX'])
    if 'INDEX2' in keys:
        update_map(pols, spws, spwmap, keys['INDEX2'])
        pass
    timeoff = 0
    if 'TIMEOFF' in keys:
        timeoff = float(keys['TIMEOFF'])
    for line in infp:
        if line.startswith('!'):
            continue
        fields = line.split()
        if len(fields) > 1:
            tm_year = year
            tm_yday = int(fields[0])
            tm_hour = int(fields[1].split(':')[0])
            tm_min = math.modf(float(fields[1].split(':')[1]))
            tm_sec = int(60 * tm_min[0])
            tm_min = int(tm_min[1])
            t = "%dy%03dd%02dh%02dm%02ds" % \
                (tm_year, tm_yday, tm_hour, tm_min, tm_sec)
            t = time.strptime(t, "%Yy%jd%Hh%Mm%Ss")
            secs = time.mktime(t) + timeoff
            values = fields[2:]
            secs = secs + (40587.0 * 86400)
            if secs <= scan_times[-1][1]:
                while secs > scan_times[scan][1]:
                    scan += 1
                    continue
                for pol in pols:
                    for spw in spws:
                        idx = (antenna, scan, spw)
                        if not idx in tsys_values:
                            tsys_values[idx] = {}
                            tsys_times[idx] = {}
                            pass
                        if not pol in tsys_values[idx]:
                            tsys_values[idx][pol] = []
                            tsys_times[idx][pol] = []
                            pass
                        try:
                            value = float(values[spwmap[(pol, spw)]])
                            if value > 0:
                                tsys_values[idx][pol].append(value)
                                tsys_times[idx][pol].append(secs)
                                pass
                        except:
                            pass
                        continue
                    continue
                pass
            pass
        if line.strip().endswith('/'):
            break
        continue
    return

def write_values(outfp):
    pols = ['R', 'L']

    keys = tsys_values.keys()
    for idx in sorted(keys):
        antenna = idx[0]
        scan = idx[1]
        spw = idx[2]
        x = tsys_times[idx]
        y = tsys_values[idx]
        for pol in pols:
            if len(y[pol]) == 0:
                x[pol] = [(scan_times[scan][0] + scan_times[scan][1]) / 2]
                y[pol] = [-1.0]
                pass
            continue

        secs = scan_times[scan][0]
        while secs <= scan_times[scan][1]:
            # ANTENNA_ID
            print >> outfp, antenna,
            # ARRAY_ID
            print >> outfp, 0,
            # FEED_ID
            print >> outfp, 0,
            # INTERVAL
            print >> outfp, 0,
            # SPECTRAL_WINDOW_ID
            print >> outfp, spw,
            # TIME
            print >> outfp, secs,
            # NUM_RECEPTORS
            print >> outfp, 2,
            # TSYS
            for pol in pols:
                print >> outfp, scipy.interp(secs, x[pol], y[pol]),
                continue
            print >> outfp
            secs += 30
            continue
        continue
    return

ms.open(vis)
scans = ms.getscansummary()
ms.close()

scan_times = []
for scan in scans:
    integration_time = scans[scan]['0']['IntegrationTime']
    start = scans[scan]['0']['BeginTime'] * 86400 - integration_time
    end = scans[scan]['0']['EndTime'] * 86400 + integration_time
    scan_times.append([start, end])
scan_times = sorted(scan_times)

outfp = tempfile.NamedTemporaryFile('w')

pols = []
keys = StringIO.StringIO()
fp = open(antab, 'r')
for line in fp:
    if line.startswith('!'):
        continue
    keys.write(line)
    if line.strip().endswith('/'):
        keys.seek(0)
        try:
            tsys = key.read_keyfile(keys)
        except RuntimeError:
            print >>sys.stderr, "\n", keys.getvalue()
            sys.exit(1)
        if tsys[0][0][0] == 'TSYS':
            process_values(fp, tsys, pols, vis)
            pass
        keys = StringIO.StringIO()
        continue
    continue

write_values(outfp)

outfp.flush()

tb.open(vis)
unit = tb.getcolkeyword("TIME", "QuantumUnits")
meas = tb.getcolkeyword("TIME", "MEASINFO")
tb.close()

tb.fromascii(tablename=vis + '/SYSCAL', asciifile=outfp.name, sep=' ',
             columnnames=columnnames, datatypes=datatypes)
tb.open(vis + '/SYSCAL', nomodify=False)
tb.putcolkeyword("INTERVAL", "QuantumUnits", unit)
tb.putcolkeyword("TIME", "QuantumUnits", unit)
tb.putcolkeyword("TIME", "MEASINFO", meas)
tb.putcolkeyword("TSYS", "QuantumUnits", "K")
tb.close()

tb.open(vis, nomodify=False)
tb.putkeyword('SYSCAL', 'Table: ' + vis + '/SYSCAL')
tb.close()

outfp.close()
fp.close()
