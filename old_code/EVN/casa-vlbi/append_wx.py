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
from __future__ import print_function
import inspect
import math
import os
import optparse
import sys
import time as tm

try:
    # Python 2
    from StringIO import StringIO
except:
    # Python 3
    from io import StringIO

import numpy as np

try:
    import astropy.io.fits as pyfits
except:
    import pyfits

os.environ['TZ'] = 'UTC'
tm.tzset()

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))
from casavlbitools import key

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

class IdiData:
    def __init__(self, idifiles):
        hdulist = pyfits.open(idifiles[0])

        # Fundamentals
        header = hdulist['ARRAY_GEOMETRY'].header
        self.obscode = header['OBSCODE']
        self.n_stokes = header['NO_STKD']
        self.stk_1 = header['STK_1']
        self.n_band = header['NO_BAND']
        self.n_chan = header['NO_CHAN']
        self.ref_freq = header['REF_FREQ']
        self.chan_bw = header['CHAN_BW']
        self.ref_pixl = header['REF_PIXL']
        self.rdate = header['RDATE']

        # Create antenna mapping
        tbhdu = hdulist['ARRAY_GEOMETRY']
        assert tbhdu.header['EXTVER'] == 1
        antennas = [s.strip() for s in tbhdu.data['ANNAME']]
        self.antenna_map = dict(zip(antennas, tbhdu.data['NOSTA']))

        # Create list of frequencies
        tbhdu = hdulist['FREQUENCY']
        assert tbhdu.data['FREQID'][0] == 1
        freqs = tbhdu.data['BANDFREQ'][0]
        self.freqs = np.array([x + self.ref_freq for x in freqs])
        assert len(self.freqs) == self.n_band

        # Create source mapping
        tbhdu = hdulist['SOURCE']
        if 'ID_NO.' in tbhdu.columns.names:
            source_id_col = 'ID_NO.'
        else:
            source_id_col = 'SOURCE_ID'
            pass
        self.source_map = dict(zip(tbhdu.data['SOURCE'],
                                   tbhdu.data[source_id_col]))

        # Reference date in convenient form
        tupletime = tm.strptime(self.rdate, "%Y-%m-%d")
        self.reftime = tm.mktime(tupletime)

        # Create an index
        self.idx = []
        source_id = -1
        self.last_time = float("-inf")
        self.first_time = float("inf")
        for idifile in idifiles:
            hdulist = pyfits.open(idifile)
            tbhdu = hdulist['UV_DATA']
            if 'SOURCE' in tbhdu.columns.names:
                source_id_col = 'SOURCE'
            else:
                source_id_col = 'SOURCE_ID'
                pass
            for data in tbhdu.data:
                jd = data['DATE']
                time = (jd - 2440587.5 + data['TIME']) * 86400
                if time > self.last_time:
                    self.last_time = time
                    pass
                if time < self.first_time:
                    self.first_time = time
                    pass
                if data[source_id_col] != source_id:
                    source_id = data[source_id_col]
                    self.idx.append((time, source_id))
                    pass
                continue
            continue
        self.idx.sort()
        return

    def find_source(self, time):
        if time < self.first_time or time > self.last_time:
            return -1
        source_id = -1
        i = 0
        try:
            while time >= self.idx[i][0]:
                source_id = self.idx[i][1]
                i += 1
                continue
        except:
            pass
        return source_id

class WXTable:
    def __init__(self):
        self.time = []
        self.time_interval = []
        self.antenna_no = []
        self.temperature = []
        self.pressure = []
        self.dewpoint = []
        self.wind_velocity = []
        self.wind_direction = []
        self.wind_gust = []
        self.precipitation = []
        self.wvr_h2o = []
        self.ionos_electron = []
        return


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

def process_values(infp, keys, idi, data):
    year = tm.gmtime(idi.reftime).tm_year
    antenna_name = find_antenna(keys[0], [])
    if not antenna_name:
        print('Antenna missing from WEATHER group')
        skip_values(infp)
        return
    try:
        antenna = antenna_map[antenna_name]
    except:
        print('Antenna %s not present in FITS-IDI file' % antenna_name)
        skip_values(infp)
        return
    keys = dict(keys[0])
    for line in infp:
        if line.startswith('!'):
            continue
        fields = line.split()
        if len(fields) > 1:
            timecode = fields[0].split('-')
            tm_year = year
            tm_yday = int(timecode[0])
            tm_hour = int(timecode[1].split(':')[0])
            tm_min = math.modf(float(timecode[1].split(':')[1]))
            tm_sec = int(60 * tm_min[0])
            tm_min = int(tm_min[1])
            t = "%dy%03dd%02dh%02dm%02ds" % \
                (tm_year, tm_yday, tm_hour, tm_min, tm_sec)
            t = tm.mktime(tm.strptime(t, "%Yy%jd%Hh%Mm%Ss"))
            days = (t - idi.reftime) / 86400
            values = fields[1:]

            if t >= idi.first_time and t <= idi.last_time:
                data.time.append(days)
                data.time_interval.append(0.0)
                data.antenna_no.append(antenna)
                data.temperature.append(float(values[0]))
                data.pressure.append(float(values[1]))
                data.dewpoint.append(float(values[2]))
                data.wind_velocity.append(float(values[3]))
                data.wind_direction.append(float(values[4]))
                data.precipitation.append(float(values[5]))
                data.wind_gust.append(float(values[6]))
                data.wvr_h2o.append(float('nan'))
                data.ionos_electron.append(float('nan'))
                pass
            pass
        if line.strip().endswith('/'):
            break
        continue
    return

def append_wx(wxfile, idifiles):
    # Check if we already have a WEATHER table
    try:
        hdulist = pyfits.open(idifiles[0])
        hdu = hdulist['WEATHER']
        print('WEATHER table already present in FITS-IDI file')
        sys.exit(1)
    except KeyError:
        pass

    idi = idiData(idifiles)
    data = WXTable()

    keys = StringIO()
    fp = open(args[0], 'r')
    for line in fp:
        if line.startswith('!'):
            continue
        keys.write(line)
        if line.strip().endswith('/'):
            keys.seek(0)
            try:
                wx = key.read_keyfile(keys)
            except RuntimeError:
                print("\n", keys.getvalue(), file=sys.stderr)
                sys.exit(1)
                pass
            if wx and wx[0] and wx[0][0][0] == 'WEATHER':
                process_values(fp, wx, idi, data)
                pass
            keys = StringIO()
            continue
        continue

    time = data.time
    time_interval = data.time_interval
    antenna_no = data.antenna_no
    temperature = data.temperature
    pressure = data.pressure
    dewpoint = data.dewpoint
    wind_velocity = data.wind_velocity
    wind_direction = data.wind_direction
    wind_gust = data.wind_gust
    data.precipitation = data.precipitation
    wvr_h20 = data.wvr_h2o
    ionos_electron = data.ionos_electron

    cols = []
    col = pyfits.Column(name='TIME', format='1D', unit='DAYS', array=time)
    cols.append(col)
    col = pyfits.Column(name='TIME_INTERVAL', format='1E', unit='DAYS',
                        array=time_interval)
    cols.append(col)
    col = pyfits.Column(name='ANTENNA_NO', format='1J', array=antenna_no)
    cols.append(col)
    col = pyfits.Column(name='TEMPERATURE', format='1E', unit='CENTIGRADE',
                        array=temperature)
    cols.append(col)
    col = pyfits.Column(name='PRESSURE', format='1E', unit='MILLIBARS',
                        array=pressure)
    cols.append(col)
    col = pyfits.Column(name='DEWPOINT', format='1E', unit='CENTIGRADE',
                        array=dewpoint)
    cols.append(col)
    col = pyfits.Column(name='WIND_VELOCITY', format='1E', unit='M/SEC',
                        array=wind_velocity)
    cols.append(col)
    col = pyfits.Column(name='WIND_DIRECTION', format='1E', unit='DEGREES',
                        array=wind_direction)
    cols.append(col)
    col = pyfits.Column(name='WIND_GUST', format='1E', unit='M/SEC',
                        array=wind_gust)
    cols.append(col)
    col = pyfits.Column(name='PRECIPITATION', format='1E', unit='CM',
                        array=precipitation)
    cols.append(col)
    col = pyfits.Column(name='WVR_H2O', format='1E', array=wvr_h2o)
    cols.append(col)
    col = pyfits.Column(name='IONOS_ELECTRON', format='1E', array=ionos_electron)
    cols.append(col)
    coldefs = pyfits.ColDefs(cols)

    header = pyfits.Header()
    try:
        # Attempt to use the new interfaces available in PyFITS 3.1.x and
        # later.  The old interfaces are still available, but generate
        # warnings that say they're deprecated.
        header['EXTNAME'] = 'WEATHER'
        header['EXTVER'] = 1
        header['TABREV'] = 1
        header['OBSCODE'] = idi.obscode
        header['NO_STKD'] = idi.n_stokes
        header['STK_1'] = idi.stk_1
        header['NO_BAND'] = idi.n_band
        header['NO_CHAN'] = idi.n_chan
        header['REF_FREQ'] = idi.ref_freq
        header['CHAN_BW'] = idi.chan_bw
        header['REF_PIXL'] = idi.ref_pixl
        # Repeat the reference data even though the FITS-IDI standard doesn't
        # seem to require it.
        header['RDATE'] = idi.rdate
        tbhdu = pyfits.BinTableHDU.from_columns(coldefs, header)
    except:
        # Fall back on the old interfaces available in PyFits 3.0.x and
        # earlier.
        header.update('EXTNAME', 'WEATHER')
        header.update('EXTVER', 1)
        header.update('TABREV', 1)
        header.update('OBSCODE', idi.obscode)
        header.update('NO_STKD', idi.n_stokes)
        header.update('STK_1', idi.stk_1)
        header.update('NO_BAND', idi.n_band)
        header.update('NO_CHAN', idi.n_chan)
        header.update('REF_FREQ', idi.ref_freq)
        header.update('CHAN_BW', idi.chan_bw)
        header.update('REF_PIXL', idi.ref_pixl)
        # Repeat the reference data even though the FITS-IDI standard doesn't
        # seem to require it.
        header.update('RDATE', idi.rdate)
        rows = len(temperature)
        tbhdu = pyfits.core.new_table(coldefs, header, rows, False, 'BinTableHDU')
        pass

    hdulist = pyfits.open(idifiles[0], mode='append')
    hdulist.append(tbhdu)
    hdulist.close()
    return

if __name__ == "__main__":
    # Allow this scrupt to be invoked using casa -c
    try:
        i = sys.argv.index("-c") + 2
    except:
        i = 1
        pass

    usage = "usage %prog [options] wxfile fitsfile"
    parser = optparse.OptionParser(usage=usage)
    (options, args) = parser.parse_args(sys.argv[i:])
    append_wx(args[0], args[1:])
