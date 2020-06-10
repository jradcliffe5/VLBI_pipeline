#! /usr/bin/env python
#
# Copyright (C) 2019
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
import time as tm

import pyfits
import numpy as np

os.environ['TZ'] = 'UTC'
tm.tzset()

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

def transform_poly(coeff, min_elev=0, max_elev=90):
    f = np.poly1d(coeff[::-1])
    g = lambda x: np.sqrt(f(90 - x))
    x = np.linspace(min_elev, max_elev, 64, endpoint=True)
    y = g(x)
    return np.poly1d(np.polyfit(x, y, 3))

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

i = sys.argv.index("-c")

usage = "usage %prog [options] fitsfile gcfile"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-l", "--min-elevation", type="float", dest="min",
                  help="minimum elevation", default=0)
parser.add_option("-u", "--max-elevation", type="float", dest="max",
                  help="maximum elevation", default=90)
(options, args) = parser.parse_args(sys.argv[i+2:])
if len(args) != 2:
    parser.error("incorrect number of arguments")

tb = casac.table()

outfp = tempfile.NamedTemporaryFile('w')

t = time.strptime("2000y01d00h00m00s", "%Yy%jd%Hh%Mm%Ss")
btime = time.mktime(t) + 40587.0 * 86400
t = time.strptime("2100y01d00h00m00s", "%Yy%jd%Hh%Mm%Ss")
etime = time.mktime(t) + 40587.0 * 86400

hdulist = pyfits.open(args[0])

tbhdu = hdulist['ARRAY_GEOMETRY']
assert tbhdu.header['EXTVER'] == 1
antennas = [s.strip() for s in tbhdu.data['ANNAME']]

tbhdu = hdulist['GAIN_CURVE']
header = tbhdu.header
n_band = header['NO_BAND']
n_pol = header['NO_POL']
n_tab = header['NO_TABS']

dpfu = {}
for data in tbhdu.data:
    antenna_no = data['ANTENNA_NO']
    type_1 = data['TYPE_1']
    gain_1 = data['GAIN_1']
    sens_1 = data['SENS_1']
    if n_pol > 1:
        type_2 = data['TYPE_2']
        gain_2 = data['GAIN_2']
        sens_2 = data['SENS_2']
    else:
        type_2 = type_1
        gain_2 = gain_1
        sens_2 = sens_1
        pass
    if n_band == 1:
        type_1 = [type_1]
        type_2 = [type_2]
        sens_1 = [sens_1]
        sens_2 = [sens_2]
        pass
    gain_1 = gain_1.reshape(n_band, n_tab)
    gain_2 = gain_2.reshape(n_band, n_tab)
    if type_1[0] != 2:
        print 'Unsupported gain curve type %' % type_1[0]
        sys.exit(1)
        pass
    if type_2[0] != 2:
        print 'Unsupported gain curve type %' % type_2[0]
        sys.exit(1)
        pass
    for index in range(n_band):
        if type_1[index] != type_1[0] or type_2[index] != type_1[0]:
            print 'Mismatched gain curve types'
            sys.exit(1)
            pass
        if sens_1[index] != sens_1[0] or sens_2[index] != sens_2[0]:
            print 'Mismatched sensitivity'
            sys.exit(1)
            pass
        if not np.array_equal(gain_1[index], gain_1[0]) or \
                not np.array_equal(gain_2[index],gain_2[0]):
            print 'Mismatched gain values'
            sys.exit(1)
            pass

    antenna = antennas[antenna_no - 1]

    dpfu = {}
    dpfu['R'] = sens_1[0]
    dpfu['L'] = sens_2[0]

    poly = {}
    poly['R'] = transform_poly(gain_1[0], options.min, options.max)
    poly['L'] = transform_poly(gain_2[0], options.min, options.max)

    print >> outfp, "C", 0, 1e12,
    print >> outfp, btime, etime,
    print >> outfp, antenna,

    for pol in ['R', 'L']:
        for i in xrange(4):
            try:
                value = poly[pol][i] * math.sqrt(dpfu[pol])
            except:
                value = 0.0
            print >> outfp, value,
            continue
        continue
    print >> outfp
    continue

outfp.flush()

tb.fromascii(args[1], asciifile=outfp.name, sep=' ',
             columnnames=columnnames, datatypes=datatypes)

outfp.close()

hdulist.close()
