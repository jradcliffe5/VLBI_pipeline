import os
#['a1','a2','b1','b2','c1','c2','c3','d1','d2','d3','e1','e2']
# bad c2 e1 e2
import os, sys

epoch=sys.argv[sys.argv.index(sys.argv[2])+1]
cwd=sys.argv[sys.argv.index(sys.argv[2])+2]
parallel=sys.argv[sys.argv.index(sys.argv[2])+3]


msfile='%s/%s.ms' %(cwd,epoch)

if parallel =='True':
	mmsfile = '%s' % (msfile.split('.ms')[0]+'.mms')
	## Make mms data-set
	os.system('rm -r %s*'%mmsfile)
	partition(vis=msfile, outputvis=mmsfile)
	os.system('rm -r %s'%msfile)
	os.system('mv %s %s'%(mmsfile,msfile))
	os.system('mv %s.flagversions %s.flagversions'%(mmsfile,msfile))
mmsfile=msfile

## DiFX correlator sampling corrections
#os.system('rm -r %s/VLBA.accor'%j)
#accor(vis=mmsfile,\
#      caltable='%s/VLBA.accor'%j,\
#      solint='inf')
#smoothcal(vis=mmsfile,
#          tablein='%s/VLBA.accor'%j,
#          caltable='%s/VLBA.accor'%j,
#	   smoothtime=180.0)

### Run prior-cals

#flagdata(vis=mmsfile,mode='list',inpfile='%s/%s_casa.flag'%(cwd,epoch))

os.system('rm -r %s/%s.tsys'%(cwd,epoch))
gencal(vis=mmsfile,\
       caltype='tsys',\
       spw='0~3',\
       antenna='!EF;!O8',\
       caltable='%s/%s.tsys'%(cwd,epoch),\
       uniform=False)

#flagdata(vis='%s/VLBA.tsys'%j,
#	 mode='clip',
#	 datacolumn='FPARAM',
#	 clipminmax=[0,370])
#smoothcal(vis=mmsfile,
#	  tablein='%s/%s.tsys'%(cwd,epoch),
#	  caltable='%s/%s.tsys'%(cwd,epoch),
#	  smoothtime=300.0)

os.system('rm -r %s/%s.gcal'%(cwd,epoch))
gencal(vis=mmsfile,\
       caltype='gc',\
       spw='0~3',\
       antenna='!EF;!O8',\
       caltable='%s/%s.gcal'%(cwd,epoch),\
       infile='%s/%s.gc'%(cwd,epoch))

os.system('rm %s/%s.listobs.txt'%(cwd,epoch))
listobs(vis=mmsfile,listfile='%s/%s.listobs.txt'%(cwd,epoch))
