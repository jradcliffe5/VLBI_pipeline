#!/usr/bin/env python

## =============================================================================
## =============================================================================
##
## tec_maps.py
##
##    Created by J. E. Kooi   2014/04/25  v2.0
##    Modified by gmoellen    2014/07/21  v2.1 (minor mods, mostly semantics)
##    Modified by J. E. Kooi  2014/09/17  v2.2 (minor mods, formating and
##                                              ~ Test for network connection
##                                              ~ Heirarchy of IGS-related 
##                                                data products added
##                                              ~ Added IGS RMS TEC maps
##                                              ~ Made IGS default data product)
##    Modified by gmoellen    2014/09/30  v2.3 (added simplified create method
##                                              that hides all of the MAPGPS-related
##                                              options, and thereby streamlines
##                                              approved general usage for
##                                              CASA 4.3)
##    Modified by J. E. Kooi   2015/01/29  v2.4 (Changed get_IGS_TEC to accept
##                                              IONEX format data with ANY grid 
##                                              spacing in deg. and time res in min)
##    Modified by J. E. Kooi   2015/03/2   v2.5 (Changed ztec_value for doplot = 
##                                              True to plot a red bar over the VTEC
##                                              to show the observing session)
##    Modified by gmoellen     2017/05/30  v2.6 Generate plot disk file
##    Modified by bkent        2017/10-31  v2.7 Fixed VisibleDeprecationWarning: 
##                                              using a non-integer 
##                                              number instead of an integer will 
##                                              result in an error in the future
##
##
##    Tested in CASA 4.3.0 and 4.2.1 on RHEL release 6.4 (Santiago)
##    Tested in CASA 4.3.0, 4.2.2, and 4.2.1 on Mac OS 10.8.5
##
##
##
## The purpose of this python module is to retrieve vertical TEC/DTEC maps from
## either IGS (housed on the CDDIS servers) or MAPGPS (housed on the Madrigal 
## servers).
##
## **** Currently, the MAPGPS is "turned off" and modification of line 306 ****
## **** is required to turn this functionality back "on."                  ****
##
## The IGS Final Product maps represent a combined TEC map:
## The different IGS Ionosphere Associate Analysis Centers IAAC TEC maps have 
## been computed with different approaches but with a common formal resolution
## of 2 hours, 5 degrees, and 2.5 degrees in UT, longitude, and latitude 
## (details can be found in e.g. Schaer, 1999; Feltens, 1998; 
## Mannucci et al., 1998; Gao et al.; Hernandez-Pajares et al.,1999). The four 
## IAACs TEC maps have been combined in an IGS combination product using weights
## obtained by two IGS Ionosphere Associate Validation Centers (IAVCs) from the
## corresponding performances in reproducing STEC and differences of STEC (IAVCs
## NRCAN and UPC respectively, see details in Feltens, 2002).
## ------ Krankowski & Sieradzki, 2013 (references can be found in this paper)
##
## The code has a hierarchy for IGS data products.  It will initially search for
## the IGS Final product data (available ~ 10-14 days after an observation) and,
## if unavailable, then the IGS Rapid Product (available in ~ 1-2 days) and,
## if unavailable, then the JPL Rapid Product. 
##
## The MAPGPS maps are computed with no pre-applied ionosphere model and, in 
## this sense, represent 'raw TEC data.' The benefit is that they have a formal
## resolution of 5 minutes, 1.0 degree, and 1.0 degree in UT, longitude, and 
## latitude (details can be found in Rideout & Coster, 2006).  The drawback is
## that the data is sparsely gridded in many locations (e.g., there are no GPS
## ground stations in the middle of the ocean) and there are sporadic gaps in
## the data at some locations (e.g., even over the United States).
##
## For now, users are encouraged to use the IGS Final Product maps instead of
## MAPGPS products because there is data at all grid points and times, 
## making it easier to deal with in the code.  The code for MAPGPS is also set
## to make a 'patch' over North America and therefore is not a global map.
## However, the code is included and need only be uncommented.  Feel free to
## experiment and compare the IGS and MAPGPS maps!
##
## This module calls several methods depending on the TEC/DTEC server and
##
##    (1) Produces a CASA image of the TEC data for
##        a) The whole world (IGS) (additional DTEC data image is output)
##        b) A 15 deg. patch centered on the VLA (MAPGPS)
##    (2) Optionally produces a vertical TEC/DTEC time series for the VLA
##
## !!!!! Important Note: In order to access the MAPGPS data, you must:
##    (1) Have "madrigalWeb.py" and "globalDownload.py" and 
##        "madrigal.head" in the working directory
##    (2) Provide your name, e-mail, and institution in the .create0 method to
##        access the Madrigal server
##
## References:
##
##    Krankowski, A., & Sieradzki, R. 2013, in International GNSS Service 
##        Technical Report, ed. R. Dach & Y. Jean, IGS Central Bureau 
##        (Astronomical Institute:University of Bern), 157
##    Rideout, W., & Coster, A. 2006, GPS Solutions, 10, 219
##
## =============================================================================
##
## Example Use:
##
##  (0) The default use provides the IGS Product:
##      > import tec_maps
##      > msname = 'visibilities.ms'
##      > CASA_image,CASA_RMS_image = tec_maps.create0(msname)
##
##  (1) IGS Product (w/out the vertical TEC/DTEC time series at the VLA)
##      > import tec_maps
##      > msname = 'visibilities.ms'
##      > CASA_image,CASA_RMS_image = tec_maps.create0(msname,'IGS')
##      > viewer(CASA_image)
##      > viewer(CASA_RMS_image)
##
##  (2) IGS Product (WITH the vertical TEC/DTEC time series at the VLA)
##      > import tec_maps
##      > msname = 'visibilities.ms'
##      > CASA_image,CASA_RMS_image = tec_maps.create0(msname,'IGS',True)
##      > viewer(CASA_image)
##      > viewer(CASA_RMS_image)
##
##  (3) IGS Product (WITH the vertical TEC/DTEC time series at the VLA and for
##      which the user specifies the output image name)
##      > import tec_maps
##      > msname = 'visibilities.ms'
##      > imagename = 'my_image'
##      > CASA_image,CASA_RMS_image = tec_maps.create0(msname,'IGS',True,imagename)
##      > viewer(CASA_image)
##      > viewer(CASA_RMS_image)
##
##  (4) MAPGPS (WITH the vertical TEC/DTEC time series for the VLA)
##      > import tec_maps
##      > msname = 'visibilities.ms'
##      > myname = 'John Doe'
##      > myemail = 'john-doe@place.edu'
##      > myplace = 'NRAO'
##      > CASA_image,CASA_RMS_image = 
##             tec_maps.create0(msname,'MAPGPS',True,'',myname,myemail,myplace)
##      > viewer(CASA_image)
##      > viewer(CASA_RMS_image)
##
##
## =============================================================================
## =============================================================================

try:
	# CASA 6
	import casatools
	from casatasks import *
	casalog.showconsole(True)
	import urllib.request as urllib2
	casa6=True
except:
	# CASA 5
	from casac import casac as casatools
	from taskinit import *
	import urllib2
	casa6=False

import glob, os, datetime
import numpy as np
from matplotlib import rc
import matplotlib.pyplot as plt

tb = casatools.table()
qa = casatools.quanta()
cs = casatools.coordsys()
ia = casatools.image()

workDir = '%s'%(os.getcwd()+'/')

def create(vis,doplot=False,imname=''):
	"""
## =============================================================================
##
## This method opens the .ms to determine the days of observation and calls the
## necessary functions to acquire the desired set of TEC/DTEC data.  The method
## finally calls ztec_value and make_image once it has the data.
##
## =============================================================================
##
## Inputs:
##    vis           type = string    Name of the measurement set for which to
##                                       acquire TEC/DTEC data
##    doplot        type = boolean   When True, this will open a plot of the 
##                                       interpolated TEC/DTEC at the VLA.
##    imname        type = string    Name of the output TEC Map optionally
##                                       specified by the user
##
## Returns:
##    Opens a plot showing the zenith TEC/DTEC for the VLA 
##    (if doplot = True) and the name of the CASA image file containing
##    the TEC map.
##
## =============================================================================
	
	Usage: 
		The default use provides the IGS Product:
		> vis = 'visibilities.ms'
		> CASA_image,CASA_RMS_image = tec_maps.create(vis)

		IGS Product (WITH the vertical TEC/RMS TEC time series at the VLA)
		> vis = 'visibilities.ms'
		> CASA_image,CASA_RMS_image = tec_maps.create(msname,plot_vla_tec = True)

		The TEC and RMS TEC images can then be examined using viewer:
		> viewer(CASA_image)
		> viewer(CASA_RMS_image)

		The TEC image should then be used in gencal (caltype='tecim') to
		generate a sampled caltable that will nominally correct for
		ionospheric effects
	"""
	# call the more general method
	return create0(ms_name=vis,plot_vla_tec=doplot,im_name=imname)


def create0(ms_name,tec_server='IGS',plot_vla_tec=False,im_name='',username='',user_email='',affiliation=''):
	"""
## =============================================================================
##
## This opens the .ms to determine the days of observation and calls the
## necessary functions to acquire the desired set of TEC/DTEC data.  The method
## finally calls ztec_value and make_image once it has the data.
##
## =============================================================================
##
## Inputs:
##    ms_name       type = string    Name of the measurement set for which to
##                                       acquire TEC/DTEC data
##    tec_server    type = string    Server from which to retrieve TEC/DTEC
##    plot_vla_tec  type = boolean   When True, this will open a plot of the 
##                                       interpolated TEC/DTEC at the VLA.
##    im_name       type = string    Name of the output TEC Map optionally
##                                       specified by the user
##    username      type = string    MAPGPS only: full name of user accessing
##                                       the site
##                                       ex: '<First> <Last>'
##    user_email    type = string    MAPGPS only: e-mail address at which the 
##                                       user can be reached
##                                       ex: '<name>@<place>.com'
##    affiliation   type = string    MAPGPS only: user's affiliated institute
##                                       ex: 'NRAO'
##
## Returns:
##    Opens a plot showing the zenith TEC/DTEC for the VLA 
##    (if plot_vla_tec = True) and the name of the CASA image file containing
##    the TEC map.
##
## =============================================================================
	
	Usage: 
		The default use provides the IGS Product:
		> msname = 'visibilities.ms'
		> CASA_image,CASA_RMS_image = tec_maps.create(msname)

		IGS Product (WITH the vertical TEC/RMS TEC time series at the VLA)
		> msname = 'visibilities.ms'
		> CASA_image,CASA_RMS_image = tec_maps.create(msname,plot_vla_tec = True)

		The TEC and RMS TEC images can then be examined using viewer:
		> viewer(CASA_image)
		> viewer(CASA_RMS_image)
	"""

	## Open the .ms to get the range in observation times
	tb.open(ms_name+'/OBSERVATION')
	obs_times = tb.getcol('TIME_RANGE')
	tb.close()

	t_min = min(obs_times)
	t_max = max(obs_times)
	
	## Calculate the reference time for the TEC map to be generated.
	ref_time  = 86400.*np.floor(t_min[0]/86400)
	ref_start = t_min[0]-ref_time
	ref_end   = t_max[0]-ref_time

	## Gets the day string and the integer number of days of observation (only tested for two continuous days)
	begin_day = qa.time(str(t_min[0])+'s',form='ymd')[0][:10]
	end_day = qa.time(str(t_max[0])+'s',form='ymd')[0][:10]
	num_of_days = int(np.floor((t_max[0]-t_min[0])/86400.))  # must be an int as used below!

	## Set up the number of times we need to go get TEC files
	if begin_day == end_day:
		call_num = 1
	elif num_of_days == 0:
		call_num = 2
	else:
		call_num = num_of_days+1

	## Set up the days for which we need to go get TEC files
	day_list = []
	next_day = begin_day
	for iter in range(call_num):
		day_list.append(next_day)
		next_day = qa.time(str(t_min[0]+86400.*(iter+1))+'s',form='ymd')[0][:10]

	## Runs the IGS methods
	if tec_server == 'IGS':
		ymd_date_num = 0
		array = []
		for ymd_date in day_list:
			points_long,points_lat,ref_long,ref_lat,incr_long,incr_lat,incr_time,num_maps,tec_array,tec_type = get_IGS_TEC(ymd_date)
			## Fill a new array with all the full set of TEC/DTEC values for all days in the observation set.
			if tec_type != '':
				if ymd_date_num == 0:
					full_tec_array = np.zeros((2,int(points_long),int(points_lat),(int(num_maps)-1)*int(call_num)+1))
					for iter in range(int(num_maps)):
						full_tec_array[:,:,:,iter] = tec_array[:,:,:,iter]
				else:
					## We remove map 0 for the current tec_array because it is a repeat of the last map from the previous tec_array
					for iter in range(int(num_maps-1)):
						full_tec_array[:,:,:,iter+int(num_maps)*ymd_date_num] = tec_array[:,:,:,iter+1]
			ymd_date_num +=1

		if tec_type != '':

			if im_name == '':
				prefix = ms_name
			else:
				prefix = im_name

			plot_name=''
			if plot_vla_tec:
				plot_name=prefix+'.IGS_TEC_at_site.png'

			ztec_value(-107.6184,34.0790,points_long,points_lat,ref_long,ref_lat,incr_long,\
						incr_lat,incr_time,ref_start,ref_end,int((num_maps-1)*call_num+1),\
						full_tec_array,plot_vla_tec,plot_name)

			CASA_image = make_image(prefix,ref_long,ref_lat,ref_time,incr_long,incr_lat,\
									incr_time*60,full_tec_array[0],tec_type,appendix = '.IGS_TEC')
			CASA_RMS_image = make_image(prefix,ref_long,ref_lat,ref_time,incr_long,incr_lat,\
									incr_time*60,full_tec_array[1],tec_type,appendix = '.IGS_RMS_TEC')
		else:
			CASA_image = ''
			CASA_RMS_image = ''

	## Runs the Madrigal methods; requires "madrigalWeb.py" and "globalDownload.py" and "madrigal.head"
	if tec_server == 'MAPGPS':
		print('\nCurrently, MAPGPS has been set to "False" \nand you must change tec_maps.py at line 306\n')
		CASA_image = ''
		CASA_RMS_image = ''

	if (tec_server == 'MAPGPS' and False): ## replace with: if tec_server == 'MAPGPS':
		mad_file_front = 'gps'+str(begin_day.split('/')[0])[2:]+str(begin_day.split('/')[1])+str(begin_day.split('/')[2])
		mad_data_file = ms_name[:-3]+'_MAPGPS_Data'

		mad_file = ''
		mad_file = check_existence(mad_data_file)
		if username!='' and user_email!='' and affiliation!='':
			if mad_file == '': 
				print('Retrieving the following MAPGPS files: '+begin_day+' to '+end_day)
				begin_mdy = str(begin_day.split('/')[1])+'/'+str(begin_day.split('/')[2])+'/'+str(begin_day.split('/')[0])
				end_mdy = str(end_day.split('/')[1])+'/'+str(end_day.split('/')[2])+'/'+str(end_day.split('/')[0])
				os.system('python globalDownload.py --url=http://madrigal.haystack.mit.edu/madrigal --outputDir='+workDir+\
					' --user_fullname="'+username+'" --user_email='+user_email+' --user_affiliation='+affiliation+\
					' --format=ascii --startDate='+str(begin_mdy)+' --endDate='+str(end_mdy)+' --inst=8000')

				non_day = qa.time(str(t_min[0]-86400.)+'s',form='ymd')[0][:10]
				non_file_prefix = 'gps'+str(non_day.split('/')[0])[2:]+str(non_day.split('/')[1])+str(non_day.split('/')[2])
				unwanted_file = check_existence(non_file_prefix)
				os.system('rm -rf '+unwanted_file+'.txt')

				files = glob.glob(r''+workDir+'*.txt')
				outfile = open(workDir+mad_data_file+'.txt','a')    
				for y in files:
					newfile = open(y,'r+')       
					data = newfile.read()
					newfile.close()
					outfile.write(data)
				outfile.close()


				## Making the CASA table is expensive, so we do it only once.
				print('Making a CASA table of: ', mad_data_file)
				make_CASA_table(mad_data_file)

			try:
				CASA_image = convert_MAPGPS_TEC(ms_name,mad_data_file,ref_time,ref_start,\
												ref_end,plot_vla_tec,im_name)
			except:
				print('An error was encountered retrieving/interpreting the MAPGPS files.')
				CASA_image = ''
				CASA_RMS_image = ''
		else:
			print('You need to supply your username, e-mail, and affiliation to access the Madrigal server.')
			CASA_image = ''
			CASA_RMS_image = ''
  
	## Returns the name of the TEC image generated
	print('The following TEC map was generated: '+CASA_image+' & '+CASA_RMS_image)
	if len(plot_name)>0:
		print('The following TEC zenith plot was generated: '+plot_name)
	else:
		plot_name='none'
	return CASA_image,CASA_RMS_image,plot_name





def get_IGS_TEC(ymd_date):
	"""
## =============================================================================
##
## Retrieves the IGS data and, specifically, the IGS Final Product: this is
## the combined TEC map from the four IAACs TEC maps.
##
## =============================================================================
##
## Inputs:
##    ymd_date     type = string    The 'yyyy/mm/dd' date of observation for 
##                                      which this will retrieve data
##
## Returns:
##    points_long  type = integer   Total number of points in longitude (deg) 
##                                      in the TEC map
##    points_lat   type = integer   Total number of points in latitude (deg)
##                                      in the TEC map
##    start_long   type = float     Initial value for the longitude (deg)
##    end_lat      type = float     Final value for the latitude (deg)
##    incr_long    type = float     Increment by which longitude increases
##                                      IGS data:       5 deg
##                                      MAPGPS data:    1 deg
##    incr_lat     type = float     Absolute value of the increment by which 
##                                      latitude increases
##                                      IGS data:       2.5 deg
##                                      MAPGPS data:    1 deg
##    incr_time    type = float     Increment by which time increases
##                                      IGS data:       120 min
##                                      MAPGPS data:    5 min
##    num_maps     type = integer   Number of maps (or time samples) of TEC
##    tec_array    type = array     4D array with axes consisting of 
##                                      [TEC_type,long.,lat.,time] that gives
##                                      the TEC/DTEC in TECU
##    tec_type     type = string    Specifies the origin of TEC data as a
##                                      CASA table keyword
##
## =============================================================================
	"""

	year = int(ymd_date.split('/')[0])
	month = int(ymd_date.split('/')[1])
	day = int(ymd_date.split('/')[2])

	## Gives the day of the year of any given year
	dayofyear = datetime.datetime.strptime(''+str(year)+' '+str(month)+' '+str(day)+'', '%Y %m %d').timetuple().tm_yday

	## Prepare the 3-digit day of the year for use to find the right IONEX file
	if dayofyear < 10:
		dayofyear = '00'+str(dayofyear)
	if dayofyear < 100 and dayofyear >= 10:
		dayofyear = '0'+str(dayofyear)

	## Outputing the name of the IONEX file you require.  
	igs_file = 'igsg'+str(dayofyear)+'0.'+str(list(str(year))[2])+''+str(list(str(year))[3])+'i'

	## =========================================================================
	##
	## This goes to the CDDIS website, and downloads and uncompresses the IGS 
	## file.  The preference is for the IGS Final product (IGSG), available
	## ~ 12-14 days after data is collected (i.e. data for September 1 should
	## be available by September 14).  If this file is not already in the
	## current working directory, it will retrieve it. If the file is 
	## unavailable, it will try to retrieve the IGS Rapid Product (IGRG),
	## released ~ 2-3 days after data is collected.  If this file is
	## unavailable, it will try to retrieve the JPL Rapid Product (JPRG), 
	## released ~ 1 day after data is collected. While the 'uncompress' command
	## is not necessary, it is the most straightforward on Linux.
	##
	## =========================================================================
	does_exist = ''
	does_exist = check_existence(igs_file)
	if does_exist == '':
		print('Retrieving the following file: ', igs_file)

		CDDIS = 'ftp://cddis.gsfc.nasa.gov/gnss/products/ionex'
		file_location = CDDIS+'/'+str(year)+'/'+str(dayofyear)+'/'

		workDir2 = workDir.replace(' ','\\ ')
		if does_exist == '':        
			get_file = file_location+igs_file+'.Z'
			retrieve = test_connection(get_file)
			if retrieve == True:
				os.system('curl -J '+get_file+' > '+workDir2+igs_file+'.Z')
				os.system('uncompress '+igs_file+'.Z')
				does_exist = check_existence(igs_file)
			else:
				print(igs_file, 'is unavailable')
				igs_file = igs_file.replace('igs','igr')

				does_exist = check_existence(igs_file)
		if does_exist == '':
			print('Retrieving the following file instead: ', igs_file)
			get_file = file_location+igs_file+'.Z'
			retrieve = test_connection(get_file)
			if retrieve == True:
				os.system('curl -J '+get_file+' > '+workDir2+igs_file+'.Z')
				os.system('uncompress '+igs_file+'.Z')
			else:
				print(igs_file, 'is unavailable')
				igs_file = igs_file.replace('igr','jpr')
				does_exist = check_existence(igs_file)
				if does_exist == '':
					print('Retrieving the following file instead: ', igs_file)
					get_file = file_location+igs_file+'.Z'
					retrieve = test_connection(get_file)
					if retrieve == True:
						os.system('curl -J '+get_file+' > '+workDir2+igs_file+'.Z')
						os.system('uncompress '+igs_file+'.Z')
					else:
						print(igs_file, 'is unavailable')
						print('\nNo data products available. You may try to manually'\
							  ' download the products at:\n'\
							  'ftp://cddis.gsfc.nasa.gov/gnss/products/ionex\n')
						return 0,0,0,0,0,0,0,0,[0],''
				else:
					pass
		else:
			pass 
	else:
		pass

	if igs_file.startswith('igs'):
		tec_type = 'IGS_Final_Product'
	elif igs_file.startswith('igr'):
		tec_type = 'IGS_Rapid_Product'
	elif igs_file.startswith('jpr'):
		tec_type = 'JPL_Rapid_Product'

	## =========================================================================
	##
	## The following section reads the lines of the ionex file for 1 day 
	## (13 maps total) into an array a[]. It also retrieves the thin-shell
	## ionosphere height used by IGS, the lat./long. spacing, etc. for use
	## later in this script.
	##
	## =========================================================================
	print('Transfering IONEX data format to a TEC/DTEC array for ',ymd_date)

	## Opening and reading the IONEX file into memory as a list
	linestring = open(igs_file, 'r').read()
	LongList = linestring.split('\n')

	## Create two lists without the header and only with the TEC and DTEC maps (based on code from ionFR.py)
	AddToList = 0 
	TECLongList = []
	DTECLongList = []
	for i in range(len(LongList)-1):
		## Once LongList[i] gets to the DTEC maps, append DTECLongList
		if LongList[i].split()[-1] == 'MAP':
			if LongList[i].split()[-2] == 'RMS':
				AddToList = 2
		if AddToList == 1:	
			TECLongList.append(LongList[i])
		if AddToList == 2:
			DTECLongList.append(LongList[i])
		## Determine the number of TEC/DTEC maps
		if LongList[i].split()[-1] == 'FILE':
			if LongList[i].split()[-3:-1] == ['MAPS','IN']:
				num_maps = float(LongList[i].split()[0])
		## Determine the shell ionosphere height (usually 450 km for IGS IONEX files)
		if LongList[i].split()[-1] == 'DHGT':
			ion_H = float(LongList[i].split()[0])
		## Determine the range in lat. and long. in the ionex file
		if LongList[i].split()[-1] == 'DLAT':
			start_lat = float(LongList[i].split()[0])
			end_lat = float(LongList[i].split()[1])
			incr_lat = float(LongList[i].split()[2])
		if LongList[i].split()[-1] == 'DLON':
			start_long = float(LongList[i].split()[0])
			end_long = float(LongList[i].split()[1])
			incr_long = float(LongList[i].split()[2])
		## Find the end of the header so TECLongList can be appended
		if LongList[i].split()[0] == 'END':
			if LongList[i].split()[2] == 'HEADER':
				AddToList = 1

	## Variables that indicate the number of points in Lat. and Lon.
	points_long = ((end_long - start_long)/incr_long) + 1
	points_lat = ((end_lat - start_lat)/incr_lat) + 1    ## Note that incr_lat is defined as '-' here
	number_of_rows = int(np.ceil(points_long/16))    ## Note there are 16 columns of data in IONEX format
	
	## 4-D array that will contain TEC & DTEC (a[0] and a[1], respectively) values
	a = np.zeros((2,int(points_long),int(points_lat),int(num_maps)))

	## Selecting only the TEC/DTEC values to store in the 4-D array.
	for Titer in range(2):
		counterMaps = 1
		UseList = []
		if Titer == 0:
			UseList = TECLongList
		elif Titer == 1:
			UseList = DTECLongList
		for i in range(len(UseList)):
			## Pointing to first map (out of 13 maps) then by changing 'counterMaps' the other maps are selected
			if UseList[i].split()[0] == ''+str(counterMaps)+'':
				if UseList[i].split()[-4] == 'START':
					## Pointing to the starting Latitude then by changing 'counterLat' we select TEC data
					## at other latitudes within the selected map
					counterLat = 0
					newstartLat = float(str(start_lat))
					for iLat in range(int(points_lat)):
						if UseList[i+2+counterLat].split()[0].split('-')[0] == ''+str(newstartLat)+'':
							## Adding to array a[] a line of Latitude TEC data
							counterLon = 0
							for row_iter in range(number_of_rows):
								for item in range(len(UseList[i+3+row_iter+counterLat].split())):
									a[Titer,counterLon,iLat,counterMaps-1] = UseList[i+3+row_iter+counterLat].split()[item]
									counterLon = counterLon + 1
						if '-'+UseList[i+2+counterLat].split()[0].split('-')[1] == ''+str(newstartLat)+'':
							## Adding to array a[] a line of Latitude TEC data. Same chunk as above but 
							## in this case we account for the TEC values at negative latitudes
							counterLon = 0
							for row_iter in range(number_of_rows):
								for item in range(len(UseList[i+3+row_iter+counterLat].split())):
									a[Titer,counterLon,iLat,counterMaps-1] = UseList[i+3+row_iter+counterLat].split()[item]
									counterLon = counterLon + 1
						counterLat = counterLat + row_iter + 2
						newstartLat = newstartLat + incr_lat
					counterMaps = counterMaps + 1

	## =========================================================================
	##
	## The section creates a new array that is a copy of a[], but with the lower
	## left-hand corner defined as the initial element (whereas a[] has the 
	## upper left-hand corner defined as the initial element).  This also
	## accounts for the fact that IONEX data is in 0.1*TECU.
	##
	## =========================================================================
	
	## The native sampling of the IGS maps minutes
	incr_time = 24*60/(int(num_maps)-1)    
	tec_array = np.zeros((2,int(points_long),int(points_lat),int(num_maps)))

	for Titer in range(2):
		incr = 0
		for ilat in range(int(points_lat)):
			tec_array[Titer,:,ilat,:] = 0.1*a[Titer,:,int(points_lat)-1-ilat,:]

	return points_long,points_lat,start_long,end_lat,incr_long,np.absolute(incr_lat),incr_time,num_maps,tec_array,tec_type





def check_existence(file_prefix):
	"""
## =============================================================================
##
## Checks to see if the IGS or MAPGPS file for a given day already exists and
## returns the file name prefix.  Primarily used to ensure we only call the data
## and make the CASA table once.
##
## =============================================================================
## 
## Inputs:
##    file_prefix   type = string   This is the prefix for the file name to
##                                      search for in the current directorty
##                                      IGS form:  'igsg'+'ddd'+'0.'+'yy'+'i'
##                                        ex:   August 6, 2011 is 'igsg2180.11i'
##                                      MAPGPS form:  'gps'+'yy'+'mm'+'dd'
##                                        ex:   August 6, 2011 is 'gps110806'
##
## Returns:
##	The name of the file it located.
##
## =============================================================================
	"""
	file_name = ''
	return_file = ''
	for file_name in [doc for doc in os.listdir(workDir)]:
		if (file_prefix.startswith('igs') and file_name.startswith('igs')):
			if file_name.startswith(file_prefix):
				return_file = file_prefix
		if (file_prefix.startswith('igr') and file_name.startswith('igr')):
			if file_name.startswith(file_prefix):
				return_file = file_prefix
		if (file_prefix.startswith('jpr') and file_name.startswith('jpr')):
			if file_name.startswith(file_prefix):
				return_file = file_prefix
		if (file_prefix.startswith('gps') and file_name.startswith('gps')):
			if (file_name.startswith(file_prefix) and file_name.endswith('.txt')):
				return_file = file_name[:-4]
		if (file_prefix.endswith('_MAPGPS_Data') and file_name.endswith('_MAPGPS_Data.tab')):
			if (file_name.startswith(file_prefix) and file_name.endswith('.tab')):
				return_file = file_prefix
	return return_file





def make_image(prefix,ref_long,ref_lat,ref_time,incr_long,incr_lat,incr_time,tec_array,tec_type,appendix=''):
	"""
## =============================================================================
##
## Creates a new image file with the TEC data and then returns the image name.  
## This also sets up the reference frame for use at the C++ level.
##
## =============================================================================
##
## Inputs:
##    prefix     type = string   Full file name for use in naming the image
##                                 IGS form:   'igsg'+'ddd'+'0.'+'yy'+'i'
##                                   ex:     August 6, 2011 is 'igsg2180.11i'
##                                 MAPGPS form:  'gps'+'yy'+'mm'+'dd'+'.###'
##                                   ex:     August 17, 2011 is 'gps110817g.001'
##    ref_long   type = float    Reference long. (deg) for setting coordinates
##    ref_lat    type = float    Reference lat. (deg) for setting coordinates
##    ref_time   type = float    Reference time (s) for setting coordinates, 
##                                   UT 0 on the first day
##    incr_long  type = float    Increment by which longitude increases
##                                   IGS data:       5 deg
##                                   MAPGPS data:    1 deg
##    incr_lat   type = float    Increment by which latitude increases
##                                   IGS data:       2.5 deg
##                                   MAPGPS data:    1 deg
##    incr_time  type = float    Increment by which time increases
##                                   IGS data:       120 min
##                                   MAPGPS data:    5 min
##    tec_array  type = array    3D array with axes consisting of 
##                                   [long.,lat.,time] giving the TEC in TECU
##    tec_type   type = string   Specifies the origin of TEC data as a
##                                   CASA table keyword
##    appendix   type = string   Appendix to add to the end of the image name
##
## Returns:
##    The name of the TEC map image
##
## =============================================================================
	"""
	print('Trying to make an image of', prefix+appendix+'.im')

	## Set the coordinate system for the TEC image
	cs0=cs.newcoordsys(linear=3)
	cs0.setnames(value='Long Lat Time')
	cs0.setunits(type='linear',value='deg deg s',overwrite=True)
	cs0.setreferencevalue([ref_long,ref_lat,ref_time])
	cs0.setincrement(type='linear',value=[incr_long,incr_lat,incr_time])

	## Make and view the TEC image
	imname=prefix+appendix+'.im'
	ia.fromarray(outfile=imname,pixels=tec_array,csys=cs0.torecord(),overwrite=True)
	ia.summary()
	## ia.statistics()
	ia.close()

	## Specify in the image where the TEC data came from
	tb.open(imname,nomodify=False)
	tb.putkeyword('TYPE',tec_type)
	tb.close()

	return imname




def ztec_value(my_long,my_lat,points_long,points_lat,ref_long,ref_lat,incr_long,incr_lat,incr_time,ref_start,ref_end,num_maps,tec_array,PLOT=False,PLOTNAME=''):
	"""
## =============================================================================
##
## Determine the TEC value for the coordinates given at every time sampling of
## the TEC. This locates the 4 points in the IONEX grid map which surround the
## coordinate for which you want to calculate the TEC value.
##
## =============================================================================
##
## Inputs:
##    my_long      type = float      Long. (deg) at which this interpolates TEC
##    my_lat       type = float      Lat. (deg) at which this interpolates TEC
##    points_long  type = integer    Total number of points in long. (deg)
##                                       in the TEC map
##    points_lat   type = integer    Total number of points in lat. (deg) 
##                                       in the TEC map
##    ref_long     type = float      Initial value for the longitude (deg)
##    ref_lat      type = float      Initial value for the latitude (deg)
##    incr_long    type = float      Increment by which longitude increases
##                                       IGS data:       5 deg
##                                       MAPGPS data:    1 deg
##    incr_lat     type = float      Increment by which latitude increases
##                                       IGS data:       2.5 deg
##                                       MAPGPS data:    1 deg
##    incr_time    type = float      Increment by which time increases
##                                       IGS data:       120 min
##                                       MAPGPS data:    5 min
##    ref_start    type = float      Beginning of observations (in seconds)
##    ref_end      type = float      End of observations (in seconds)
##    num_maps     type = integer    Number of maps (or time samples) of TEC
##    tec_array    type = array      3D array with axes consisting of 
##                                       [long.,lat.,time] giving TEC in TECU
##    PLOT         type = boolean    Determines whether to plot or return the
##                                       TEC time series of the local long./lat.
##
## Returns:
##    site_tec     type = array      2D array containing the TEC/DTEC values 
##                                       for the local long./lat.
##
## =============================================================================
	"""
	indexLat = 0
	indexLon = 0
	n = 0
	m = 0
	## Find the corners of the grid that surrounds the local long./lat.
	for lon in range(int(points_long)):
		if (my_long > (ref_long + (n+1)*incr_long)  and my_long <= (ref_long + (n+2)*incr_long)) :
			lowerIndexLon =  n + 1
			higherIndexLon = n + 2	
		n = n + 1
	for lat in range(int(points_lat)):
		if (my_lat > (ref_lat + (m+1)*incr_lat)  and my_lat <= (ref_lat + (m+2)*incr_lat)) :
			lowerIndexLat =  m + 1
			higherIndexLat = m + 2
		m = m + 1
	## Using the 4-point formula indicated in the IONEX manual, find the TEC value at the local coordinates
	diffLon = my_long - (ref_long + lowerIndexLon*incr_long)
	WLON = diffLon/incr_long
	diffLat = my_lat - (ref_lat + lowerIndexLat*incr_lat)
	WLAT = diffLat/incr_lat

	site_tec = np.zeros((2,num_maps))
	for Titer in range(2):
		for m in range(num_maps):			
			site_tec[Titer,m] = (1.0-WLAT)*(1.0-WLON)*tec_array[Titer,lowerIndexLon,lowerIndexLat,m] +\
								WLON*(1.0-WLAT)*tec_array[Titer,higherIndexLon,lowerIndexLat,m] +\
								(1.0-WLON)*WLAT*tec_array[Titer,lowerIndexLon,higherIndexLat,m] +\
								WLON*WLAT*tec_array[Titer,higherIndexLon,higherIndexLat,m]

	if PLOT == True:
		## Set axis label size for the plots
		rc('xtick', labelsize=15)
		rc('ytick', labelsize=15)
		plottimes = [x*incr_time for x in range(num_maps)]
		plt.interactive(False)
		plt.errorbar(plottimes,site_tec[0],site_tec[1])
		plt.axvspan(ref_start/60.0, ref_end/60.0, facecolor='r', alpha=0.5)
		plt.xlabel(r'$\mathrm{Time}$ $\mathrm{(minutes)}$', fontsize=20)
		plt.ylabel(r'$\mathrm{TEC}$ $\mathrm{(TECU)}$', fontsize=20)
		plt.title(r'$\mathrm{TEC}$ $\mathrm{values}$ $\mathrm{for}$ $\mathrm{Long.}$ $\mathrm{=}$ '+\
					'$\mathrm{'+str(my_long)+'}$ / $\mathrm{Lat.}$ $\mathrm{=}$ $\mathrm{'+str(my_lat)+'}$',\
					fontsize=20)
		plt.axis([min(plottimes),max(plottimes),0,1.1*max(site_tec[0])])

		if len(PLOTNAME)>0:
			plt.savefig( PLOTNAME )

	if PLOT == False:
		return site_tec





def test_connection(reference):
	"""
## =============================================================================
##
## Determines whether the machine is connected to the internet or not.  Also
## used to determine whether a given IONEX file exists.
##
## =============================================================================
##
## Inputs:
##    reference    type = string     website/online file to attempt to access
##
## Returns:
##    True if the website/online file is accessible and False if not
##
## =============================================================================
	"""
	try:
		response = urllib2.urlopen(reference,timeout=5)
		return True
	except urllib2.URLError as err: 
		return False





def convert_MAPGPS_TEC(ms_name,mad_data_file,ref_time,ref_start,ref_end,plot_vla_tec,im_name):
	"""
## =============================================================================
##
## This opens the MAPGPS Data table and selects a subset of TEC/DTEC values
## within a 15 deg square of the VLA. This then plots the zenith TEC/DTEC at the
## VLA site and makes the TEC map for use at the C++ level. We chose to deal
## with the MAPGPS data in this separate fashion because there are large
## 'gaps' in the data where no TEC/DTEC values exist.  Consequently, we use the
## filled in CASA table to produce a TEC map and can not simply
## concatenate arrays.
##
## =============================================================================
##
## Inputs:
##    ms_name         type = string    Name of the measurement set for which to
##                                         acquire TEC/DTEC data
##    mad_data_file   type = string    Name of the MAPGPS TEC/DTEC data table
##    ref_time        type = float     Reference time (s) for setting the 
##                                         coordinates, UT 0 on the first day
##    plot_vla_tec    type = boolean   When True, this will open a plot of the 
##                                         interpolated TEC/DTEC at the VLA.
##    im_name       type = string    Name of the output TEC Map optionally
##                                       specified by the user
##
## Returns:
##    Opens a plot showing the zenith TEC/DTEC at the VLA (if plot_vla_tec=True)
##    and the name of the CASA image file containing the TEC map.
##
## =============================================================================
	"""
	## Only retrieve data in a 15x15 deg. patch centered (more or less) at the VLA
	tb.open(mad_data_file+'.tab')
	st0=tb.query('GDLAT>19 && GDLAT<49 && GLON>-122 && GLON<-92',
	## If you want ALL the data to make a global map, use the line below:
	#st0=tb.query('GDLAT>-90. && GDLAT<90. && GLON>-180. && GLON<180',
				name='tecwindow')

	utimes=np.unique(st0.getcol('UT1_UNIX'))
	ulat=np.unique(st0.getcol('GDLAT'))
	ulong=np.unique(st0.getcol('GLON'))

	points_lat=len(ulat)
	points_long=len(ulong)
	num_maps=len(utimes)

	## Initialize the array which will be used to make the image
	tec_array=np.zeros((2,points_long,points_lat,num_maps),dtype=float)

	minlat=min(ulat)
	minlong=min(ulong)

	print('rows',len(utimes))

	itime=0
	for t in utimes:
		st1=st0.query('UT1_UNIX=='+str(t),name='bytime')
		n=st1.nrows()
		if itime%100==0:
			print(itime, n)
		ilong=st1.getcol('GLON')-minlong
		ilat=st1.getcol('GDLAT')-minlat
		itec=st1.getcol('TEC')
		idtec=st1.getcol('DTEC')
		for i in range(n):
			tec_array[0,int(ilong[i]),int(ilat[i]),itime]=itec[i]
			tec_array[1,int(ilong[i]),int(ilat[i]),itime]=idtec[i]
		st1.close()

		## Simply interpolate to cull as many zeros as possible
		## (median of good neighbors, if at least four of them)
		thistec_array=tec_array[:,:,:,itime].copy()
		thisgood=thistec_array[0]>0.0
		for i in range(1,points_long-1):
			for j in range(1,points_lat-1):
				if not thisgood[i,j]:
					mask=thisgood[(i-1):(i+2),(j-1):(j+2)]
					if np.sum(mask)>4:
						#print itime, i,j, pylab.sum(mask)
						tec_array[0,i,j,itime]=np.median(thistec_array[0,(i-1):(i+2),(j-1):(j+2)][mask])
						tec_array[1,i,j,itime]=np.median(thistec_array[1,(i-1):(i+2),(j-1):(j+2)][mask])
		itime+=1

	st0.close()
	tb.close()

	ztec_value(-107.6184,34.0790,points_long,points_lat,minlong,minlat,1,\
				1,5,ref_start,ref_end,int(num_maps),tec_array,plot_vla_tec)
	## ref_time + 150 accounts for the fact that the MAPGPS map starts at 00:02:30 UT, not 00:00:00 UT
	if im_name == '':
		prefix = ms_name
	else:
		prefix = im_name
	CASA_image = make_image(prefix,minlong,minlat,ref_time+150.0,1,1,5*60,tec_array[0],'MAPGPS',appendix = '.MAPGPS_TEC')

	return CASA_image





def make_CASA_table(file_name):
	"""
## =============================================================================
##
## Makes a CASA table for the MAPGPS file for a given day.
## It requires the 'madrigal.head' file be in the working directory.
##
## =============================================================================
## 
## Inputs:
##    file_name    type = string    This is the full MAPGPS file name
##                                    MAPGPS form: 'gps'+'yy'+'mm'+'dd'+'.###'
##                                    ex:   August 17, 2011 is 'gps110817g.001'
##
## =============================================================================
	"""
	os.system('rm -rf '+file_name+'.tab')
	tb.fromascii(tablename=file_name+'.tab',asciifile=file_name+'.txt',headerfile='madrigal.head',sep=" ",
				commentmarker='^YEAR      MONT')

	# this will work when tb.fromascii is fixed...
	#   (making the headerfile unnecessary)
	#tb.fromascii('madtest.tab','madtest.txt',sep=" ",
	#             columnnames=['YEAR','MONTH','DAY','HOUR','MIN','SEC',
	#                          'UT1_UNIX','UT2_UNIX','RECNO',
	#                          'GDLAT','GLON','TEC','DTEC'],
	#             datatypes=['I','I','I','I','I','I','I','I','I','R','R','R','R'],
	#             autoheader=F,commentmarker='^YEAR      MONT')
