# vex.py
# a interferometric array vex schedule class
#
#    Copyright (C) 2018 Hotaka Shiokawa
#    Heavily modified by Jack Radcliffe 2021
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import range
from builtins import object

import numpy as np
import re
import math


import os

###################################################################################################
# Vex object
###################################################################################################


class Vex(object):
	"""Read in observing schedule data from .vex files.
	   Assumes there is only 1 MODE in vex file
	   Attributes:
		   filename (str): The .vex filename.
		   source (str): The source name.
		   metalist (list): The observation information.
		   sched (list): The schedule information.
		   array (Array): an Array object of sites.
	"""

	def __init__(self, filename):

		f = open(filename)
		raw = f.readlines()
		f.close()

		self.filename = filename

		# Divide 'raw' data into sectors of '$' marks
		# ASSUMING '$' is the very first character in a line (no space in front)
		metalist = []  # meaning list of metadata

		for i in range(len(raw)):
			if raw[i][0] == '$':
				temp = [raw[i]]
				break

		for j in range(i + 1, len(raw)):
			if raw[j][0] != '$':
				temp.append(raw[j])
			elif raw[j][0] == '$':
				metalist.append(temp)
				temp = [raw[j]]
			else:
				print('Something is wrong.')
		metalist.append(temp)  # don't forget to add the final one
		self.metalist = metalist

		# Extract desired information
		# SOURCE ========================================================
		SOURCE = self.get_sector('SOURCE')
		source = {}
		indef = False

		for i in range(len(SOURCE)):

			line = SOURCE[i]
			if line[0:3] == "def":
				indef = True

			if indef:
				ret = self.get_variable("source_name", line)
				if len(ret) > 0:
					source_name = ret
				ret = self.get_variable("ra", line)
				if len(ret) > 0:
					ra = ret
				ret = self.get_variable("dec", line)
				if len(ret) > 0:
					dec = ret
				ret = self.get_variable("ref_coord_frame", line)
				if len(ret) > 0:
					ref_coord_frame = ret

				if line[0:6] == "enddef":
					source[source_name] = {'ra': ra, 'dec': dec,
								   'ref_coord_frame': ref_coord_frame}
					indef = False

		self.source = source

		# FREQ ==========================================================
		FREQ = self.get_sector('FREQ')
		indef = False
		nfreq = 0
		for i in range(len(FREQ)):

			line = FREQ[i]
			if line[0:3] == "def":
				if nfreq > 0:
					print("Not implemented yet.")
				nfreq += 1
				indef = True

			if indef:
				idx = line.find('chan_def')
				if idx >= 0 and line[0] != '*':
					chan_def = re.findall(r"[-+]?\d+[\.]?\d*", line)
					self.freq = float(chan_def[0]) * 1.e6
					self.bw_hz = float(chan_def[1]) * 1.e6

				if line[0:6] == "enddef":
					indef = False

		# SITE ==========================================================
		SITE = self.get_sector('SITE')
		sites = []
		site_ID_dict = {}
		indef = False

		for i in range(len(SITE)):

			line = SITE[i]
			if line[0:3] == "def":
				indef = True

			if indef:
				# get site_name and SEFD
				ret = self.get_variable("site_name", line)
				if len(ret) > 0:
					site_name = ret
					#SEFD = self.get_SEFD(site_name)

				# making dictionary of site_ID:site_name
				ret = self.get_variable("site_ID", line)
				if len(ret) > 0:
					site_ID_dict[ret] = site_name

				# get site_position
				ret = self.get_variable("site_position", line)
				if len(ret) > 0:
					site_position = re.findall(r"[-+]?\d+[\.]?\d*", line)

				# same format as Andrew's array tables
				if line[0:6] == "enddef":
					sites.append([site_name, site_position[0],
								  site_position[1], site_position[2]])
					indef = False

		# Construct Array() object of Andrew's format
		# mimic the function "load_array(filename)"
		# TODO this does not store d-term and pol cal. information!
		#tdataout = [np.array((x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[4]),
		#					  0.0, 0.0, 0.0, 0.0, 0.0)) for x in sites]

		tdataout = 0
		self.array = tdataout

		# SCHED  =========================================================
		SCHED = self.get_sector('SCHED')
		sched = []
		inscan = False

		for i in range(len(SCHED)):

			line = SCHED[i]
			if line[0:4] == "scan":
				inscan = True
				temp = {}
				temp['scan'] = {}
				cnt = 0

			if inscan:
				ret = self.get_variable("start", line)
				if len(ret) > 0:
					mjd, hr = vexdate_to_MJD_hr(ret)  # convert vex time format to mjd and hour
					temp['mjd_floor'] = mjd
					temp['start_hr'] = hr

				ret = self.get_variable("mode", line)
				if len(ret) > 0:
					temp['mode'] = ret

				ret = self.get_variable("source", line)
				if len(ret) > 0:
					temp['source'] = ret

				ret = self.get_variable("station", line)
				if len(ret) > 0:
					site_ID = ret
					site_name = site_ID_dict[site_ID]  # convert to more familier site name
					sdur = re.findall(r"[-+]?\d+[\.]?\d*", line)
					s_st = float(sdur[0])  # start time in sec
					s_en = float(sdur[1])  # end time in sec
					d_size = float(sdur[2])  # data size(?) in GB
					temp['scan'][cnt] = {'site': site_name, 'scan_sec_start': s_st,
										 'scan_sec': s_en, 'data_size': d_size}
					cnt += 1

				if line[0:7] == "endscan":
					sched.append(temp)
					inscan = False

		self.sched = sched

	# Function to obtain a desired sector from 'metalist'

	def get_sector(self, sname):
		"""Obtain a desired sector from 'metalist'.
		"""

		for i in range(len(self.metalist)):
			if sname in self.metalist[i][0]:
				return self.metalist[i]
		print('No sector named %s' % sname)
		return False

	# Function to get a value of 'vname' in a line which has format of
	# 'vname' = value ;(or :)
	def get_variable(self, vname, line):
		"""Function to get a value of 'vname' in a line.
		"""

		idx = self.find_variable(vname, line)
		name = ''
		if idx >= 0:
			start = False
			for i in range(idx + len(vname), len(line)):
				if start is True:
					if line[i] == ';' or line[i] == ':':
						break
					elif line[i] != ' ':
						name += line[i]
				if start is False and line[i] != ' ' and line[i] != '=':
					break
				if line[i] == '=':
					start = True
		return name

	# check if a variable 'vname' exists by itself in a line.
	# returns index of vname[0] in a line, or -1
	def find_variable(self, vname, line):
		"""Function to find a variable 'vname' in a line.
		"""
		idx = line.find(vname)
		if ((idx > 0 and line[idx - 1] == ' ') or idx == 0) and line[0] != '*':
			if idx + len(vname) == len(line):
				return idx
			if (line[idx + len(vname)] == '=' or
			   line[idx + len(vname)] == ' ' or
			   line[idx + len(vname)] == ':' or
			   line[idx + len(vname)] == ';'):
				return idx
		return -1

	# Find SEFD for a given station name.
	# For now look for it in Andrew's tables
	# Vex files could have SEFD sector.
	def get_SEFD(self, station):
		"""Find SEFD for a given station.
		"""
		f = open(os.path.dirname(os.path.abspath(__file__)) + "/../arrays/SITES.txt")
		sites = f.readlines()
		f.close()
		for i in range(len(sites)):
			if sites[i].split()[0] == station:
				return float(re.findall(r"[-+]?\d+[\.]?\d*", sites[i])[3])
		print('No station named %s' % station)
		return 10000.  # some arbitrary value

	# Find the time that any station starts observing the source in MJD.
	# Find the time that the last station stops observing the source in MHD.
	def get_obs_timerange(self, source):
		"""Find the time that any station starts observing the source in MJD,
		   and the time that the last station stops observing the source.
		"""

		sched = self.sched
		first = True
		for i_scan in range(len(sched)):
			if sched[i_scan]['source'] == source and first is True:
				Tstart_hr = sched[i_scan]['start_hr']
				mjd_s = sched[i_scan]['mjd_floor'] + Tstart_hr / 24.
				first = False
			if sched[i_scan]['source'] == source and first is False:
				Tstop_hr = sched[i_scan]['start_hr'] + sched[i_scan]['scan'][0]['scan_sec'] / 3600.
				mjd_e = sched[i_scan]['mjd_floor'] + Tstop_hr / 24.

		return mjd_s, mjd_e

# =================================================================
# =================================================================

# Function to find MJD (int!) and hour in UT from vex format,
# e.g, 2016y099d05h00m00s

def jd_to_mjd(jd):
	"""
	Convert Julian Day to Modified Julian Day
	
	Parameters
	----------
	jd : float
		Julian Day
		
	Returns
	-------
	mjd : float
		Modified Julian Day
	
	"""
	return jd - 2400000.5

def date_to_jd(year,month,day):
	"""
	Convert a date to Julian Day.
	
	Algorithm from 'Practical Astronomy with your Calculator or Spreadsheet', 
		4th ed., Duffet-Smith and Zwart, 2011.
	
	Parameters
	----------
	year : int
		Year as integer. Years preceding 1 A.D. should be 0 or negative.
		The year before 1 A.D. is 0, 10 B.C. is year -9.
		
	month : int
		Month as integer, Jan = 1, Feb. = 2, etc.
	
	day : float
		Day, may contain fractional part.
	
	Returns
	-------
	jd : float
		Julian Day
		
	Examples
	--------
	Convert 6 a.m., February 17, 1985 to Julian Day
	
	>>> date_to_jd(1985,2,17.25)
	2446113.75
	
	"""
	if month == 1 or month == 2:
		yearp = year - 1
		monthp = month + 12
	else:
		yearp = year
		monthp = month
	
	# this checks where we are in relation to October 15, 1582, the beginning
	# of the Gregorian calendar.
	if ((year < 1582) or
		(year == 1582 and month < 10) or
		(year == 1582 and month == 10 and day < 15)):
		# before start of Gregorian calendar
		B = 0
	else:
		# after start of Gregorian calendar
		A = math.trunc(yearp / 100.)
		B = 2 - A + math.trunc(A / 4.)
		
	if yearp < 0:
		C = math.trunc((365.25 * yearp) - 0.75)
	else:
		C = math.trunc(365.25 * yearp)
		
	D = math.trunc(30.6001 * (monthp + 1))
	
	jd = B + C + D + day + 1720994.5
	
	return jd
	


def vexdate_to_MJD_hr(vexdate):
	"""Find the integer MJD and UT hour from vex format date.
	"""
	time = re.findall(r"[-+]?\d+[\.]?\d*", vexdate)
	year = int(time[0])
	date = int(time[1])
	yeardatetime = ("%04i" % year) + ':' + ("%03i" % date) + ":00:00:00.000"
	try:
		from astropy.time import Time
		t = Time(yeardatetime, format='yday')
		mjd = t.mjd
	except:
		from datetime import datetime
		res = datetime.strptime(str(year)+ "-" +str(date), "%Y-%j").strftime("%d-%m-%Y").split('-')
		t = date_to_jd(int(res[2]),int(res[1]),int(res[0]))
		mjd = jd_to_mjd(t)
	hour = int(time[2]) + float(time[3]) / 60. + float(time[4]) / 60. / 60.

	return mjd, hour