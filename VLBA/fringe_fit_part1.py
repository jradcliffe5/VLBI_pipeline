import sys, os
epoch =sys.argv[sys.argv.index(sys.argv[2])+1]
phasecal=sys.argv[sys.argv.index(sys.argv[2])+2]
sbdcal=sys.argv[sys.argv.index(sys.argv[2])+3]

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

flagmanager(vis=mmsfile,mode='save',versionname='flag_1')
flagdata(vis=mmsfile,
         mode='manual',
         spw='0:0~5;122~127, 1:0~5;122~127, 2:0~5;122~127, 3:0~5;122~127, 4:0~5;122~127, 5:0~5;122~127, 6:0~5;122~127,7:0~5;122~127')
flagdata(vis=mmsfile, mode='manual',autocorr=True)

os.system('rm -r %s.sbd'%inbase)
fringefit(vis=mmsfile,
            caltable='%s.sbd'%inbase,
            field=sbdcal,
            solint='inf',
            zerorates=True,
            refant=refant,
            minsnr=5,
            gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase],
            interp=['linearperobs,linear','linearperobs','linearperobs'],
            parang=True)

bandpass(vis=mmsfile,
         caltable='%s.bpass'%inbase,
         field=sbdcal,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase],
         interp=['linearperobs','linearperobs,linear','linearperobs','linearperobs'],
         solnorm=True,
         fillgaps=4,
         solint='inf',
         combine='scan',
         refant=refant,
         bandtype='B',
         spwmap=[[],[],[],[]],
         parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='preapply_1')
applycal(vis=mmsfile,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.accor'%inbase,'%s.sbd'%inbase,\
                    '%s.bpass'%inbase],
         interp=['linearperobs','linearperobs,linear','linearperobs','linearperobs','linearperobs,linear'],
         spwmap=[[],[],[],[],[]],
         applymode='',
         parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='flag_2')