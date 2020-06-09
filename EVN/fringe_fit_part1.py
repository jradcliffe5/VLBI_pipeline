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

def fill_flagged_soln(caltable='', fringecal=False):
		"""
		This is to replace the gaincal solution of flagged/failed solutions by the nearest valid 
		one.
		If you do not do that and applycal blindly with the table your data gets 
		flagged between  calibration runs that have a bad/flagged solution at one edge.
		Can be pretty bad when you calibrate every hour or more 
		(when you are betting on self-cal) of observation (e.g L-band of the EVLA)..one can 
		lose the whole hour of good data without realizing !
		"""
		if fringecal==False:
			gaincol='CPARAM'
		else:
			gaincol='FPARAM'
		tb.open(caltable, nomodify=False)
		flg=tb.getcol('FLAG')
		#sol=tb.getcol('SOLUTION_OK')
		ant=tb.getcol('ANTENNA1')
		gain=tb.getcol(gaincol)
		t=tb.getcol('TIME')
		dd=tb.getcol('SPECTRAL_WINDOW_ID')
		#dd=tb.getcol('CAL_DESC_ID')
		maxant=np.max(ant)
		maxdd=np.max(dd)
		npol=len(gain[:,0,0])
		nchan=len(gain[0,:,0])
		
		k=1
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
		 
		###
		tb.putcol('FLAG', flg)
		#tb.putcol('SOLUTION_OK', sol)
		tb.putcol(gaincol, gain)
		tb.done()

selectant = ''
selectspw = ''
sbdsolint='1min'

refant = find_refants(['EF','T6','O8','SR','WB','JB','UR','TR','SV'],mmsfile)

flagmanager(vis=mmsfile,mode='save',versionname='flag_1')
edgechan='0~2;29~31'
flagdata(vis=mmsfile,
			mode='manual',
			spw='0:0~2;29~31, 1:0~2;29~31, 2:0~2;29~31, 3:0~2;29~31, 4:0~2;29~31, 5:0~2;29~31, 6:0~2;29~31, 7:0~2;29~31')
flagdata(vis=mmsfile, mode='manual',autocorr=True)

os.system('rm -r %s/%s.sbd'%(cwd,epoch))
fringefit(vis=mmsfile,
				caltable='%s/%s.sbd'%(cwd,epoch),
				field=sbdcal,
				solint=sbdsolint,
				antenna=selectant,
				spw=selectspw,
				zerorates=True,
				refant=refant,
				minsnr=5,
				gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch)],
				interp=['linear,linear','linear'],
				parang=True)


bandpass(vis=mmsfile,
			caltable='%s/%s.bpass'%(cwd,epoch),
			field=sbdcal,
			gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch)],
			interp=['linear','linear,linear','linear'],
			solnorm=False,
			antenna=selectant,
			spw=selectspw,
			fillgaps=4,
			solint='inf',
			combine='scan',
			refant=refant,
			bandtype='B',
			spwmap=[[],[],[],[]],
			parang=True)

fill_flagged_soln(caltable='%s/%s.sbd'%(cwd,epoch), fringecal=True)
fill_flagged_soln(caltable='%s/%s.bpass'%(cwd,epoch), fringecal=False)


flagmanager(vis=mmsfile,mode='save',versionname='preapply_1')
applycal(vis=mmsfile,
			gaintable=['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch),\
						  '%s/%s.bpass'%(cwd,epoch)],
			interp=['linear','linear,linear','linear','linear,linear'],
			antenna=selectant,
			spw=selectspw,
			spwmap=[[],[],[],[]],
			applymode='',
			parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='flag_2')

tables = [['%s/%s.tsys'%(cwd,epoch),'%s/%s.gcal'%(cwd,epoch),'%s/%s.sbd'%(cwd,epoch),\
						  '%s/%s.bpass'%(cwd,epoch)],['linear','linear,linear','linear','linear,linear'],[[],[],[],[]]]
with open('%s_calibtables.txt'%epoch, 'w') as filehandle:
	 json.dump(tables, filehandle)
