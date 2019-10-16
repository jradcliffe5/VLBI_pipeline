import sys
from casa import gaincal, applycal,tclean, imstat
vis = sys.argv[sys.argv.index(sys.argv[2])+1]
type = sys.argv[sys.argv.index(sys.argv[2])+2]
field = sys.argv[sys.argv.index(sys.argv[2])+3]
solint = sys.argv[sys.argv.index(sys.argv[2])+4]
gaintable=sys.argv[sys.argv.index(sys.argv[2])+5]
combine=sys.argv[sys.argv.index(sys.argv[2])+6]
applytype=sys.argv[sys.argv.index(sys.argv[2])+7]
epoch=sys.argv[sys.argv.index(sys.argv[2])+8]

caltype=type.split(',')
solint=solint.split(',')
combine=combine.split(',')
gaintable=gaintable.split(',')

def find_refants(pref_ant,vis):
   tb.open('%s/ANTENNA'%vis)
   antennas = tb.getcol('NAME')
   tb.close()
   refant=[]
   for i in pref_ant:
      if i in antennas:
         refant.append(i)
   return ",".join(refant)

refant = find_refants(['PT','BR','HN','FD','KP','MK','NL','OV','SC'],vis)

#print(gaintable)
#sys.exit()
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

for i in range(len(caltype)):
	if caltype[i] == 'K':
		gaintype='K'
		calmode='ap'
		minblperant=3
		solnorm=False
	elif caltype[i] == 'p':
		gaintype='G'
		calmode='p'
		minblperant=3
		solnorm=False
	elif caltype[i] == 'ap':
		gaintype='G'
		calmode='ap'
		minblperant=4
		solnorm=True
	else:
		sys.exit()

	if combine[i] == 'spw':
		combine_add = 'combine'
	else:
		combine_add = ''


	spwmap=[]
	interp=[]
	for j in gaintable: 
		if ('.mbd' in j) or ('combine' in j): 
			spwmap.append(8*[0])
			interp.append('linearperobs')
		else: 
			spwmap.append([])
			interp.append('linearperobs')
	os.system('rm -r %s/%s_%s%s.%s'%(epoch,field,str(int(i)+1),combine_add,caltype[i]))
	gaincal(vis=vis,
		    caltable='%s/%s_%s%s.%s'%(epoch,field,str(int(i)+1),combine_add,caltype[i]),
		    field=field,
		    solint=solint,
		    refant=refant,
		    minblperant=minblperant,
		    solnorm=solnorm,
		    combine=combine[i],
		    gaintype=gaintype,
		    calmode=calmode,
		    gaintable=gaintable,
		    spwmap=spwmap,
			interp=interp,
		    parang=True)

	fill_flagged_soln_gain(caltable='%s/%s_%s%s.%s'%(epoch,field,str(int(i)+1),combine_add,caltype[i]), doplot=False)

	gaintable.append('%s/%s_%s%s.%s'%(epoch,field,str(int(i)+1),combine_add,caltype[i]))

	if combine_add == 'combine': 
		spwmap.append(8*[0])
		interp.append('linearperobs')
	else:
		spwmap.append([])
		interp.append('linearperobs')

	applycal(vis=vis,
		     gaintable=gaintable,
		     spwmap=spwmap,
		     applymode=applytype,
			 interp=interp,
		     parang=True)

	os.system('rm -r %s/pcal_rms_%s'%(epoch,i+1))
	tclean(vis=vis,
			 field=field,
			 imagename='%s/pcal_rms_%s'%(epoch,i+1),
			 cell=['0.0005arcsec'],
			 imsize=[640,640],
			 deconvolver='mtmfs',
			 phasecenter='J2000 12h34m11.743000s +61d58m34s',
			 niter=1,
			 parallel=False,
			 usemask='user',
			 savemodel='none')
	rms = imstat(imagename='%s/pcal_rms_%s.image.tt0'%(epoch,i+1),box='20,20,620,620')['rms'][0]
	tclean(vis=vis,
			 field=field,
			 imagename='%s/pcal_sc_%s'%(epoch,i+1),
			 cell=['0.0005arcsec'],
			 imsize=[640,640],
			 deconvolver='mtmfs',
			 niter=1000,
			 threshold=rms,
			 parallel=False,
			 usemask='user',
			 mask='FF.mask',
			 savemodel='modelcolumn')
