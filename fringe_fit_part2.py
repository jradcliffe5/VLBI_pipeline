import sys, os
epoch =sys.argv[sys.argv.index(sys.argv[2])+1]
phasecal=sys.argv[sys.argv.index(sys.argv[2])+2]
sbdcal=sys.argv[sys.argv.index(sys.argv[2])+3]
casa_tclean=sys.argv[sys.argv.index(sys.argv[2])+4]
loop=sys.argv[sys.argv.index(sys.argv[2])+5]

inbase='%s/VLBA'%epoch
mmsfile = '%s/VLBA_%s.ms'%(epoch,epoch)

def find_refants(pref_ant,vis):
   tb.open('%s/ANTENNA'%vis)
   antennas = tb.getcol('NAME')
   tb.close()
   refant=[]
   for i in pref_ant:
      if i in antennas:
         refant.append(i)
   return ",".join(refant)

refant = find_refants(['PT','BR','HN','FD','KP','MK','NL','OV','SC'],mmsfile)

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

gaintables = ['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,'%s.bpass'%inbase]
interp = ['linearperobs,linear','linearperobs','linearperobs','linearperobs','linearperobs,linear']
spwmap = [[],[],[],[],[]]
for i in range(int(loop)-1):
	gaintables.append('%s.mbd%s'%(inbase,i+1))
	interp.append('linearperobs')
	spwmap.append(8*[0])

os.system('rm -r %s.mbd%s'%(inbase,loop))
fringefit(vis=mmsfile,
					field=phasecal+','+sbdcal,
					caltable='%s.mbd%s'%(inbase,loop),
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


fill_flagged_soln('%s.mbd%s'%(inbase,loop))

gaintables.append('%s.mbd%s'%(inbase,loop))
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
	os.system('rm -r %s_pcal_loop_%s'%(inbase,loop))
	tclean(vis=mmsfile,
					 field=phasecal,
					 imagename='%s_rms_%s'%(inbase,loop),
					 cell=['0.0005arcsec'],
					 imsize=[640,640],
					 deconvolver='mtmfs',
					 phasecenter='J2000 12h34m11.743000s +61d58m34.0s',
					 niter=1,
					 parallel=False,
					 usemask='user',
					 savemodel='none')
	rms = imstat(imagename='%s_rms_%s.image.tt0'%(inbase,loop),box='20,20,620,620')['rms'][0]
	tclean(vis=mmsfile,
					 field=phasecal,
					 imagename='%s_pcal_loop_%s'%(inbase,loop),
					 cell=['0.0005arcsec'],
					 imsize=[640,640],
					 deconvolver='mtmfs',
					 niter=1000,
					 threshold=rms,
					 parallel=False,
					 usemask='user',
					 mask='FF.mask',
					 savemodel='modelcolumn')