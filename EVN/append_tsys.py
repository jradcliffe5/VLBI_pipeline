#! /usr/bin/env python
#
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
import time as tm

import pyfits
import numpy as np

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
import key

class IdiHDU(pyfits.PrimaryHDU):
    @classmethod
    def match_header(cls, header):
        try:
            keyword = header.cards[0].keyword
        except:
            keyword = header.ascard[0].key
            pass
        return (keyword == 'SIMPLE' and 'GROUPS' in header and
                header['GROUPS'] == True and 'NAXIS' in header and
                header['NAXIS'] == 0)

pyfits.register_hdu(IdiHDU)

os.environ['TZ'] = 'UTC'
tm.tzset()

# Allow this scrupt to be invoked using casa -c
try:
    i = sys.argv.index("-c") + 2
except:
    i = 1
    pass

usage = "usage %prog [options] antabfile fitsfile"
parser = optparse.OptionParser(usage=usage)
(options, args) = parser.parse_args(sys.argv[i:])

# Check if we already have a SYSTEM_TEMPERATURES table
try:
    hdulist = pyfits.open(args[1])
    hdu = hdulist['SYSTEM_TEMPERATURE']
    print 'SYSTEM_TEMPERATURE table already present in FITS-IDI file'
    sys.exit(1)
except KeyError:
    pass

# Create an index
idx = []
source_id = -1
last_time = float("-inf")
first_time = float("inf")
for arg in args[1:]:
    hdulist = pyfits.open(arg)
    tbhdu = hdulist['UV_DATA']
    if 'SOURCE' in tbhdu.columns.names:
        source_id_col = 'SOURCE'
    else:
        source_id_col = 'SOURCE_ID'
        pass
    for data in tbhdu.data:
        jd = data['DATE']
        time = (jd - 2440587.5 + data['TIME']) * 86400
        if time > last_time:
            last_time = time
            pass
        if time < first_time:
            first_time = time
            pass
        if data[source_id_col] != source_id:
            source_id = data[source_id_col]
            idx.append((time, source_id))
            pass
        continue
    continue
idx.sort()

hdulist = pyfits.open(args[1], mode='append')
header = hdulist['ARRAY_GEOMETRY'].header
obscode = header['OBSCODE']
n_stokes = header['NO_STKD']
stk_1 = header['STK_1']
n_band = header['NO_BAND']
n_chan = header['NO_CHAN']
ref_freq = header['REF_FREQ']
chan_bw = header['CHAN_BW']
ref_pixl = header['REF_PIXL']
rdate = header['RDATE']

tbhdu = hdulist['ARRAY_GEOMETRY']
assert tbhdu.header['EXTVER'] == 1
antennas = [s.strip() for s in tbhdu.data['ANNAME']]
antenna_map = dict(zip(antennas, tbhdu.data['NOSTA']))

tbhdu = hdulist['FREQUENCY']
assert tbhdu.data['FREQID'][0] == 1
freqs = tbhdu.data['BANDFREQ'][0]
freqs = np.array(map (lambda x: x + ref_freq, freqs))
assert len(freqs) == n_band

tbhdu = hdulist['SOURCE']
if 'ID_NO.' in tbhdu.columns.names:
    source_id_col = 'ID_NO.'
else:
    source_id_col = 'SOURCE_ID'
    pass
source_map = dict(zip(tbhdu.data['SOURCE'], tbhdu.data[source_id_col]))

tupletime= tm.strptime(rdate, "%Y-%m-%d")
ref = tm.mktime(tupletime)

time = []
time_interval = []
source_id = []
antenna_no = []
array = []
freqid = []
tsys_1 = []
tsys_2 = []
tant = []

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
    if time < first_time or time > last_time:
        return -1
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

def process_values(infp, keys, pols):
    year = tupletime.tm_year
    antenna_name = find_antenna(keys[0], ['SRC/SYS'])
    if not antenna_name:
        print 'Antenna missing from TSYS group'
        skip_values(infp)
        return
    try:
        antenna = antenna_map[antenna_name]
    except:
        print 'Antenna %s not present in FITS-IDI file' % antenna_name
        skip_values(infp)
        return
    keys = dict(keys[0])
    spws = []
    spwmap = {}
    update_map(pols, spws, spwmap, keys['INDEX'])
    if 'INDEX2' in keys:
        update_map(pols, spws, spwmap, keys['INDEX2'])
        pass
    if len(spws) != n_band:
        print >>sys.stderr, \
            'INDEX for antenna %s does not match FITS-IDI file' % antenna_name
        sys.exit(1)
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
            t = tm.mktime(tm.strptime(t, "%Yy%jd%Hh%Mm%Ss"))
            days = (t + timeoff - ref) / 86400
            source = find_source(t)
            values = fields[2:]
            tsys = {'R': [], 'L': []}
            for spw in spws:
                for pol in ['R', 'L']:
                    try:
                        value = float(values[spwmap[(pol, spw)]])
                    except:
                        value = float("nan")
                        pass
                    tsys[pol].append(value)
                    continue
                continue
            if source != -1:
                time.append(days)
                time_interval.append(0.0)
                source_id.append(source)
                antenna_no.append(antenna)
                array.append(1)
                freqid.append(1)
                tsys_1.append(tsys['R'])
                tsys_2.append(tsys['L'])
                tant.append(n_band * [float('nan')])
                pass
            pass
        if line.strip().endswith('/'):
            break
        continue
    return

pols = []
keys = StringIO.StringIO()
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
            print >>sys.stderr, "\n", keys.getvalue()
            sys.exit(1)
        if tsys and tsys[0] and tsys[0][0][0] == 'TSYS':
            process_values(fp, tsys, pols)
            pass
        keys = StringIO.StringIO()
        continue
    continue

if len(pols) == 1 and pols[0] == 'L':
    tsys_1 = tsys_2
    pass

cols = []
col = pyfits.Column(name='TIME', format='1D', unit='DAYS', array=time)
cols.append(col)
col = pyfits.Column(name='TIME_INTERVAL', format='1E', unit='DAYS', array=time_interval)
cols.append(col)
col = pyfits.Column(name='SOURCE_ID', format='1J', array=source_id)
cols.append(col)
col = pyfits.Column(name='ANTENNA_NO', format='1J', array=antenna_no)
cols.append(col)
col = pyfits.Column(name='ARRAY', format='1J', array=array)
cols.append(col)
col = pyfits.Column(name='FREQID', format='1J', array=freqid)
cols.append(col)
format = '%dE' % n_band
col = pyfits.Column(name='TSYS_1', format=format, unit='K', array=tsys_1)
cols.append(col)
col = pyfits.Column(name='TANT_1', format=format, unit='K', array=tant)
cols.append(col)
if len(pols) > 1:
    col = pyfits.Column(name='TSYS_2', format=format, unit='K', array=tsys_2)
    cols.append(col)
    col = pyfits.Column(name='TANT_2', format=format, unit='K', array=tant)
    cols.append(col)
    pass
coldefs = pyfits.ColDefs(cols)

header = pyfits.Header()
try:
    # Attempt to use the new interfaces available in PyFITS 3.1.x and
    # later.  The old interfaces are still available, but generate
    # warnings that say they're deprecated.
    header['EXTNAME'] = 'SYSTEM_TEMPERATURE'
    header['EXTVER'] = 1
    header['TABREV'] = 1
    header['OBSCODE'] = obscode
    header['NO_STKD'] = n_stokes
    header['STK_1'] = stk_1
    header['NO_BAND'] = n_band
    header['NO_CHAN'] = n_chan
    header['REF_FREQ'] = ref_freq
    header['CHAN_BW'] = chan_bw
    header['REF_PIXL'] = ref_pixl
    # Repeat the reference data even though the FITS-IDI standard doesn't
    # seem to require it.
    header['RDATE'] = rdate
    header['NO_POL'] = len(pols)
    tbhdu = pyfits.BinTableHDU.from_columns(coldefs, header)
except:
    # Fall back on the old interfaces available in PyFits 3.0.x and
    # earlier.
    header.update('EXTNAME', 'SYSTEM_TEMPERATURE')
    header.update('EXTVER', 1)
    header.update('TABREV', 1)
    header.update('OBSCODE', obscode)
    header.update('NO_STKD', n_stokes)
    header.update('STK_1', stk_1)
    header.update('NO_BAND', n_band)
    header.update('NO_CHAN', n_chan)
    header.update('REF_FREQ', ref_freq)
    header.update('CHAN_BW', chan_bw)
    header.update('REF_PIXL', ref_pixl)
    # Repeat the reference data even though the FITS-IDI standard doesn't
    # seem to require it.
    header.update('RDATE', rdate)
    header.update('NO_POL', len(pols))
    rows = len(tsys_1)
    tbhdu = pyfits.core.new_table(coldefs, header, rows, False, 'BinTableHDU')
    pass

hdulist.append(tbhdu)
hdulist.close()
