import optparse

import scipy as sp
import numpy as np

from astropy.utils import iers
from astropy.table import Table
from astropy.time import Time
from astropy import constants
from astropy import units
from astropy import _erfa as erfa
from scipy.interpolate import interp1d

#import matplotlib.pyplot as plt
import pyfits

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

usage = "usage %prog [options] fitsfile ms caltable"
parser = optparse.OptionParser(usage=usage)
parser.add_option("-e", "--eop-file", type="string", dest="eopfile",
                  help="file with EOPs to use")
(options, args) = parser.parse_args(sys.argv[i+2:])
if len(args) != 3:
    parser.error("incorrect number of arguments")

hdulist = pyfits.open(args[0])

tbhdu = hdulist['CALC']
assert tbhdu.header['EXTVER'] == 1
rdate = Time(tbhdu.header['RDATE'])

cmjd = (tbhdu.data['TIME'] + rdate.mjd) * units.d
cut1c = tbhdu.data['UT1-UTC'] * units.s
ctaiutc = tbhdu.data['IAT-UTC'] * units.s
cwobx = tbhdu.data['WOBXY'][:,0] * units.arcsec
cwoby = tbhdu.data['WOBXY'][:,1] * units.arcsec

cb = casac.calibrater()
ms = casac.ms()
tb = casac.table()

tb.open(args[1] + '/ANTENNA')
position = tb.getcol('POSITION')
tb.close()

ms.open(args[1])
scans = ms.getscansummary()

scaninfo = {}
for scan in scans:
    scan_number = int(scan)
    scaninfo[scan_number] = {}
    scaninfo[scan_number]['begin'] = scans[scan]['0']['BeginTime']
    scaninfo[scan_number]['end'] = scans[scan]['0']['EndTime']
    scaninfo[scan_number]['field'] = scans[scan]['0']['FieldId']
    continue

(x, y, z) = position * units.m

cb.open(args[1], addcorr=False, addmodel=False)
cb.createcaltable(args[2], 'Real', 'Fringe Jones', True)
cb.close()

tb.open(args[2] + '/SPECTRAL_WINDOW')
chanfreq = tb.getcol('CHAN_FREQ')[0] * units.Hz
tb.close()

tb.open(args[2], nomodify=False)

#velite = constants.c
velite = 2.997925e8 * units.m / units.s
radsec = erfa.DS2R / units.s

tu = (rdate.jd - 2415020.0) / 36525.0

gmstm = (8640184.542 / 3600.0) * tu
gmstm = np.fmod(gmstm, 24.0)
gmstm = (6.0 + 38.0/60.0 + 45.836/3600.0) + gmstm + (0.0929/3600.0) * tu * tu
gstiat = np.pi * gmstm / 12.0
rate = 1.00273790265 + 0.589e-10 * tu
rotiat = 2 * np.pi * rate

if options.eopfile:
    dat = np.loadtxt(options.eopfile, skiprows=1)
    i = np.searchsorted(dat[:,0], rdate.jd, side='left')
    mjd = (dat[i - 1:i + 4,0] - erfa.DJM0) * units.d
    ut1c = dat[i - 1:i + 4,3] * 1e-6 * units.s
    taiutc = np.zeros(5) * units.s
    wobx = dat[i - 1:i + 4,1] * 1e-1 * units.arcsec
    woby = dat[i - 1:i + 4,2] * 1e-1 * units.arcsec
else:
    dat = iers.IERS_Auto.open()
    i = np.searchsorted(dat['MJD'].value, rdate.mjd, side='left')
    mjd = dat['MJD'][i - 1:i + 4]
    ut1c = dat['UT1_UTC_A'][i - 1:i + 4]
    taiutc = ctaiutc
    wobx = dat['PM_x_A'][i - 1:i + 4]
    woby = dat['PM_y_A'][i - 1:i + 4]
    pass

#ut1c = [ 0.028803, 0.028025, 0.027090, 0.025967, 0.024677 ] * units.s
#ut1c = [ 0.021803, 0.021025, 0.020090, 0.018967, 0.017677 ] * units.s
#wobx = [ 0.157790, 0.157350, 0.157110, 0.156500, 0.155380 ] * units.arcsec
#woby = [ 0.308430, 0.306940, 0.305980, 0.305510, 0.305350 ] * units.arcsec

#ut1c = [ 0.0, 0.0, 0.0, 0.0, 0.0 ] * units.s
#wobx = [ 0.0, 0.0, 0.0, 0.0, 0.0 ] * units.arcsec
#woby = [ 0.0, 0.0, 0.0, 0.0, 0.0 ] * units.arcsec

leaps0 = ctaiutc[1] - taiutc[1]

cwobx = interp1d(cmjd, cwobx, kind='cubic')
cwoby = interp1d(cmjd, cwoby, kind='cubic')
wobx = interp1d(mjd, wobx, kind='cubic')
woby = interp1d(mjd, woby, kind='cubic')

xs = np.array([
#             l   l'  F   D OMEGA     sin   cos
        [     1., 0., 2., 2., 2.,    -0.02, 0.00 ],
        [     2., 0., 2., 0., 1.,    -0.04, 0.00 ],
        [     2., 0., 2., 0., 2.,    -0.10, 0.00 ],
        [     0., 0., 2., 2., 1.,    -0.05, 0.00 ],
        [     0., 0., 2., 2., 2.,    -0.12, 0.00 ],
        [     1., 0., 2., 0., 0.,    -0.04, 0.00 ],
        [     1., 0., 2., 0., 1.,    -0.40, 0.01 ],
        [     1., 0., 2., 0., 2.,    -0.98, 0.03 ],
        [     3., 0., 0., 0., 0.,    -0.02, 0.00 ],
        [    -1., 0., 2., 2., 1.,    -0.08, 0.00 ],
        [    -1., 0., 2., 2., 2.,    -0.20, 0.00 ],
        [     1., 0., 0., 2., 0.,    -0.08, 0.00 ],
        [     2., 0., 2.,-2., 2.,     0.02, 0.00 ],
        [     0., 1., 2., 0., 2.,     0.03, 0.00 ],
        [     0., 0., 2., 0., 0.,    -0.30, 0.00 ],
        [     0., 0., 2., 0., 1.,    -3.20, 0.09 ],
        [     0., 0., 2., 0., 2.,    -7.73, 0.21 ],
        [     2., 0., 0., 0.,-1.,     0.02, 0.00 ],
        [     2., 0., 0., 0., 0.,    -0.34, 0.00 ],
        [     2., 0., 0., 0., 1.,     0.02, 0.00 ],
        [     0.,-1., 2., 0., 2.,    -0.02, 0.00 ],
        [     0., 0., 0., 2.,-1.,     0.05, 0.00 ],
        [     0., 0., 0., 2., 0.,    -0.72, 0.02 ],
        [     0., 0., 0., 2., 1.,    -0.05, 0.00 ],
        [     0.,-1., 0., 2., 0.,    -0.05, 0.00 ],
        [     1., 0., 2.,-2., 1.,     0.05, 0.00 ],
        [     1., 0., 2.,-2., 2.,     0.10, 0.00 ],
        [     1., 1., 0., 0., 0.,     0.04, 0.00 ],
        [    -1., 0., 2., 0., 0.,     0.05, 0.00 ],
        [    -1., 0., 2., 0., 1.,     0.18, 0.00 ],
        [    -1., 0., 2., 0., 2.,     0.44, 0.00 ],
        [     1., 0., 0., 0.,-1.,     0.53, 0.00 ],
        [     1., 0., 0., 0., 0.,    -8.33, 0.12 ],
        [     1., 0., 0., 0., 1.,     0.54, 0.00 ],
        [     0., 0., 0., 1., 0.,     0.05, 0.00 ],
        [     1.,-1., 0., 0., 0.,    -0.06, 0.00 ],
        [    -1., 0., 0., 2.,-1.,     0.12, 0.00 ],
        [    -1., 0., 0., 2., 0.,    -1.84, 0.02 ],
        [    -1., 0., 0., 2., 1.,     0.13, 0.00 ],
        [     1., 0.,-2., 2.,-1.,     0.02, 0.00 ],
        [    -1.,-1., 0., 2., 0.,    -0.09, 0.00 ],
        [     0., 2., 2.,-2., 2.,    -0.06, 0.00 ],
        [     0., 1., 2.,-2., 1.,     0.03, 0.00 ],
        [     0., 1., 2.,-2., 2.,    -1.88, 0.00 ],
        [     0., 0., 2.,-2., 0.,     0.25, 0.00 ],
        [     0., 0., 2.,-2., 1.,     1.17, 0.00 ],
        [     0., 0., 2.,-2., 2.,   -48.84, 0.11 ],
        [     0., 2., 0., 0., 0.,    -0.19, 0.00 ],
        [     2., 0., 0.,-2.,-1.,     0.05, 0.00 ],
        [     2., 0., 0.,-2., 0.,    -0.55, 0.00 ],
        [     2., 0., 0.,-2., 1.,     0.04, 0.00 ],
        [     0.,-1., 2.,-2., 1.,    -0.05, 0.00 ],
        [     0., 1., 0., 0.,-1.,     0.09, 0.00 ],
        [     0.,-1., 2.,-2., 2.,     0.83, 0.00 ],
        [     0., 1., 0., 0., 0.,   -15.55, 0.02 ],
        [     0., 1., 0., 0., 1.,    -0.14, 0.00 ],
        [     1., 0., 0.,-1., 0.,     0.03, 0.00 ],
        [     2., 0.,-2., 0., 0.,    -0.14, 0.00 ],
        [    -2., 0., 2., 0., 1.,     0.42, 0.00 ],
        [    -1., 1., 0., 1., 0.,     0.04, 0.00 ],
        [     0., 0., 0., 0., 2.,     7.90, 0.00 ],
        [     0., 0., 0., 0., 1., -1637.68,-0.10 ]])

def ut1szt(fa):
    dut = 0.0
    for i in xrange(len(xs)):
        arg = xs[i, 0] * fa[0] + xs[i, 1] * fa[1] + xs[i, 2] * fa[2] \
            + xs[i, 3] * fa[3] + xs[i, 4] * fa[4]
#        arg = np.fmod(arg, 2*np.pi)
        arg = np.fmod(arg, erfa.TURNAS) * erfa.DAS2R
        dut = xs[i, 5] * np.sin(arg) + xs[i, 6] * np.cos(arg) + dut
        continue
    return dut * 1e-4 * units.s

def nutfa(xjd):
    t = (xjd - erfa.DJ00) / erfa.DJC

    fa = np.zeros(5)
#    fa[0] = erfa.fal03(t)
#    fa[1] = erfa.falp03(t)
#    fa[2] = erfa.faf03(t)
#    fa[3] = erfa.fad03(t)
#    fa[4] = erfa.faom03(t)

    cent = t
    cent2 = cent * cent
    cent3 = cent * cent2
    cent4 = cent2 * cent2

    el = -0.00024470 * cent4 + 0.051635 * cent3 + 31.8792 * cent2 \
        + 1717915923.2178 * cent + 485868.249036
    elp = -0.00001149 * cent4 + -0.000136 * cent3 + -0.5532 * cent2 \
        + 129596581.0481 * cent + 1287104.79305
    f = 0.00000417 * cent4 + -0.001037 * cent3 + -12.7512 * cent2 \
        + 1739527262.8478 * cent + 335779.526232
    d = -0.00003169 * cent4 + 0.006593 * cent3 + -6.3706 * cent2 \
        + 1602961601.2090 * cent + 1072260.70369
    om = -0.00005939 * cent4 + 0.007702 * cent3 + 7.4722 * cent2 \
        + -6962890.2665 * cent + 450160.398036

    fa[0] = np.fmod(el, erfa.TURNAS)
    fa[1] = np.fmod(elp, erfa.TURNAS)
    fa[2] = np.fmod(f, erfa.TURNAS)
    fa[3] = np.fmod(d, erfa.TURNAS)
    fa[4] = np.fmod(om, erfa.TURNAS)
    return fa

def ut1cor(mjd, ut1ptx, taiutc, xjdtim):
    ut1pt = taiutc - ut1ptx

    ut1rs = np.zeros(len(mjd)) * units.s
    for i in xrange(len(mjd)):
        xjd = mjd[i].value + erfa.DJM0
        fa = nutfa(xjd)
        dut = ut1szt(fa)
        ut1rs[i] = ut1pt[i] + dut
        continue

    ut1rs = interp1d(mjd, ut1rs, kind='cubic')

    xjd = xjdtim
    fa = nutfa(xjd)
    dut = ut1szt(fa)
    shortp = -dut
    atmut1 = ut1rs(xjdtim - erfa.DJM0) * units.s + shortp
    return taiutc[1] - atmut1

for scan in scaninfo:
    start = scaninfo[scan]['begin']
    end = scaninfo[scan]['end']

    fieldid = scaninfo[scan]['field']
    fielddir = ms.getfielddirmeas('REFERENCE_DIR', fieldid)
    dra = fielddir['m0']['value']
    ddec = fielddir['m1']['value']
    sindec = np.sin(ddec)
    cosdec = np.cos(ddec)

    nsteps = np.ceil(1440 * (end - start))
    for t in np.linspace(start, end, nsteps):
        t = Time(t, format="mjd")
#        t = Time(rdate.mjd + 0.544351875782, format="mjd")

        dtcor = ut1cor(cmjd, cut1c, ctaiutc, t.jd)
        xpcor = cwobx(t.mjd) * erfa.DAS2R
        ypcor = cwoby(t.mjd) * erfa.DAS2R

        had = gstiat + (t - rdate + dtcor).value * rotiat
        chad = np.cos(had)
        shad = np.sin(had)

        xr = x * chad - y * shad + z * (-np.sin(xpcor) * chad - np.sin(ypcor) * shad)
        yr = x * shad + y * chad + z * (-np.sin(xpcor) * shad + np.sin(ypcor) * chad)
        zr = x * np.sin(xpcor) - y * np.sin(ypcor) + z

        delay = ((xr * np.cos(dra) + yr * np.sin(dra)) * cosdec + zr * sindec) \
            / velite
        rate = radsec / velite * \
            (((-x * shad - y * chad) * np.cos(dra)) + \
             ((+x * chad - y * shad) * np.sin(dra))) * cosdec

        dtcor = ut1cor(mjd, ut1c, taiutc, t.jd) + leaps0
        xpcor = wobx(t.mjd) * erfa.DAS2R
        ypcor = woby(t.mjd) * erfa.DAS2R

        had = gstiat + (t - rdate + dtcor).value * rotiat
        chad = np.cos(had)
        shad = np.sin(had)

        xr = x * chad - y * shad + z * (-np.sin(xpcor) * chad - np.sin(ypcor) * shad)
        yr = x * shad + y * chad + z * (-np.sin(xpcor) * shad + np.sin(ypcor) * chad)
        zr = x * np.sin(xpcor) - y * np.sin(ypcor) + z

        delayc = ((xr * np.cos(dra) + yr * np.sin(dra)) * cosdec + zr * sindec) \
            / velite
        ratec = radsec / velite * \
            (((-x * shad - y * chad) * np.cos(dra)) + \
             ((+x * chad - y * shad) * np.sin(dra))) * cosdec

        delay = delayc - delay
        rate = ratec - rate
#        print delay
#        print rate
#        raise Hell

        zeros = np.zeros(6)
        row = tb.nrows()
        tb.addrows(len(delay) * len(chanfreq))
        for antenna in xrange(len(delay)):
            for spw in xrange(len(chanfreq)):
                phase = 2 * np.pi * np.modf(chanfreq[spw] * delay)[0]
                tb.putcell('TIME', row, t.mjd * 86400)
                tb.putcell('FIELD_ID', row, fieldid)
                tb.putcell('SPECTRAL_WINDOW_ID', row, spw)
                tb.putcell('ANTENNA1', row, antenna)
                tb.putcell('ANTENNA2', row, -1)
                fparam = np.zeros(6)
                fparam[0] = fparam[3] = phase[antenna].value
                fparam[1] = fparam[4] = delay[antenna].value * 1e9
                fparam[2] = fparam[5] = rate[antenna].value
                tb.putcell('FPARAM', row, fparam.reshape(6, 1))
                tb.putcell('PARAMERR', row, zeros.reshape(6, 1))
                tb.putcell('FLAG', row, zeros.reshape(6, 1))
                row += 1
                continue
            continue
        continue
    continue

tb.close()
ms.done()

#mjdspace = np.linspace(mjd[0], mjd[-1], num=41, endpoint=True)
#a = [ut1cor(mjd, ut1c, taiutc, x.value + erfa.DJM0).value for x in mjd]
#b = [ut1cor(mjd, ut1c, taiutc, x.value + erfa.DJM0).value for x in mjdspace]
#plt.plot(mjd, a, 'o', mjdspace, b)
#plt.show()
#plt.plot(mjd, wobx(mjd), 'o', mjdspace, wobx(mjdspace))
#plt.show()
#plt.plot(mjd, woby(mjd), 'o', mjdspace, woby(mjdspace))
#plt.show()
