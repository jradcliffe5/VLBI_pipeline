# Copyright (C) 2016
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
from casac import casac

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
import key

os.environ['TZ'] = 'UTC'
time.tzset()

columnnames = [
    "BANDNAME",
    "BFREQ",
    "EFREQ",
    "BTIME",
    "ETIME",
    "ANTENNA",
    "GAIN"
]

datatypes = [
    "A",
    "D",
    "D",
    "D",
    "D",
    "A",
    "R4,2"
]

vlba_freqs = {
    '90cm': [ 0.312, 0.342 ],
    '50cm': [ 0.596, 0.626 ],
    '21cm': [ 1.35, 1.548 ],
    '18cm': [ 1.548, 1.75 ],
    '13cm': [ 2.2, 2.4 ],
    '13cmsx': [ 2.2, 2.4 ],
    '6cm': [ 3.9, 5.828 ],
    '7ghz': [ 5.828, 7.9 ],
    '4cm': [ 8.0, 8.8],
    '4cmsx': [ 8.0, 8.8 ],
    '2cm': [ 12.0, 15.4 ],
    '1cm': [ 21.7, 23.018 ],
    '24ghz': [ 23.018, 24.1 ],
    '7mm': [ 41.0, 45.0 ],
    '3mm': [ 80.0, 90.0 ]
}

keyin_keys = [ 'EQUAT', 'ALTAZ', 'ELEV', 'GCNRAO', 'TABLE', 'RCP', 'LCP' ]

def transform_poly(coeff, min_elev=0, max_elev=90):
    f = np.poly1d(coeff[::-1])
    g = lambda x: np.sqrt(f(90 - x))
    x = np.linspace(min_elev, max_elev, 64, endpoint=True)
    y = g(x)
    return np.poly1d(np.polyfit(x, y, 3))

def skip_values(infp):
    for line in infp:
        if line.startswith('!'):
            continue
        if line.strip().endswith('/'):
            break
        continue
    return

def parse_timerange(timerange):
    t = (int(timerange[0]), int(timerange[1]), int(timerange[2]),
         int(timerange[3]), 0, 0, 0, 0, 0)
    return time.mktime(t) + 40587.0 * 86400

def find_antenna(keys, ignore):
    for key in keys[1:]:
        if not type(key[1]) is bool:
            continue
        if key[0] in ignore:
            continue
        return key[0]
    return None

i = sys.argv.index("-c")

usage = "usage %prog [options] antabfile gcfile"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-l", "--min-elevation", type="float", dest="min",
                  help="minimum elevation", default=0)
parser.add_option("-u", "--max-elevation", type="float", dest="max",
                  help="maximum elevation", default=90)
(options, args) = parser.parse_args(sys.argv[i+2:])
if len(args) != 2:
    parser.error("incorrect number of arguments")

antab = args[0]
gc = args[1]

tb = casac.table()

outfp = tempfile.NamedTemporaryFile('w')

t = time.strptime("2000y01d00h00m00s", "%Yy%jd%Hh%Mm%Ss")
btime = time.mktime(t) + 40587.0 * 86400
t = time.strptime("2100y01d00h00m00s", "%Yy%jd%Hh%Mm%Ss")
etime = time.mktime(t) + 40587.0 * 86400

def gain_common(gain, antenna, band, bfreq, efreq, btime, etime, outfp):
    print >> outfp, band, bfreq, efreq,
    print >> outfp, btime, etime,
    print >> outfp, antenna,
    dpfu = {}
    try:
        dpfu['R'] = gain['DPFU'][0]
        dpfu['L'] = gain['DPFU'][1]
    except:
        dpfu['R'] = dpfu['L'] = gain['DPFU']
        pass
    try:
        value = gain['POLY'][0]
    except:
        gain['POLY'] = [gain['POLY']]
        pass
    poly = transform_poly(gain['POLY'], options.min, options.max)
    for pol in ['R', 'L']:
        for i in xrange(4):
            try:
                value = poly[i] * math.sqrt(dpfu[pol])
            except:
                value = 0.0
                pass
            print >> outfp, value,
            continue
        continue
    print >> outfp
    return

keys = StringIO.StringIO()
fp = open(antab, 'r')
for line in fp:
    if line.startswith('!'):
        continue
    keys.write(line)
    if line.strip().endswith('/'):
        keys.seek(0)
        gain = key.read_keyfile(keys)
        # Standard ANTAB
        if gain and gain[0] and gain[0][0][0] == 'GAIN':
            antenna = find_antenna(gain[0], keyin_keys)
            gain = dict(gain[0])
            try:
                bfreq = gain['FREQ'][0] * 1e6
            except:
                bfreq = 0
                pass
            try:
                efreq = gain['FREQ'][1] * 1e6
            except:
                efreq = 1e12
                pass
            gain_common(gain, antenna, "C", bfreq, efreq, btime, etime, outfp)
        # VLBA gains file
        elif gain and gain[0] and gain[0][0][0] == 'BAND':
            antenna = gain[0][8][0]
            gain = dict(gain[0])
            timerange = gain['TIMERANG']
            btime = parse_timerange(timerange[0:])
            etime = parse_timerange(timerange[4:])
            band = gain['BAND']
            try:
                freq = vlba_freqs[band]
                bfreq = freq[0] * 1e9
                efreq = freq[1] * 1e9
            except:
                freq = gain['FREQ']
                bfreq = freq - freq / 4
                efreq = freq + freq / 4
                pass
            gain_common(gain, antenna, band, bfreq, efreq, btime, etime, outfp)
        elif gain and gain[0] and gain[0][0][0] == 'TSYS':
            skip_values(fp)
            pass
        keys = StringIO.StringIO()
        continue
    continue

outfp.flush()

tb.fromascii(gc, asciifile=outfp.name, sep=' ',
             columnnames=columnnames, datatypes=datatypes)

outfp.close()
fp.close()
