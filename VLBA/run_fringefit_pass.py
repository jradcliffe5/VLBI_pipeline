epoch='a1'
inbase = 'VLBA'
mmsfile='VLBA_%s.ms'%(epoch)
phasecal = 'J1234+619'
sbdcal='J0927+390'

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
'''
flagmanager(vis=mmsfile,mode='save',versionname='flag_1')
flagdata(vis=mmsfile,
         mode='manual',
         spw='0:0~5;122~127, 1:0~5;122~127, 2:0~5;122~127, 3:0~5;122~127, 4:0~5;122~127, 5:0~5;122~127, 6:0~5;122~127,7:0~5;122~127')

## Instrumental delays
os.system('rm -r %s.sbd'%inbase)
fringefit(vis=mmsfile,
            caltable='%s.sbd'%inbase,
            field=sbdcal,
            solint='inf',
            zerorates=True,
            refant='PT,BR,HN,FD',
            minsnr=5,
            gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase],
            interp=['linear,linear','linear','linear'],
            parang=True)

bandpass(vis=mmsfile,
         caltable='%s.bpass'%inbase,
         field=sbdcal,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase],
         interp=['linear','linear,linear','linear','linear'],
         solnorm=True,
         fillgaps=1,
         solint='inf',
         combine='scan',
         refant='PT,BR,HN,FD',
         bandtype='B',
         spwmap=[[],[],[],[]],
         parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='preapply_1')
applycal(vis=mmsfile,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,\
                    '%s.bpass'%inbase],
         interp=['linear','linear,linear','linear','linear','linear,linear'],
         spwmap=[[],[],[],[],[]],
         applymode='calonly',
         parang=True)
flagmanager(vis=mmsfile,mode='save',versionname='flag_2')
'''
## AOFLAG again

### Multi-band delays
'''
os.system('rm -r %s.bpass'%inbase)
bandpass(vis=mmsfile,
         caltable='%s.bpass'%inbase,
         field=sbdcal,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase],
         interp=['linear','linear,linear','linear','linear'],
         solnorm=True,
         fillgaps=1,
         solint='inf',
         combine='scan',
         refant='PT,BR,HN,FD',
         bandtype='B',
         spwmap=[[],[],[],[]],
         parang=True)
'''

os.system('rm -r %s.mbd'%inbase)
fringefit(vis=mmsfile,
          field=phasecal+','+sbdcal,
          caltable='%s.mbd'%inbase,
          combine='spw',
          solint='inf',
          zerorates=False,
          refant='PT,BR,HN',
          delaywindow=[-10,10],
          ratewindow=[-1,1],
          minsnr=2.,
          gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,'%s.bpass'%inbase],
          interp=['linear,linear','linear','linear','linear','linear,linear'],
          parang=True)

'''
#fill_flagged_soln('%s.mbd'%inbase)


flagmanager(vis=mmsfile,mode='save',versionname='pre_apply_2')
applycal(vis=mmsfile,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,'%s.mbd'%inbase,'%s.bpass'%inbase],
         interp=['linear','linear,linear','linear','linear','linear','linear,linear'],
         spwmap=[[],[],[], [],8*[0],[]],
         applymode='calonly',
         parang=True)

fringefit(vis=mmsfile,
          field=phasecal+','+sbdcal,
          caltable='%s.mbd2'%inbase,
          combine='spw',
          solint='inf',
          zerorates=False,
          refant='PT,BR,HN',
          delaywindow=[-10,10],
          ratewindow=[-1,1],
          minsnr=2.,
          gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,'%s.mbd'%inbase,'%s.bpass'%inbase],
          interp=['linear','linear,linear','linear','linear','linear','linear,linear'],
          spwmap=[[],[],[], [],8*[0],[]],
          parang=True)
'''