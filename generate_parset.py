#!/usr/bin/env python
"""
Automatically generate a VLBI pipeline parset (vlbi_pipe_params.json).

The observation is characterised directly from the FITS-IDI files (and/or the
vex schedule) so that the fields a user normally has to fill in by hand -
project code, antennas, reference antenna order, fringe finders, phase
calibrators and targets - are derived from the data themselves.

Typical usage::

	python generate_parset.py -i ~/ek053a/uv -o vlbi_pipe_params.json
	python generate_parset.py -i ~/ek053a/uv -v ~/ek053a/ek053a.vex --cwd /scratch/EK053A
	python generate_parset.py -v ek053a.vex --dry-run

Everything that cannot be inferred from the data (HPC settings, CASA paths,
calibration solution intervals...) is inherited from a template parset, by
default the vlbi_pipe_params.json shipped with the pipeline, so the output is
always a complete, runnable parset.
"""

from __future__ import print_function

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

import numpy as np

try:
	from astropy.io import fits
except ImportError:
	import pyfits as fits

sys.path.append(os.path.dirname(os.path.realpath(__file__)))

## Reference antenna preference, roughly in order of decreasing sensitivity.
## Antennas which are not in this list are appended in the order they appear
## in the data, so an unknown array still produces a usable refant list.
STATION_PREFERENCE = [
	## Large single dishes / most sensitive EVN + global elements
	"EF", "GB", "AR", "SR", "O8", "WB", "T6", "YS", "MC", "NT", "SH", "KM",
	"IR", "TR", "SV", "BD", "ZC", "UR", "HH", "WZ", "YJ", "ON", "MH", "NY",
	"EB", "JV", "RO", "MA", "TI", "KU",
	## e-MERLIN out-stations
	"JB", "DA", "PI", "KN", "JM", "DE", "CM",
	## VLBA
	"LA", "PT", "KP", "FD", "NL", "OV", "BR", "MK", "HN", "SC",
	## VLA / LBA / other
	"Y", "Y1", "Y27", "VLA", "AT", "MP", "PA", "HO", "CD", "KE", "YG", "WA",
]

## Sources whose names look like these are entries in a standard calibrator
## catalogue (JHHMM+DDMM, BHHMM+DD, HHMM+DDD, 3C/4C/OQ/DA/NRAO...).
CALIBRATOR_NAME_RE = re.compile(
	r"^("
	r"[JB]\d{4}[\+\-]\d{2,4}[A-Za-z]?"        # J1031+7441, B0329+54
	r"|\d{4}[\+\-]\d{2,3}"                    # 0528+134
	r"|(3C|4C|OQ|OJ|DA|PKS|NRAO|ICRF)[\s_\-]?\d+.*"
	r")$", re.IGNORECASE)

SPEED_OF_LIGHT = 299792458.0

## Solution intervals --estimate-snr is allowed to pick from, in seconds
SOLINT_CHOICES = [10., 15., 30., 60., 120., 300.]

## How far above the pipeline's minimum SNR a solution interval has to sit
## before it is trusted - solutions right on the threshold fail half the time
SNR_MARGIN = 1.5

## Amplitude self-calibration needs roughly twice the SNR of a phase-only solve
AMPLITUDE_SNR_FACTOR = 2.0

## Rule of thumb for the tropospheric coherence time in good conditions:
## the phase error grows about linearly with frequency, giving ~10 min at
## 1.6 GHz, ~2 min at 8.4 GHz and ~45 s at 22 GHz. Solving for phase over
## longer than this gains nothing, however much SNR the source has.
COHERENCE_TIME_GHZ_S = 1000.

## Round numbers the coherence time is reported and applied at
COHERENCE_LADDER = [10., 15., 20., 30., 45., 60., 90., 120., 180., 300.,
					600., 900.]

## Solution types that carry phase, and are therefore limited by coherence.
## 'ap' is included because gaincal solves it as a vector average, so losing
## coherence biases the amplitude low as well as scrambling the phase.
PHASE_CAL_TYPES = ('f', 'p', 'ap', 'k')

## Below this the ionosphere is worth correcting for with a TEC model
IONOSPHERE_MAX_FREQ = 8.0e9

## Below this it is worth fitting a dispersive term in the fringe fit
DISPERSIVE_MAX_FREQ = 5.0e9


###################################################################################################
# Small helpers
###################################################################################################

def is_calibrator_name(source):
	"""True if a source name follows a standard calibrator catalogue convention."""
	return CALIBRATOR_NAME_RE.match(source.strip()) is not None


def angsep(ra1, dec1, ra2, dec2):
	"""Angular separation (deg) between two positions given in degrees."""
	ra1, dec1, ra2, dec2 = np.radians([ra1, dec1, ra2, dec2])
	cossep = (np.sin(dec1) * np.sin(dec2)
			  + np.cos(dec1) * np.cos(dec2) * np.cos(ra1 - ra2))
	return float(np.degrees(np.arccos(np.clip(cossep, -1.0, 1.0))))


def deg_to_casa_coords(ra_deg, dec_deg):
	"""Convert RA/Dec in degrees into CASA sexagesimal strings."""
	ra_deg = float(ra_deg) % 360.
	ra_hours = ra_deg / 15.
	hh = int(ra_hours)
	mm = int((ra_hours - hh) * 60.)
	ss = (ra_hours - hh - mm / 60.) * 3600.

	sign = '-' if dec_deg < 0 else '+'
	dec_deg = abs(float(dec_deg))
	dd = int(dec_deg)
	dm = int((dec_deg - dd) * 60.)
	ds = (dec_deg - dd - dm / 60.) * 3600.

	return ('%02dh%02dm%09.6fs' % (hh, mm, ss),
			'%s%02dd%02dm%08.5fs' % (sign, dd, dm, ds))


def sexagesimal_to_deg(ra_str, dec_str):
	"""Convert vex style '10h00m25.0s' / '+02d33\\'00.0"' strings to degrees."""
	ra_parts = [float(x) for x in re.findall(r"[-+]?\d+\.?\d*", ra_str)]
	dec_parts = [float(x) for x in re.findall(r"[-+]?\d+\.?\d*", dec_str)]
	ra = (ra_parts[0] + ra_parts[1] / 60. + ra_parts[2] / 3600.) * 15.
	sign = -1. if dec_str.strip().startswith('-') else 1.
	dec = sign * (abs(dec_parts[0]) + dec_parts[1] / 60. + dec_parts[2] / 3600.)
	return ra, dec


def natural_sort(unsorted):
	"""Sort strings so that idi2 comes before idi10."""
	convert = lambda text: int(text) if text.isdigit() else text.lower()
	alphanum = lambda key: [convert(c) for c in re.split(r'([0-9]+)', key)]
	return sorted(unsorted, key=alphanum)


def format_time(seconds):
	"""Human readable duration."""
	if seconds >= 3600:
		return '%.1f h' % (seconds / 3600.)
	if seconds >= 60:
		return '%.1f min' % (seconds / 60.)
	return '%.0f s' % seconds


###################################################################################################
# Locating the input files
###################################################################################################

def find_fitsidi_files(path):
	"""Return a naturally sorted list of FITS-IDI files given a file or directory."""
	if path is None:
		return []
	if os.path.isfile(path):
		return [os.path.abspath(path)]
	if not os.path.isdir(path):
		print('WARNING: %s does not exist - ignoring' % path)
		return []

	idifiles = []
	for i in os.listdir(path):
		if re.search(r'\.IDI\d*$', i, re.IGNORECASE) or i.lower().endswith('idifits') \
		   or re.search(r'IDI\d+$', i):
			idifiles.append(os.path.abspath(os.path.join(path, i)))
	return natural_sort(idifiles)


def find_vex_file(search_dirs, project_code=None):
	"""Look for a vex/vix schedule in the given directories."""
	for directory in search_dirs:
		if directory is None or not os.path.isdir(directory):
			continue
		candidates = []
		for i in os.listdir(directory):
			if i.lower().endswith('.vex') or i.lower().endswith('.vix'):
				candidates.append(os.path.abspath(os.path.join(directory, i)))
		if candidates:
			if project_code is not None:
				for c in candidates:
					if os.path.basename(c).lower().startswith(project_code.lower()):
						return c
			return natural_sort(candidates)[0]
	return None


def find_aux_file(search_dirs, project_code, extensions):
	"""Find auxiliary files (antab, uvflg...) belonging to a project code."""
	for directory in search_dirs:
		if directory is None or not os.path.isdir(directory):
			continue
		for i in natural_sort(os.listdir(directory)):
			name = i.lower()
			if not name.startswith(project_code.lower()):
				continue
			for ext in extensions:
				if name.endswith(ext):
					return os.path.abspath(os.path.join(directory, i))
	return None


###################################################################################################
# Reading the observation
###################################################################################################

def read_fitsidi(idifiles, scan_gap=30.0):
	"""
	Characterise an observation from its FITS-IDI files.

	Returns a dictionary with the project code, array, correlator, frequency
	setup, antennas, source positions and the reconstructed scan list
	(source, start MJD, duration in seconds).
	"""
	info = {'antennas': [], 'sources': OrderedDict(), 'scans': [],
			'calcodes': {}, 'files': idifiles, 'row_index': []}

	times = []
	source_ids = []
	id_to_source = {}
	antenna_numbers = OrderedDict()

	for n, idifile in enumerate(idifiles):
		print('   reading %s' % os.path.basename(idifile))
		hdu = fits.open(idifile, memmap=True)

		try:
			array_hdr = hdu['ARRAY_GEOMETRY'].header
		except KeyError:
			array_hdr = hdu[1].header

		if n == 0:
			info['project_code'] = str(array_hdr.get('OBSCODE', '')).strip()
			info['telescope'] = str(array_hdr.get('ARRNAM', '')).strip()
			info['correlator'] = str(hdu[0].header.get('CORRELAT', '')).strip()
			info['obs_date'] = str(array_hdr.get('RDATE', '')).strip()
			info['nspw'] = int(array_hdr.get('NO_BAND', 1))
			info['nchan'] = int(array_hdr.get('NO_CHAN', 1))
			info['npol'] = int(array_hdr.get('NO_STKD', 1))
			info['ref_freq'] = float(array_hdr.get('REF_FREQ', 0.0))
			info['chan_bw'] = float(array_hdr.get('CHAN_BW', 0.0))
			try:
				freq_tab = hdu['FREQUENCY'].data
				info['bandwidth'] = float(np.sum(np.atleast_1d(
					freq_tab['TOTAL_BANDWIDTH'][0])))
				info['band_freqs'] = (np.atleast_1d(freq_tab['BANDFREQ'][0])
									  + info['ref_freq']).tolist()
			except KeyError:
				info['bandwidth'] = info['chan_bw'] * info['nchan'] * info['nspw']
				info['band_freqs'] = [info['ref_freq']]

			for row in hdu['ARRAY_GEOMETRY'].data:
				ant = str(row['ANNAME']).strip().upper()
				antenna_numbers[int(row['NOSTA'])] = ant
				if ant not in info['antennas']:
					info['antennas'].append(ant)

		for row in hdu['SOURCE'].data:
			name = str(row['SOURCE']).strip()
			id_to_source[int(row['SOURCE_ID'])] = name
			if name not in info['sources']:
				info['sources'][name] = {'ra': float(row['RAEPO']) % 360.,
										 'dec': float(row['DECEPO'])}
				info['calcodes'][name] = str(row['CALCODE']).strip()

		uv = hdu['UV_DATA'].data
		## DATE holds the integer Julian day, TIME the fraction of a day
		file_times = (np.asarray(uv['DATE'], dtype=np.float64)
					  + np.asarray(uv['TIME'], dtype=np.float64))
		file_sids = np.asarray(uv['SOURCE_ID'], dtype=np.int32)
		times.append(file_times)
		source_ids.append(file_sids)
		## Keep the (small) time/source/baseline columns so that --estimate-snr
		## can go straight to the rows of a given scan without a second pass
		info['row_index'].append({'file': idifile, 'times': file_times,
								  'source_ids': file_sids,
								  'baselines': np.asarray(uv['BASELINE'])})
		try:
			info['int_time'] = float(np.median(np.asarray(uv['INTTIM'])))
		except KeyError:
			info['int_time'] = 2.0
		hdu.close()

	if times:
		times = np.concatenate(times)
		source_ids = np.concatenate(source_ids)
		info['scans'] = build_scans(times, source_ids, id_to_source,
									gap=max(scan_gap, 3 * info.get('int_time', 2.0)))
		info['start_mjd'] = float(np.min(times)) - 2400000.5
		info['end_mjd'] = float(np.max(times)) - 2400000.5

	info['antenna_numbers'] = antenna_numbers
	info['source_ids'] = dict([(v, k) for k, v in id_to_source.items()])

	## Only keep sources that actually have visibilities attached
	observed = set([s['source'] for s in info['scans']])
	if observed:
		info['sources'] = OrderedDict(
			[(k, v) for k, v in info['sources'].items() if k in observed])

	return info


def build_scans(times_jd, source_ids, id_to_source, gap=30.0):
	"""Reconstruct a scan list from visibility timestamps and source ids."""
	order = np.argsort(times_jd, kind='mergesort')
	times_jd = times_jd[order]
	source_ids = source_ids[order]

	if len(times_jd) == 0:
		return []

	new_scan = np.where((np.diff(times_jd) * 86400. > gap)
						| (np.diff(source_ids) != 0))[0]
	starts = np.concatenate(([0], new_scan + 1))
	ends = np.concatenate((new_scan, [len(times_jd) - 1]))

	scans = []
	for a, b in zip(starts, ends):
		scans.append({'source': id_to_source.get(int(source_ids[a]),
												 str(source_ids[a])),
					  'start_mjd': float(times_jd[a]) - 2400000.5,
					  'duration': float((times_jd[b] - times_jd[a]) * 86400.)})
	return scans


###################################################################################################
# Estimating how strong the calibrators are
###################################################################################################

def fringe_search_snr(vis):
	"""
	Peak SNR of a coarse delay/rate search on one baseline.

	'vis' is a (time, band, channel) complex array of raw visibilities. The
	residual delay and rate of uncalibrated data decohere any straight
	average, so each band is FFT'd over channel and time and the peak of the
	delay/rate plane is compared with the noise away from it. The result is
	the SNR a fringe fit would reach on that baseline, per band, over the
	length of data supplied - no flux scale or Tsys needed, because the
	correlator amplitudes are already normalised correlation coefficients.
	"""
	ntime, nband, nchan = vis.shape
	if ntime < 2 or nchan < 4:
		return 0.0, 0.0

	snrs, peaks = [], []
	for b in range(nband):
		plane = vis[:, b, :]
		if not np.any(plane):
			continue
		amp = np.abs(np.fft.fft2(plane, s=(2 * ntime, 2 * nchan))) \
			/ (ntime * nchan)
		## |FFT| of pure noise is Rayleigh distributed, whose median is
		## sigma*sqrt(2 ln 2), so this converts the robust median into a sigma
		sigma = np.median(amp) / 1.177
		if sigma > 0:
			snrs.append(amp.max() / sigma)
			peaks.append(amp.max())

	if not snrs:
		return 0.0, 0.0
	return float(np.median(snrs)), float(np.median(peaks))


def measure_calibrator_snr(info, sources, edge_frac=0.1, verbose=True):
	"""
	Measure the fringe SNR of each calibrator from one scan of raw data.

	Returns, per source, the median per-baseline SNR, the SNR of the weakest
	antenna (the one that limits the solution) and the length and bandwidth
	the measurement refers to, so that it can be scaled to any solution
	interval.
	"""
	nband = info.get('nspw', 1)
	nchan = info.get('nchan', 1)
	npol = info.get('npol', 1)
	spw_bw = info.get('bandwidth', 0.) / max(nband, 1)
	antennas = info.get('antenna_numbers', {})

	## Longest scan of each source, so the measurement has the most to work on
	best_scan = {}
	for scan in info['scans']:
		if scan['source'] not in sources:
			continue
		if scan['duration'] > best_scan.get(scan['source'],
											{'duration': -1})['duration']:
			best_scan[scan['source']] = scan

	results = OrderedDict()
	for source in sources:
		scan = best_scan.get(source)
		source_id = info.get('source_ids', {}).get(source)
		if scan is None or source_id is None:
			continue

		start = scan['start_mjd'] + 2400000.5
		end = start + scan['duration'] / 86400.

		snr_baseline = {}
		for entry in info['row_index']:
			rows = ((entry['source_ids'] == source_id)
					& (entry['times'] >= start) & (entry['times'] <= end))
			if not rows.any():
				continue

			hdu = fits.open(entry['file'], memmap=True)
			flux = hdu['UV_DATA'].data['FLUX'][rows]
			hdu.close()

			## FLUX is (band, channel, stokes, [real, imag, weight]), which
			## astropy hands back either flat or already shaped by TDIM
			nvis = nband * nchan * max(npol, 1)
			ncomplex = int(flux.size / (flux.shape[0] * nvis))
			if ncomplex < 2:
				continue
			flux = flux.reshape(-1, nband, nchan, npol, ncomplex)
			vis = flux[..., 0] + 1j * flux[..., 1]
			if ncomplex > 2:
				vis[flux[..., 2] <= 0] = 0.
			## Parallel hands only, averaged into an approximate Stokes I
			vis = vis[:, :, :, 0:min(2, npol)].mean(axis=-1)

			edge = int(round(edge_frac * nchan))
			if nchan - 2 * edge >= 4:
				vis = vis[:, :, edge:nchan - edge]

			baselines = entry['baselines'][rows]
			for code in np.unique(baselines):
				a1, a2 = int(code) // 256, int(code) % 256
				if a1 == a2:
					continue
				snr, _ = fringe_search_snr(vis[baselines == code])
				name = (antennas.get(a1, str(a1)), antennas.get(a2, str(a2)))
				snr_baseline[name] = max(snr_baseline.get(name, 0.), snr)

		if not snr_baseline:
			continue

		## A fringe fit solves per antenna, combining every baseline to it
		snr_antenna = {}
		for (a1, a2), snr in snr_baseline.items():
			for ant in (a1, a2):
				snr_antenna[ant] = snr_antenna.get(ant, 0.) + snr ** 2
		snr_antenna = dict([(a, np.sqrt(v)) for a, v in snr_antenna.items()])

		weakest = min(snr_antenna, key=lambda a: snr_antenna[a])
		results[source] = {
			'snr_baseline': float(np.median(list(snr_baseline.values()))),
			'snr_antenna': float(snr_antenna[weakest]),
			'weakest_antenna': weakest,
			'nantenna': len(snr_antenna),
			'tau': scan['duration'],
			'spw_bw': spw_bw}

	if verbose and results:
		print('')
		print('Fringe SNR measured on one scan of each calibrator '
			  '(per %.1f MHz spw):' % (spw_bw / 1e6))
		print('%-20s %10s %12s %14s %10s'
			  % ('CALIBRATOR', 'SCAN', 'SNR/BASELINE', 'SNR/ANTENNA',
				 'WEAKEST'))
		print('-' * 72)
		for source, r in results.items():
			print('%-20s %10s %12.1f %14.1f %10s'
				  % (source, format_time(r['tau']), r['snr_baseline'],
					 r['snr_antenna'], r['weakest_antenna']))

	return results


def scaled_snr(measurement, tau, nspw=1, combine_spw=False):
	"""SNR the measurement implies for a different solution interval."""
	gain = np.sqrt(nspw) if combine_spw else 1.
	return float(measurement['snr_antenna']
				 * np.sqrt(tau / measurement['tau']) * gain)


def parse_solint(value, scan_length):
	"""Length of a CASA solution interval in seconds ('inf' is a whole scan)."""
	if isinstance(value, (int, float)):
		return float(value)
	value = str(value).strip().lower()
	if value in ('', 'inf', 'int'):
		return scan_length
	match = re.match(r'^([\d\.]+)\s*(s|sec|min|m|h)?$', value)
	if match is None:
		return None
	scale = {'min': 60., 'm': 60., 'h': 3600.}.get(match.group(2), 1.)
	return float(match.group(1)) * scale


def coherence_time(freq_hz):
	"""
	Rule-of-thumb tropospheric coherence time (s) at an observing frequency.

	Snapped to a ladder of round numbers, since carrying '119 s' around would
	imply far more precision than a rule of thumb deserves.
	"""
	if not freq_hz:
		return None
	estimate = np.clip(COHERENCE_TIME_GHZ_S / (freq_hz / 1e9), 10., 900.)
	return float(min(COHERENCE_LADDER, key=lambda t: abs(t - estimate)))


def fix_solints(sequence, scan_length, measurement, int_time, threshold, nspw,
				cal_types=None, max_tau=None):
	"""
	Bring a sequence of solution intervals within reach of the data.

	Two constraints pull in opposite directions. SNR wants long intervals, so
	anything that cannot reach the threshold is stretched to the shortest
	interval that can. Coherence wants short ones, so any phase-bearing solve
	longer than the coherence time is pulled back to it - solving for phase
	beyond that gains no SNR, it only averages the atmosphere away. When the
	two cannot be satisfied at once the spws are combined instead, which buys
	SNR with bandwidth rather than time.

	The template sequence carries the intent of the calibration, so intervals
	that already work are left exactly as they are. Without a measurement only
	the coherence cap is applied, since that depends on frequency alone.
	Returns the new sequence, whether the spws have to be combined, and a list
	of what changed.
	"""
	combine, replacement = False, None
	if measurement is not None:
		shortest, combine = recommend_solint(measurement, int_time, threshold,
											 nspw, scan_length, max_tau=max_tau)
		replacement = format_solint(shortest, scan_length)

	fixed, changes = [], []
	for j, interval in enumerate(sequence):
		cal_type = cal_types[j] if cal_types else 'f'
		tau = parse_solint(interval, scan_length)
		if tau is None:
			fixed.append(interval)
			continue

		## Coherence only limits solves that carry phase
		capped = interval
		if max_tau is not None and cal_type in PHASE_CAL_TYPES and tau > max_tau:
			tau = max_tau
			capped = format_solint(max_tau, scan_length)
			if capped != interval:
				changes.append('%s -> %s (coherence)' % (interval, capped))

		if measurement is None \
		   or scaled_snr(measurement, tau, nspw, combine) >= threshold:
			fixed.append(capped)
		else:
			fixed.append(replacement)
			if replacement != capped:
				changes.append('%s -> %s (SNR)' % (capped, replacement))
	return fixed, combine, changes


def recommend_solint(measurement, int_time, threshold, nspw, scan_length,
					 max_tau=None):
	"""
	Shortest sensible solution interval that still clears the SNR threshold.

	SNR grows as the square root of the solution interval, and by another
	sqrt(nspw) if the spectral windows are combined, so the measured value is
	simply scaled. 'max_tau' caps how far the interval may be stretched, as
	nothing is gained by averaging past the coherence time. Returns
	(seconds, combine_spw), or (None, True) when even the longest usable
	interval with every spw combined falls short.
	"""
	floor = max(3 * int_time, 10.)
	options = [t for t in SOLINT_CHOICES if floor <= t < scan_length] \
		+ [scan_length]
	if max_tau is not None:
		options = [t for t in options if t <= max_tau] or [min(floor, max_tau)]

	for combine in (False, True):
		for tau in options:
			if scaled_snr(measurement, tau, nspw, combine) >= threshold:
				return tau, combine
	return None, True


def format_solint(seconds, scan_length):
	"""CASA solution interval string for a length in seconds."""
	if seconds is None or seconds >= scan_length:
		return 'inf'
	if seconds >= 60 and seconds % 60 == 0:
		return '%dmin' % int(seconds / 60)
	return '%ds' % int(round(seconds))


def read_vex(vexfile):
	"""Characterise an observation from its vex schedule."""
	from vex import Vex

	info = {'antennas': [], 'sources': OrderedDict(), 'scans': [],
			'calcodes': {}, 'vex_file': os.path.abspath(vexfile)}

	vex = Vex(vexfile)

	for name, pos in vex.source.items():
		try:
			ra, dec = sexagesimal_to_deg(pos['ra'], pos['dec'])
		except (IndexError, ValueError):
			continue
		info['sources'][name] = {'ra': ra, 'dec': dec}
		info['calcodes'][name] = ''

	for scan in vex.sched:
		stations = list(scan['scan'].values())
		## a station only records between its own start and stop offsets, so
		## the scan itself lasts as long as the station that stops last
		duration = max([s['scan_sec'] for s in stations]) if stations else 0.0
		info['scans'].append({'source': scan['source'],
							  'start_mjd': scan['mjd_floor'] + scan['start_hr'] / 24.,
							  'duration': float(duration)})
		for station in stations:
			ant = station['site_id'].strip().upper()
			if ant not in info['antennas']:
				info['antennas'].append(ant)

	info['scans'].sort(key=lambda s: s['start_mjd'])
	if info['scans']:
		info['start_mjd'] = info['scans'][0]['start_mjd']
		info['end_mjd'] = max([s['start_mjd'] + s['duration'] / 86400.
							   for s in info['scans']])

	## Everything else worth having lives in the header blocks and comments
	with open(vexfile) as f:
		raw = f.read()

	match = re.search(r'exper_name\s*=\s*([^;]+);', raw)
	if match:
		info['project_code'] = match.group(1).strip()
	match = re.search(r'target_correlator\s*=\s*([^;]+);', raw)
	if match:
		info['correlator'] = match.group(1).strip()
	match = re.search(r'exper_description\s*=\s*"?([^";]+)"?;', raw)
	if match:
		info['description'] = match.group(1).strip()

	## EVN/SCHED cover comments frequently name the fringe finders explicitly
	hints = []
	for match in re.finditer(r'\*.*fringe\s+finders?\s*[:\-]?\s*(.+)', raw,
							 re.IGNORECASE):
		for candidate in re.split(r'[,\s]+and[,\s]+|[,/]', match.group(1)):
			candidate = candidate.strip().strip('.')
			if candidate:
				hints.append(candidate)
	info['fringe_finder_hints'] = hints

	## Frequency setup of the first $FREQ def, i.e. the one the bulk of the
	## array observes with
	if vex.nsubband > 0:
		info['nspw'] = vex.nsubband
		info['bandwidth'] = vex.total_bw_hz
		info['ref_freq'] = vex.freq
		info['chan_bw'] = vex.bw_hz
	match = re.search(r'\*\s*number_channels\s*:\s*(\d+)', raw)
	if match:
		info['nchan'] = int(match.group(1))
	match = re.search(r'\*\s*integr_time\s*:\s*([\d\.]+)', raw)
	if match:
		info['int_time'] = float(match.group(1))

	return info


def merge_info(idi_info, vex_info):
	"""Merge the FITS-IDI and vex descriptions, preferring the FITS-IDI data."""
	if idi_info is None:
		return vex_info
	if vex_info is None:
		return idi_info

	merged = dict(vex_info)
	merged.update(dict([(k, v) for k, v in idi_info.items()
						if v not in (None, '', [], {})]))

	## Source positions from the vex file fill in anything the IDI lacks, but
	## the classification must only ever use sources with actual visibilities
	sources = OrderedDict()
	for name, pos in idi_info['sources'].items():
		sources[name] = pos
	merged['sources'] = sources
	merged['vex_file'] = vex_info.get('vex_file')
	merged['vex_sources'] = vex_info['sources']
	merged['fringe_finder_hints'] = vex_info.get('fringe_finder_hints', [])
	merged['antennas'] = idi_info['antennas'] or vex_info['antennas']
	return merged


###################################################################################################
# Working out what each source is
###################################################################################################

def source_statistics(scans):
	"""Per source scan counts, total time on source and median scan length."""
	stats = OrderedDict()
	for scan in scans:
		entry = stats.setdefault(scan['source'],
								 {'nscans': 0, 'total_time': 0.0, 'durations': []})
		entry['nscans'] += 1
		entry['total_time'] += scan['duration']
		entry['durations'].append(scan['duration'])
	for name, entry in stats.items():
		entry['median_duration'] = float(np.median(entry['durations']))
	return stats


def count_transitions(scans):
	"""Count how often the schedule alternates between each pair of sources."""
	transitions = {}
	for first, second in zip(scans[:-1], scans[1:]):
		if first['source'] == second['source']:
			continue
		key = tuple(sorted([first['source'], second['source']]))
		transitions[key] = transitions.get(key, 0) + 1
	return transitions


def target_separations(sources, targets, positions):
	"""Angular distance (deg) from each source to the nearest target."""
	targets = [t for t in targets if t in positions]
	if not targets:
		return {}

	separations = {}
	for name in sources:
		if name not in positions:
			continue
		separations[name] = min(
			[angsep(positions[name]['ra'], positions[name]['dec'],
					positions[t]['ra'], positions[t]['dec']) for t in targets])
	return separations


def regroup_roles(roles, positions, keep_order=False):
	"""
	Rebuild the phase-referencing groups after a manual override.

	Each calibrator is attached to the target it sits closest to, which is
	all that can be assumed once the schedule-derived grouping has been
	overruled.
	"""
	targets = roles['targets']
	calibrators = roles['phase_calibrators']
	roles['groups'] = []
	if not targets or not calibrators:
		return roles

	separations = dict(roles.get('separations') or {})
	grouped = OrderedDict([(t, []) for t in targets])
	known = [t for t in targets if t in positions]

	for cal in calibrators:
		nearest = targets[0]
		if cal in positions and known:
			seps = dict([(t, angsep(positions[cal]['ra'], positions[cal]['dec'],
									positions[t]['ra'], positions[t]['dec']))
						 for t in known])
			nearest = min(seps, key=lambda t: seps[t])
			separations[cal] = seps[nearest]
		grouped[nearest].append(cal)

	for target, cals in grouped.items():
		if not cals:
			continue
		if not keep_order:
			cals = sorted(cals, key=lambda n: (-separations.get(n, 0.), n))
		roles['groups'].append({'targets': [target], 'calibrators': cals})

	roles['separations'] = separations
	roles['phase_calibrators'] = [c for g in roles['groups']
								  for c in g['calibrators']]
	return roles


def classify_sources(info, max_sep=10.0, min_transitions=3, verbose=True):
	"""
	Split the observed sources into fringe finders, phase calibrators and targets.

	The classification uses the structure of the schedule rather than any
	external catalogue:

	  * sources that repeatedly alternate with each other and sit close
	    together on the sky form a phase-referencing group;
	  * within a group the source with the most time on source (preferring
	    names that do not look like calibrator catalogue entries) is the
	    target, the rest are phase calibrators (including check sources);
	  * sources that never join a group and are only visited a handful of
	    times are fringe finders;
	  * anything named in a "Fringe finders: ..." vex comment is forced to be
	    a fringe finder.
	"""
	scans = info['scans']
	stats = source_statistics(scans)
	positions = info['sources']
	names = list(stats.keys())

	if not names:
		return {'fringe_finders': [], 'phase_calibrators': [], 'targets': [],
				'stats': stats}

	## --- group sources that alternate with each other and are close by ------
	transitions = count_transitions(scans)
	parent = dict([(n, n) for n in names])

	def find(node):
		while parent[node] != node:
			parent[node] = parent[parent[node]]
			node = parent[node]
		return node

	def union(a, b):
		ra, rb = find(a), find(b)
		if ra != rb:
			parent[rb] = ra

	for (a, b), count in transitions.items():
		if count < min_transitions:
			continue
		if a in positions and b in positions:
			separation = angsep(positions[a]['ra'], positions[a]['dec'],
								positions[b]['ra'], positions[b]['dec'])
		else:
			separation = 0.0
		if separation <= max_sep:
			union(a, b)

	groups = OrderedDict()
	for name in names:
		groups.setdefault(find(name), []).append(name)

	## --- assign roles -------------------------------------------------------
	hints = [h.upper() for h in info.get('fringe_finder_hints', [])]
	total_times = dict([(n, stats[n]['total_time']) for n in names])
	longest = max(total_times.values())

	fringe_finders, targets = [], []
	## Each phase-referencing group is one science field with its own
	## calibrator(s): [{'targets': [...], 'calibrators': [...]}, ...]
	phase_ref_groups = []

	for members in groups.values():
		members = sorted(members, key=lambda n: total_times[n], reverse=True)

		if len(members) == 1:
			name = members[0]
			isolated_cal = (stats[name]['nscans'] <= 4
							or total_times[name] < 0.15 * longest)
			if name.upper() in hints or (isolated_cal and is_calibrator_name(name)) \
			   or (isolated_cal and info['calcodes'].get(name, '')):
				fringe_finders.append(name)
			elif isolated_cal and stats[name]['nscans'] <= 2:
				## a single, short visit with a non-catalogue name is still far
				## more likely to be a fringe finder than a science target
				fringe_finders.append(name)
			else:
				targets.append(name)
			continue

		## Phase-referencing group: pick the target(s)
		non_catalogue = [n for n in members if not is_calibrator_name(n)]
		if non_catalogue:
			group_targets = non_catalogue
		else:
			group_targets = [members[0]]

		group = {'targets': [], 'calibrators': []}
		for name in members:
			if name.upper() in hints:
				fringe_finders.append(name)
			elif name in group_targets:
				group['targets'].append(name)
			else:
				group['calibrators'].append(name)

		targets += group['targets']
		if group['targets'] and group['calibrators']:
			phase_ref_groups.append(group)

	## Sort by time on source so the most useful entry comes first, breaking
	## ties on the name so that the same data always gives the same parset
	rank = lambda n: (-total_times[n], n)
	fringe_finders = sorted(set(fringe_finders), key=rank)
	targets = sorted(set(targets), key=rank)

	## Separations are measured against the science field a calibrator serves,
	## and against the nearest target for everything else
	separations = target_separations(names, targets, positions)
	for group in phase_ref_groups:
		separations.update(target_separations(group['calibrators'],
											  group['targets'], positions))

	## Within a group the calibrators form a chain that works inwards towards
	## the science field, so the one furthest from the target is solved first
	## and the closest one last. Fall back on time on source when no positions
	## are available.
	for group in phase_ref_groups:
		group['targets'] = sorted(group['targets'], key=rank)
		if separations:
			group['calibrators'] = sorted(
				group['calibrators'],
				key=lambda n: (-separations.get(n, 0.), n))
		else:
			group['calibrators'] = sorted(group['calibrators'], key=rank)

	## Keep the groups themselves in order of the most heavily observed field
	phase_ref_groups.sort(key=lambda g: rank(g['targets'][0]))
	phase_calibrators = []
	for group in phase_ref_groups:
		phase_calibrators += [c for c in group['calibrators']
							  if c not in phase_calibrators]

	## A pipeline run needs something to fringe fit on - fall back to the
	## brightest looking calibrator if the schedule had no obvious one
	if not fringe_finders and phase_calibrators:
		print('WARNING: no fringe finder identified, using the phase '
			  'calibrator(s) with the longest scans instead')
		fringe_finders = [sorted(phase_calibrators,
								 key=lambda n: -stats[n]['median_duration'])[0]]

	if verbose:
		def row(name, role, indent=0):
			separation = '%.2f deg' % separations[name] \
				if name in separations and name not in targets else ''
			print('%-22s %7d %12s %12s %9s   %s'
				  % (' ' * indent + name, stats[name]['nscans'],
					 format_time(total_times[name]),
					 format_time(stats[name]['median_duration']), separation, role))

		print('')
		print('%-22s %7s %12s %12s %9s   %s'
			  % ('SOURCE', 'NSCANS', 'TIME', 'MEDIAN SCAN', 'SEP', 'CLASSIFICATION'))
		print('-' * 90)

		## Show each science field with the calibrators that serve it, in the
		## order they will be solved
		listed = []
		for group in phase_ref_groups:
			for name in group['targets']:
				row(name, 'target')
				listed.append(name)
			for k, name in enumerate(group['calibrators']):
				row(name, 'phase calibrator %d/%d'
					% (k + 1, len(group['calibrators'])), indent=2)
				listed.append(name)
		for name in targets + phase_calibrators + fringe_finders + list(names):
			if name in listed:
				continue
			row(name, 'fringe finder' if name in fringe_finders else
				('phase calibrator' if name in phase_calibrators else 'target'))
			listed.append(name)

		chained = [g for g in phase_ref_groups if len(g['calibrators']) > 1]
		if chained:
			print('')
			print('Chained calibrators are ordered furthest from their target '
				  'first, so that the\ncalibration works inwards towards the '
				  'science field.')
		if len(phase_ref_groups) > 1:
			print('')
			print('%d independent target/phase calibrator pairs found, so all '
				  'phase calibrators\nare solved in a single pass - see '
				  'phase_referencing/select_calibrators.' % len(phase_ref_groups))
		print('')

	return {'fringe_finders': fringe_finders,
			'phase_calibrators': phase_calibrators,
			'targets': targets,
			'groups': phase_ref_groups,
			'separations': separations,
			'stats': stats}


def order_refants(antennas):
	"""Order the observing antennas by the standard reference antenna preference."""
	antennas = [a.upper() for a in antennas]
	ordered = [a for a in STATION_PREFERENCE if a in antennas]
	ordered += [a for a in antennas if a not in ordered]
	return ordered


###################################################################################################
# Building the parset
###################################################################################################

def edge_channel_spec(nchan, percent=2.0):
	"""Edge channel flagging spec, guaranteeing at least one channel per edge."""
	if nchan is None or nchan <= 0:
		return '%g%%' % percent
	if int(round((percent / 100.) * nchan)) >= 1:
		return '%g%%' % percent
	return int(max(1, round(0.05 * nchan)))


def calibration_passes(roles):
	"""
	Split the phase calibrators into the fringe-fit passes of select_calibrators.

	Every caltable written by run_phase_referencing is appended with
	gainfield='', and apply_target then applies all of them to every target,
	which picks up the nearest solution in time from each pass. Independent
	target/calibrator pairs therefore have to be solved together in a single
	pass: giving each its own pass would transfer every other pair's
	solutions onto every target, from a completely different part of the sky.

	Only a chain of calibrators serving the same field can be split over
	successive passes, because there that transfer is exactly the intent -
	the outer calibrator is solved first and its solutions are carried onto
	the inner one before it is solved in turn.
	"""
	groups = roles.get('groups') or []
	calibrators = list(roles['phase_calibrators'])

	if len(groups) == 1 and len(groups[0]['calibrators']) > 1:
		return [[c] for c in groups[0]['calibrators']]
	if calibrators:
		return [calibrators]
	return []


def phase_referencing_lists(template, ncals):
	"""Replicate the template self-calibration sequence for each phase calibrator."""
	keys = ['cal_type', 'sol_interval', 'combine', 'interp_flagged']
	defaults = {'cal_type': ["f", "f", "f", "p", "p", "ap", "ap", "ap", "ap", "f", "p"],
				'sol_interval': ["inf", "inf", "inf", "inf", "1min", "inf", "inf",
								 "inf", "1min", "inf", "1min"],
				'combine': ["spw", "spw", "", "", "", "spw", "", "", "spw", "", ""],
				'interp_flagged': [True] * 11}

	out = {}
	for key in keys:
		sequence = defaults[key]
		if key in template and len(template[key]) > 0:
			sequence = template[key][0]
		out[key] = [list(sequence) for _ in range(max(ncals, 1))]
	out['pass_ants'] = [[""] for _ in range(max(ncals, 1))]
	return out


def build_parset(template, info, roles, args):
	"""Fill a copy of the template parset with everything we have inferred."""
	params = json.loads(json.dumps(template), object_pairs_hook=OrderedDict)
	notes = []
	tune_cal_types = getattr(args, 'tune_cal_types', False)

	project_code = (args.project_code or info.get('project_code') or '').lower()
	cwd = os.path.abspath(args.cwd)

	pipe_path = os.path.dirname(os.path.realpath(__file__))
	if os.path.dirname(pipe_path) == cwd:
		pipe_path = os.path.basename(pipe_path)

	# ---------------------------------------------------------------- global
	glob = params['global']
	glob['project_code'] = project_code
	glob['cwd'] = cwd
	glob['vlbipipe_path'] = pipe_path
	glob['fitsidi_files'] = ["auto"]
	glob['fitsidi_path'] = (os.path.dirname(info['files'][0])
							if info.get('files') else cwd)
	glob['refant'] = order_refants(info['antennas'])
	glob['fringe_finders'] = roles['fringe_finders']
	glob['phase_calibrators'] = roles['phase_calibrators']
	glob['targets'] = roles['targets']
	glob['use_initial_model'] = {}
	if args.email is not None:
		glob['email_progress'] = args.email
	if args.job_manager is not None:
		glob['job_manager'] = args.job_manager

	# ---------------------------------------------------------- prepare_data
	prep = params['prepare_data']
	search_dirs = [glob['fitsidi_path'], os.path.dirname(glob['fitsidi_path']),
				   cwd, os.path.dirname(info.get('vex_file') or '')]
	antab = find_aux_file(search_dirs, project_code, ['.antab', '.antabfs'])
	if antab is not None:
		default_antab = os.path.join(cwd, '%s.antab' % project_code)
		prep['antab_file'] = 'auto' if os.path.exists(default_antab) \
			else antab
		prep['gaincurve']['prep_type'] = 'convert'
		notes.append('Antab file: %s' % antab)
	else:
		prep['antab_file'] = 'auto'
		if info.get('telescope', '').upper() in ('VLBA', 'LBA'):
			prep['gaincurve']['prep_type'] = 'append'
		notes.append('No antab file found - Tsys/gain curve must already be in '
					 'the FITS-IDI files, or provide one before running '
					 'prepare_data')

	flagfile = find_aux_file(search_dirs, project_code, ['.uvflg', '.flag'])
	prep['flag_file'] = 'auto'
	if flagfile is not None:
		notes.append('Observatory flag file: %s' % flagfile)
	params['init_flag']['manual_flagging']['flag_file'] = \
		'manual_flagging_%s.txt' % project_code

	# ------------------------------------------------------- import_fitsidi
	if info.get('int_time'):
		## a scan gap must be longer than a few integrations to be meaningful
		params['import_fitsidi']['scan_gap'] = float(max(15.0,
														 5 * info['int_time']))

	# ----------------------------------------------------------- apriori_cal
	correlator = (info.get('correlator') or '').upper()
	if 'DIFX' in correlator or 'VLBA' in correlator or 'SOCORRO' in correlator:
		params['apriori_cal']['correlator'] = 'difx'
	elif correlator:
		params['apriori_cal']['correlator'] = 'default'
	if info.get('int_time'):
		params['apriori_cal']['accor_options']['solint'] = \
			'%ds' % int(max(30, 15 * info['int_time']))

	# ------------------------------------------------------------- init_flag
	params['init_flag']['flag_edge_chans']['edge_chan_flag'] = \
		edge_channel_spec(info.get('nchan'))
	params['init_flag']['AO_flag_fields'] = [list(roles['targets'])] \
		if roles['targets'] else [[]]
	strategy = params['init_flag']['AO_flag_strategy']
	if strategy and isinstance(strategy[0], str):
		params['init_flag']['AO_flag_strategy'] = \
			['%s/aoflag_strategies/%s' % (pipe_path,
										  os.path.basename(strategy[0]))]

	# --------------------------------------------------------- fit_autocorrs
	params['fit_autocorrs']['select_calibrators'] = \
		list(roles['fringe_finders']) or list(roles['phase_calibrators'])

	# -------------------------------------------- sub_band_delay / bandpass
	## 'default' makes both steps track global/fringe_finders automatically
	sbd = params['sub_band_delay']
	sbd['select_calibrators'] = [["default"]]
	sbd['time_range'] = [""]
	sbd['min_snr'] = [sbd['min_snr'][0] if isinstance(sbd['min_snr'], list)
					  else sbd['min_snr']]
	ff_scan = np.median([roles['stats'][f]['median_duration']
						 for f in roles['fringe_finders']]) \
		if roles['fringe_finders'] else 60.
	## solve on a fraction of a fringe finder scan, rounded to a tidy interval
	sbd['sol_interval'] = ['%ds' % int(max(30, min(60, 10 * round(ff_scan / 20.))))]

	snr = roles.get('snr') or {}
	int_time = info.get('int_time', 2.)
	nspw = info.get('nspw', 1)
	freq = info.get('ref_freq') or 0.
	t_coh = coherence_time(freq)
	threshold = SNR_MARGIN * float(np.atleast_1d(sbd['min_snr'])[0])
	measured = [snr[f] for f in roles['fringe_finders'] if f in snr]
	## the whole pass is solved together, so the weakest one sets the pace
	weakest = min(measured, key=lambda m: m['snr_antenna']) if measured else None
	fixed, combine, changes = fix_solints(sbd['sol_interval'], ff_scan, weakest,
										  int_time, threshold, nspw,
										  cal_types=['f'], max_tau=t_coh)
	sbd['sol_interval'] = fixed
	if changes:
		notes.append('sub_band_delay solution interval %s' % ', '.join(changes))
	if combine:
		notes.append('the fringe finder(s) reach SNR %.0f only with the '
					 'spws combined, but sub_band_delay has to solve per '
					 'spw - expect flagged solutions' % threshold)

	bpass = params['bandpass_cal']
	bpass['same_as_sbd_cal'] = True
	bpass['select_calibrators'] = [["default"]]
	bpass['time_range'] = [""]

	# ---------------------------------------------------- phase_referencing
	phaseref = params['phase_referencing']
	passes = calibration_passes(roles)
	phaseref['select_calibrators'] = passes or 'default'
	phaseref.update(phase_referencing_lists(phaseref, len(passes)))
	if len(passes) == 1 and len(passes[0]) > 1:
		notes.append('%d target/phase calibrator pairs are solved in one '
					 'phase_referencing pass so that each target picks up its '
					 'own calibrator - do not split them into separate passes'
					 % len(roles.get('groups') or []))

	## Scale the measured SNR onto each pass: the template sequence keeps its
	## shape, and only the intervals the calibrators cannot support are
	## stretched to something that will actually solve
	threshold = SNR_MARGIN * float(phaseref['min_snr'])
	for i, pass_calibrators in enumerate(passes):
		measured = [c for c in pass_calibrators if c in snr]
		weakest_name = min(measured, key=lambda c: snr[c]['snr_antenna']) \
			if measured else None
		weakest = snr[weakest_name] if weakest_name else None
		scan_length = np.median([roles['stats'][c]['median_duration']
								 for c in pass_calibrators
								 if c in roles['stats']] or [60.])

		fixed, combine, changes = fix_solints(phaseref['sol_interval'][i],
											  scan_length, weakest, int_time,
											  threshold, nspw,
											  phaseref['cal_type'][i],
											  max_tau=t_coh)
		phaseref['sol_interval'][i] = fixed
		if changes:
			notes.append('phase_referencing pass %d intervals: %s'
						 % (i + 1, ', '.join(sorted(set(changes)))))
		if weakest is None:
			continue
		if combine:
			phaseref['combine'][i] = ['spw'] * len(phaseref['combine'][i])
			notes.append('pass %d combines the spws throughout - %s only '
						 'reaches SNR %.0f per spw, against the %.0f needed'
						 % (i + 1, weakest_name,
							scaled_snr(weakest, weakest['tau']), threshold))
		if scaled_snr(weakest, weakest['tau'], nspw, True) < threshold:
			notes.append('%s is too weak to fringe fit even with every spw '
						 'combined over a whole scan (SNR %.0f) - consider '
						 'in-beam calibration or the mssc step'
						 % (weakest_name,
							scaled_snr(weakest, weakest['tau'], nspw, True)))

		## Steps the calibrator cannot actually solve are dropped rather than
		## left to produce flagged solutions. Amplitude self-calibration is
		## held to a higher bar than a phase-only solve.
		if not tune_cal_types:
			continue
		keep = []
		for j, cal_type in enumerate(phaseref['cal_type'][i]):
			tau = parse_solint(phaseref['sol_interval'][i][j], weakest['tau'])
			needed = threshold * (AMPLITUDE_SNR_FACTOR
								  if cal_type in ('a', 'ap') else 1.)
			if tau is not None and \
			   scaled_snr(weakest, tau, nspw, combine) >= needed:
				keep.append(j)
		if not keep:
			keep = [0]
		if len(keep) < len(phaseref['cal_type'][i]):
			dropped = [phaseref['cal_type'][i][j]
					   for j in range(len(phaseref['cal_type'][i]))
					   if j not in keep]
			notes.append('pass %d: dropped %d step(s) (%s) that %s cannot '
						 'solve at SNR %.0f'
						 % (i + 1, len(dropped), ','.join(dropped),
							weakest_name, threshold))
			for key in ('cal_type', 'sol_interval', 'combine', 'interp_flagged'):
				phaseref[key][i] = [phaseref[key][i][j] for j in keep]

	# ------------------------------------------------- frequency dependencies
	if freq > 0:
		dispersive = freq < DISPERSIVE_MAX_FREQ
		params['apriori_cal']['ionex_options']['run'] = freq < IONOSPHERE_MAX_FREQ
		sbd['do_disp_delays'] = dispersive

		## A dispersive term is another free parameter, so only fit it in the
		## phase referencing when the calibrators can spare the SNR
		phase_ref_dispersive = dispersive
		measured = [snr[c] for c in roles['phase_calibrators'] if c in snr]
		if dispersive and measured:
			weakest = min(measured, key=lambda m: m['snr_antenna'])
			phase_ref_dispersive = \
				scaled_snr(weakest, weakest['tau'], nspw) >= 3 * threshold
		phaseref['do_disp_delays'] = bool(phase_ref_dispersive)
		sbd['do_disp_delays'] = bool(dispersive)

		notes.append('at %.2f GHz: %s a dispersive delay term (%s in the phase '
					 'referencing), %s an ionospheric TEC correction, and phase '
					 'solves capped at the ~%s coherence time'
					 % (freq / 1e9,
						'fitting' if dispersive else 'not fitting',
						'fitted' if phase_ref_dispersive else 'not fitted',
						'applying' if freq < IONOSPHERE_MAX_FREQ else 'skipping',
						format_time(t_coh) if t_coh else 'unknown'))

	# ---------------------------------------------------------- apply_to_all
	apply_all = params['apply_to_all']
	apply_all['target_path'] = os.path.join(cwd, 'data')
	apply_all['target_outpath'] = os.path.join(cwd, 'output')
	apply_all['pbcor']['vex_file'] = os.path.basename(info['vex_file']) \
		if info.get('vex_file') else ''
	if roles['targets']:
		target = roles['targets'][0]
		position = info['sources'].get(target) \
			or info.get('vex_sources', {}).get(target)
		if position is not None:
			apply_all['pbcor']['pointing_centre'] = \
				list(deg_to_casa_coords(position['ra'], position['dec']))
			notes.append('apply_to_all/pbcor pointing centre taken from the '
						 'phase centre of %s - correct this by hand for '
						 'multi-phase-centre data' % target)

	return params, notes


###################################################################################################
# Entry point
###################################################################################################

def parse_args(argv=None):
	parser = argparse.ArgumentParser(
		description='Generate a VLBI pipeline parset from FITS-IDI files '
					'and/or a vex schedule.',
		formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-i', '--idi', default=None,
						help='FITS-IDI file, or a directory containing them')
	parser.add_argument('-v', '--vex', default=None,
						help='vex/vix schedule file (auto-detected if omitted)')
	parser.add_argument('-o', '--output', default='vlbi_pipe_params.json',
						help='output parset')
	parser.add_argument('-t', '--template', default=None,
						help='parset used for everything that cannot be '
							 'inferred (default: the one shipped with the '
							 'pipeline)')
	parser.add_argument('--cwd', default=None,
						help='working directory the pipeline will run in '
							 '(default: the current directory)')
	parser.add_argument('--project-code', default=None,
						help='override the project code found in the data')
	parser.add_argument('--email', default=None,
						help='override email_progress')
	parser.add_argument('--job-manager', default=None,
						choices=['slurm', 'pbs', 'bash'],
						help='override job_manager')
	parser.add_argument('--fringe-finders', default=None,
						help='comma separated list, overrides the automatic '
							 'classification')
	parser.add_argument('--phase-calibrators', default=None,
						help='comma separated list, overrides the automatic '
							 'classification')
	parser.add_argument('--targets', default=None,
						help='comma separated list, overrides the automatic '
							 'classification')
	parser.add_argument('--estimate-snr', action='store_true',
						help='measure the fringe SNR of each calibrator from '
							 'one scan of raw data and size the solution '
							 'intervals from it (needs the FITS-IDI files)')
	parser.add_argument('--tune-cal-types', action='store_true',
						help='also drop self-calibration steps the calibrators '
							 'are too weak to solve, amplitude steps first '
							 '(implies --estimate-snr)')
	parser.add_argument('--max-separation', type=float, default=10.0,
						help='maximum separation (deg) for two sources to be '
							 'considered a phase-referencing pair')
	parser.add_argument('--dry-run', action='store_true',
						help='print the parset instead of writing it')
	parser.add_argument('--no-vex', action='store_true',
						help='ignore any vex file')
	return parser.parse_args(argv)


def main(argv=None):
	args = parse_args(argv)

	if args.idi is None and args.vex is None:
		args.idi = os.getcwd()
	if args.cwd is None:
		args.cwd = os.getcwd()

	idifiles = find_fitsidi_files(args.idi)
	idi_info = None
	if idifiles:
		print('Found %d FITS-IDI file(s)' % len(idifiles))
		idi_info = read_fitsidi(idifiles)
	elif args.idi is not None:
		print('WARNING: no FITS-IDI files found in %s' % args.idi)

	vexfile = args.vex
	if vexfile is None and not args.no_vex:
		search = [args.cwd]
		if idifiles:
			search.insert(0, os.path.dirname(idifiles[0]))
			search.insert(1, os.path.dirname(os.path.dirname(idifiles[0])))
		vexfile = find_vex_file(search,
								idi_info.get('project_code') if idi_info else None)
		if vexfile is not None:
			print('Auto-detected vex file %s' % vexfile)
	if args.no_vex:
		vexfile = None

	vex_info = None
	if vexfile is not None:
		try:
			vex_info = read_vex(vexfile)
			print('Read schedule from %s (%d scans)'
				  % (os.path.basename(vexfile), len(vex_info['scans'])))
		except Exception as error:
			print('WARNING: could not parse %s (%s) - continuing without it'
				  % (vexfile, error))

	## A stray schedule from a different experiment would silently corrupt the
	## source classification, so make sure both describe the same observation
	if vex_info is not None and idi_info is not None:
		idi_code = (idi_info.get('project_code') or '').upper()
		vex_code = (vex_info.get('project_code') or '').upper()
		if idi_code and vex_code and idi_code != vex_code:
			if args.vex is None:
				print('WARNING: auto-detected %s belongs to %s, not %s '
					  '- ignoring it' % (os.path.basename(vexfile), vex_code,
										 idi_code))
				vex_info = None
			else:
				print('WARNING: %s belongs to %s but the FITS-IDI files are '
					  '%s - using it anyway as it was given explicitly'
					  % (os.path.basename(vexfile), vex_code, idi_code))

	info = merge_info(idi_info, vex_info)
	if info is None or not info.get('scans'):
		print('ERROR: no FITS-IDI files or vex schedule could be read - '
			  'nothing to work from')
		return 1

	print('')
	print('Project code : %s' % info.get('project_code', 'unknown'))
	print('Array        : %s' % info.get('telescope', 'unknown'))
	print('Correlator   : %s' % info.get('correlator', 'unknown'))
	print('Antennas     : %s' % ', '.join(info['antennas']))
	if info.get('ref_freq'):
		print('Frequency    : %.3f GHz, %d x %d channels, %.1f MHz total'
			  % (info['ref_freq'] / 1e9, info.get('nspw', 1),
				 info.get('nchan', 1), info.get('bandwidth', 0.0) / 1e6))
	if info.get('start_mjd'):
		print('Observed     : MJD %.4f - %.4f (%s)'
			  % (info['start_mjd'], info['end_mjd'],
				 format_time((info['end_mjd'] - info['start_mjd']) * 86400.)))
	print('Scans        : %d' % len(info['scans']))

	roles = classify_sources(info, max_sep=args.max_separation)

	## Manual overrides always win
	for key, value in (('fringe_finders', args.fringe_finders),
					   ('phase_calibrators', args.phase_calibrators),
					   ('targets', args.targets)):
		if value is not None:
			roles[key] = [v.strip() for v in value.split(',') if v.strip()]
			print('Overriding %s with %s' % (key, ', '.join(roles[key])))

	## An overridden target must not stay behind in the calibrator lists.
	## Fringe finders may legitimately double as phase calibrators, so those
	## two are left alone.
	for key in ('phase_calibrators', 'fringe_finders'):
		demoted = [n for n in roles[key] if n in roles['targets']]
		if demoted:
			roles[key] = [n for n in roles[key] if n not in roles['targets']]
			print('Removed %s from %s - now a target'
				  % (', '.join(demoted), key))

	## Overriding either list invalidates the groups worked out from the
	## schedule, so rebuild them by attaching each calibrator to its nearest
	## target. A calibrator order given on the command line is kept as it
	## stands, since it was chosen deliberately.
	if args.targets is not None or args.phase_calibrators is not None:
		regroup_roles(roles, info['sources'],
					  keep_order=args.phase_calibrators is not None)
		for group in roles['groups']:
			print('%s <- %s' % (', '.join(group['targets']),
								', '.join(group['calibrators'])))

	if args.tune_cal_types:
		args.estimate_snr = True

	if args.estimate_snr:
		if info.get('row_index'):
			roles['snr'] = measure_calibrator_snr(
				info, roles['fringe_finders'] + roles['phase_calibrators'])
		else:
			print('WARNING: --estimate-snr needs the FITS-IDI files, and only '
				  'a vex file was read - skipping')

	template_file = args.template or os.path.join(
		os.path.dirname(os.path.realpath(__file__)), 'vlbi_pipe_params.json')
	if not os.path.exists(template_file):
		print('ERROR: template parset %s does not exist' % template_file)
		return 1
	with open(template_file) as f:
		template = json.load(f, object_pairs_hook=OrderedDict)

	params, notes = build_parset(template, info, roles, args)
	output = json.dumps(params, indent=4)

	if args.dry_run:
		print(output)
	else:
		with open(args.output, 'w') as f:
			f.write(output + '\n')
		print('Wrote %s (template: %s)' % (os.path.abspath(args.output),
										   template_file))

	if notes:
		print('')
		print('Please check:')
		for note in notes:
			print('  * %s' % note)

	if not roles['targets']:
		print('  * no target was identified - set global/targets by hand')
	if not roles['phase_calibrators']:
		print('  * no phase calibrator was identified - set '
			  'global/phase_calibrators by hand')

	return 0


if __name__ == '__main__':
	sys.exit(main())
