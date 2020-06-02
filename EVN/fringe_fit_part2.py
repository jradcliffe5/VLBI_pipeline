import sys, os
import numpy as np
import json

print(sys.argv)
epoch =sys.argv[sys.argv.index(sys.argv[2])+1]
cwd=sys.argv[sys.argv.index(sys.argv[2])+2]
phasecal=str(sys.argv[sys.argv.index(sys.argv[2])+3])
sbdcal=sys.argv[sys.argv.index(sys.argv[2])+4]
casa_tclean=sys.argv[sys.argv.index(sys.argv[2])+5]
loop=int(sys.argv[sys.argv.index(sys.argv[2])+6])
pcal_no=int(sys.argv[sys.argv.index(sys.argv[2])+7])
try:
	pad_ants=sys.argv[sys.argv.index(sys.argv[2])+8]
except:
	pad_ants = -1


if pad_ants.find(",") > 0:
   pad_ants = np.array(pad_ants.split(",")).astype(int)
else:
   pad_ants = np.array([pad_ants]).astype(int)

if phasecal.find(",") > 0:
   phasecal = phasecal.split(",")[pcal_no-1]
else:
   phasecal = phasecal

inbase='%s/%s'%(cwd,epoch)
mmsfile = '%s/%s.ms'%(cwd,epoch)

def find_refants(pref_ant,vis):
   tb.open('%s/ANTENNA'%vis)
   antennas = tb.getcol('NAME')
   tb.close()
   refant=[]
   for i in pref_ant:
	  if i in antennas:
		 refant.append(i)
   return ",".join(refant)

refant = find_refants(['EF','T6','O8','SR','WB','JB','UR','TR','SV'],mmsfile)


def pad_antennas(caltable='',ants=[],gain=False):
	tb.open('%s'%caltable,nomodify=False)
	flg=tb.getcol('FLAG')
	#sol=tb.getcol('SOLUTION_OK')
	ant=tb.getcol('ANTENNA1')
	if gain == True:
		g_col = 'CPARAM'
		gain=tb.getcol(g_col)
		repl_val = 1+0j
	else:
		g_col = 'FPARAM'
		gain=tb.getcol(g_col)
		repl_val = 0

	for i in ants:
		flg[:,:,(ant==i)] = 0
		print(gain[:,:,(ant==i)])
		gain[:,:,(ant==i)] = repl_val

	tb.putcol('FLAG', flg)
	tb.putcol(g_col, gain)

	tb.close()

def fill_flagged_soln(caltable='', doplot=False):
		"""
		This is to replace the gaincal solution of flagged/failed solutions by the nearest valid 
		one.
		If you do not do that and applycal blindly with the table your data gets 
		flagged between  calibration runs that have a bad/flagged solution at one edge.
		Can be pretty bad when you calibrate every hour or more 
		(when you are betting on self-cal) of observation (e.g L-band of the EVLA)..one can 
		lose the whole hour of good data without realizing !
		"""
		tb.open(caltable, nomodify=False)
		flg=tb.getcol('FLAG')
		#sol=tb.getcol('SOLUTION_OK')
		ant=tb.getcol('ANTENNA1')
		gain=tb.getcol('FPARAM')
		t=tb.getcol('TIME')
		dd=tb.getcol('SPECTRAL_WINDOW_ID')
		#dd=tb.getcol('CAL_DESC_ID')
		maxant=np.max(ant)
		maxdd=np.max(dd)
		npol=len(gain[:,0,0])
		nchan=len(gain[0,:,0])
		
		k=1
		if(doplot):
				pl.ion()
				pl.figure(1)
				pl.plot(t[(ant==k)], sol[0,0,(ant==k)], 'b+')
				pl.plot(t[(ant==k)], flg[0,0,(ant==k)], 'r+')
				pl.twinx()
				pl.plot(t[(ant==k)], abs(gain[0,0,(ant==k)]), 'go')
		print 'maxant', maxant
		numflag=0.0
		for k in range(maxant+1):
				for j in range (maxdd+1):
						subflg=flg[:,:,(ant==k) & (dd==j)]
						subt=t[(ant==k) & (dd==j)]
						#subsol=sol[:,:,(ant==k) & (dd==j)]
						subgain=gain[:,:,(ant==k) & (dd==j)]
						#print 'subgain', subgain.shape
						for kk in range(1, len(subt)):
								for chan in range(nchan):
										for pol in range(npol):
												if(subflg[pol,chan,kk] and not subflg[pol,chan,kk-1]):
														numflag += 1.0
														subflg[pol,chan,kk]=False
														#subsol[pol, chan, kk]=True
														subgain[pol,chan,kk]=subgain[pol,chan,kk-1]
												if(subflg[pol,chan,kk-1] and not subflg[pol,chan,kk]):
														numflag += 1.0
														subflg[pol,chan,kk-1]=False
														#subsol[pol, chan, kk-1]=True
														subgain[pol,chan,kk-1]=subgain[pol,chan,kk]
						flg[:,:,(ant==k) & (dd==j)]=subflg
						#sol[:,:,(ant==k) & (dd==j)]=subsol
						gain[:,:,(ant==k) & (dd==j)]=subgain


		print 'numflag', numflag
		if(doplot):
				pl.figure(2)
				k=1
				#pl.clf()
				pl.plot(t[(ant==k)], sol[0,0,(ant==k)], 'b+')
				pl.plot(t[(ant==k)], flg[0,0,(ant==k)], 'r+')
				pl.twinx()
				pl.plot(t[(ant==k)], abs(gain[0,0,(ant==k)]), 'go')
				pl.title('antenna='+str(k))
		 
		###
		tb.putcol('FLAG', flg)
		#tb.putcol('SOLUTION_OK', sol)
		tb.putcol('FPARAM', gain)
		tb.done()

def fill_flagged_soln_gain(caltable='', doplot=False):
		"""
		This is to replace the gaincal solution of flagged/failed solutions by the nearest valid 
		one.
		If you do not do that and applycal blindly with the table your data gets 
		flagged between  calibration runs that have a bad/flagged solution at one edge.
		Can be pretty bad when you calibrate every hour or more 
		(when you are betting on self-cal) of observation (e.g L-band of the EVLA)..one can 
		lose the whole hour of good data without realizing !
		"""
		tb.open(caltable, nomodify=False)
		flg=tb.getcol('FLAG')
		#sol=tb.getcol('SOLUTION_OK')
		ant=tb.getcol('ANTENNA1')
		gain=tb.getcol('CPARAM')
		t=tb.getcol('TIME')
		dd=tb.getcol('SPECTRAL_WINDOW_ID')
		#dd=tb.getcol('CAL_DESC_ID')
		maxant=np.max(ant)
		maxdd=np.max(dd)
		npol=len(gain[:,0,0])
		nchan=len(gain[0,:,0])
		
		k=1
		if(doplot):
				pl.ion()
				pl.figure(1)
				pl.plot(t[(ant==k)], sol[0,0,(ant==k)], 'b+')
				pl.plot(t[(ant==k)], flg[0,0,(ant==k)], 'r+')
				pl.twinx()
				pl.plot(t[(ant==k)], abs(gain[0,0,(ant==k)]), 'go')
		print 'maxant', maxant
		numflag=0.0
		for k in range(maxant+1):
				for j in range (maxdd+1):
						subflg=flg[:,:,(ant==k) & (dd==j)]
						subt=t[(ant==k) & (dd==j)]
						#subsol=sol[:,:,(ant==k) & (dd==j)]
						subgain=gain[:,:,(ant==k) & (dd==j)]
						#print 'subgain', subgain.shape
						for kk in range(1, len(subt)):
								for chan in range(nchan):
										for pol in range(npol):
												if(subflg[pol,chan,kk] and not subflg[pol,chan,kk-1]):
														numflag += 1.0
														subflg[pol,chan,kk]=False
														#subsol[pol, chan, kk]=True
														subgain[pol,chan,kk]=subgain[pol,chan,kk-1]
												if(subflg[pol,chan,kk-1] and not subflg[pol,chan,kk]):
														numflag += 1.0
														subflg[pol,chan,kk-1]=False
														#subsol[pol, chan, kk-1]=True
														subgain[pol,chan,kk-1]=subgain[pol,chan,kk]
						flg[:,:,(ant==k) & (dd==j)]=subflg
						#sol[:,:,(ant==k) & (dd==j)]=subsol
						gain[:,:,(ant==k) & (dd==j)]=subgain


		print 'numflag', numflag
		if(doplot):
				pl.figure(2)
				k=1
				#pl.clf()
				pl.plot(t[(ant==k)], sol[0,0,(ant==k)], 'b+')
				pl.plot(t[(ant==k)], flg[0,0,(ant==k)], 'r+')
				pl.twinx()
				pl.plot(t[(ant==k)], abs(gain[0,0,(ant==k)]), 'go')
				pl.title('antenna='+str(k))
		 
		###
		tb.putcol('FLAG', flg)
		#tb.putcol('SOLUTION_OK', sol)
		tb.putcol('CPARAM', gain)
		tb.done()

def json_load_byteified(file_handle):
	return _byteify(
		json.load(file_handle, object_hook=_byteify),
		ignore_dicts=True
	)

def json_loads_byteified(json_text):
	return _byteify(
		json.loads(json_text, object_hook=_byteify),
		ignore_dicts=True
	)

def _byteify(data, ignore_dicts = False):
	# if this is a unicode string, return its string representation
	if isinstance(data, unicode):
		return data.encode('utf-8')
	# if this is a list of values, return list of byteified values
	if isinstance(data, list):
		return [ _byteify(item, ignore_dicts=True) for item in data ]
	# if this is a dictionary, return dictionary of byteified keys and values
	# but only if we haven't already byteified it
	if isinstance(data, dict) and not ignore_dicts:
		return {
			_byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
			for key, value in data.iteritems()
		}
	# if it's anything else, return it in its original form
	return data
#gaintables = ['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.sbd'%inbase,'%s.bpass'%inbase]
#interp = ['linear,linear','linear','nearest','linear,linear']
#spwmap = [[],[],[],[]]
#for i in range(int(loop)-1):
#	gaintables.append('%s.mbd%s'%(inbase,i+1))
#	interp.append('linear')
#	spwmap.append(8*[0])


# open output file for reading
with open('%s_calibtables.txt'%inbase, 'r') as filehandle:
	tables = json_load_byteified(filehandle)

gaintables = tables[0]
interp = tables[1]
spwmap = tables[2]

os.system('rm -r %s_pc%s.mbd%s'%(inbase,pcal_no,loop))
fringefit(vis=mmsfile,
	  field=phasecal,
	  caltable='%s_pc%s.mbd%s'%(inbase,pcal_no,loop),
	  combine='spw',
	  solint='inf',
	  zerorates=False,
	  refant=refant,
	  delaywindow=[-50,50],
	  ratewindow=[-3,3],
	  minsnr=2.,
	  gaintable=gaintables,
	  interp=interp,
	  spwmap=spwmap,
	  parang=True)


fill_flagged_soln('%s_pc%s.mbd%s'%(inbase,pcal_no,loop))
if pad_ants != -1:
	pad_antennas(caltable='%s_pc%s.mbd%s'%(inbase,pcal_no,loop),ants=pad_ants,gain=False)

gaintables.append('%s_pc%s.mbd%s'%(inbase,pcal_no,loop))
interp.append('linear')
spwmap.append(8*[0])

#flagmanager(vis=mmsfile,mode='save',versionname='preapply_2')


applycal(vis=mmsfile,
	 gaintable=gaintables,
	 interp=interp,
	 spwmap=spwmap,
	 applymode='',
	 parang=True)

if casa_tclean == 'True':
	tb.open(mmsfile+'/FIELD')
	phase_centre = tb.getcol('PHASE_DIR').T[tb.getcol('NAME')==phasecal].squeeze()
	phase_centre_offset = 1 #arcsec
	phase_centre = 'J2000 %srad %srad'%(phase_centre[0],phase_centre[1]+((phase_centre_offset/3600.)*(np.pi/180.)))
	tb.close()
	os.system('rm -r %s_pc%s_rms_%s*'%(inbase,pcal_no,loop))
	os.system('rm -r %s_pc%s_pcal_loop_%s*'%(inbase,pcal_no,loop))
	tclean(vis=mmsfile,
		   field=phasecal,	
		   imagename='%s_pc%s_rms_%s'%(inbase,pcal_no,loop),
		   cell=['0.0005arcsec'],
		   imsize=[640,640],
		   deconvolver='mtmfs',
		   phasecenter=phase_centre,
		   niter=1,
		   parallel=False,
		   usemask='user',
		   savemodel='none')
	rms = imstat(imagename='%s_pc%s_rms_%s.image.tt0'%(inbase,pcal_no,loop),box='20,20,620,620')['rms'][0]
	tclean(vis=mmsfile,
		   field=phasecal,
		   imagename='%s_pc%s_pcal_loop_%s'%(inbase,pcal_no,loop),
		   cell=['0.0005arcsec'],
		   imsize=[640,640],
		   deconvolver='mtmfs',
		   niter=1000,
		   threshold=rms,
		   parallel=False,
		   usemask='user',
		   mask='circle[[320pix, 320pix], 10pix]',
		   savemodel='modelcolumn')

tables = [gaintables,interp,spwmap]
with open('%s_calibtables.txt'%inbase, 'w') as filehandle:
	json.dump(tables, filehandle)

