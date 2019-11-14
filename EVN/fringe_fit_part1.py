import sys, os
inbase =sys.argv[sys.argv.index(sys.argv[2])+1]
phasecal=sys.argv[sys.argv.index(sys.argv[2])+2]
sbdcal=sys.argv[sys.argv.index(sys.argv[2])+3]

inbase='%s'%inbase
mmsfile = '%s.ms'%inbase

def find_refants(pref_ant,vis):
   tb.open('%s/ANTENNA'%vis)
   antennas = tb.getcol('NAME')
   tb.close()
   refant=[]
   for i in pref_ant:
      if i in antennas:
         refant.append(i)
   return ",".join(refant)

refant = find_refants(['EF','T6','O8','WB','MC','TR','SV','BD','ZC'],mmsfile)

flagmanager(vis=mmsfile,mode='save',versionname='flag_1')
flagdata(vis=mmsfile,
         mode='manual',
         spw='0:0~2;30~32, 1:0~2;30~32, 2:0~2;30~32, 3:0~2;30~32, 4:0~2;30~32, 5:0~2;30~32, 6:0~2;30~32,7:0~2;30~32')
flagdata(vis=mmsfile, mode='manual',autocorr=True)

os.system('rm -r %s.sbd'%inbase)
fringefit(vis=mmsfile,
            caltable='%s.sbd'%inbase,
            field=sbdcal,
            solint='inf',
            zerorates=True,
            refant=refant,
            minsnr=5,
            gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase],
            interp=['linearperobs,linear','linearperobs','linearperobs'],
            parang=True)

bandpass(vis=mmsfile,
         caltable='%s.bpass'%inbase,
         field=sbdcal,
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.sbd'%inbase],
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
         gaintable=['%s.tsys'%inbase,'%s.gcal'%inbase,'%s.sbd'%inbase,\
                    '%s.bpass'%inbase],
         interp=['linearperobs','linearperobs,linear','linearperobs','linearperobs','linearperobs,linear'],
         spwmap=[[],[],[],[],[]],
         applymode='',
         parang=True)

flagmanager(vis=mmsfile,mode='save',versionname='flag_2')