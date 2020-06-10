#! /usr/bin/env python
#
# Copyright (C) 2016, 2017
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
import optparse
import os
import sys

filename = inspect.getframeinfo(inspect.currentframe()).filename
sys.path.append(os.path.dirname(os.path.realpath(filename)))

from casavlbitools.fitsidi import convert_flags

if __name__ == "__main__":
    # Allow this scrupt to be invoked using casa -c
    try:
        i = sys.argv.index("-c") + 2
    except:
        i = 1
        pass

    usage = "usage %prog [options] uvflagfile fitsfile"
    parser = optparse.OptionParser(usage=usage)
    (options, args) = parser.parse_args(sys.argv[i:])
    convert_flags(infile=args[0],outfile=args[1], idifiles=args[2:])
