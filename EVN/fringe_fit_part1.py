import sys, os
import json
epoch =sys.argv[sys.argv.index(sys.argv[2])+1]
cwd=sys.argv[sys.argv.index(sys.argv[2])+2]
phasecal=sys.argv[sys.argv.index(sys.argv[2])+3]
sbdcal=sys.argv[sys.argv.index(sys.argv[2])+4]

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


refant = find_refants(['EF','T6','O8','SR','WB','JB','UR','TR','SV'],mmsfile)

flagmanager(vis=mmsfile,mode='save',versionname='flag_1')
flagdata(vis=mmsfile,
			mode='manual',
			spw='0:0~2;30~32, 1:0~2;30~32, 2:0~2;30~32, 3:0~2;30~32, 4:0~2;30~32, 5:0~2;30~32, 6:0~2;30~32,7:0~2;30~32')
flagdata(vis=mmsfile, mode='manual',autocorr=True)

os.system('rm -r %s/%s.sbd'%(cwd,epoch))
fringefit(vis=mmsfile,
				caltable='%s/%s.sbd'%(cwd,epoch),
				field=sbdcal,
				solint='inf',
				zerorates=True,
				refant=refant,
				minsnr=5,
				gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch)],
				interp=['linear,linear','linear'],
				parang=True)
fill_flagged_soln(caltable='%s/%s.sbd'%(cwd,epoch), doplot=False)

bandpass(vis=mmsfile,
			caltable='%s/%s.bpass'%(cwd,epoch),
			field=sbdcal,
			gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch)],
			interp=['linear','linear,linear','nearest'],
			solnorm=True,
			fillgaps=4,
			solint='inf',
			combine='scan',
			refant=refant,
			bandtype='B',
			spwmap=[[],[],[],[]],
			parang=True)
fill_flagged_soln_gain(caltable='%s/%s.bpass'%(cwd,epoch), doplot=False)


flagmanager(vis=mmsfile,mode='save',versionname='preapply_1')
applycal(vis=mmsfile,
			gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch),\
						  '%s/%s.bpass'%(cwd,epoch)],
			interp=['linear','linear,linear','nearest','linear,linear'],
			spwmap=[[],[],[],[]],
			applymode='',
			parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='flag_2')

tables = [['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch),\
						  '%s/%s.bpass'%(cwd,epoch)],['linear','linear,linear','nearest','linear,linear'],[[],[],[],[]]]
with open('%s_calibtables.txt'%epoch, 'w') as filehandle:
	 json.dump(tables, filehandle)
