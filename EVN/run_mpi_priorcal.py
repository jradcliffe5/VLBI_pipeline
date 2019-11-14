import os,sys

inbase = sys.argv[sys.argv.index(sys.argv[2])+1]

msfile='%s.ms' %(inbase)

mmsfile=msfile


### Run prior-cals
os.system('rm -r %s.tsys'%inbase)
gencal(vis=mmsfile,\
	   caltype='tsys',\
	   caltable='%s.tsys'%inbase,\
	   uniform=False)
#flagdata(vis='%s.tsys'%inbase,
#		 mode='clip',
#		 datacolumn='FPARAM',
#		 clipminmax=[0,370])
smoothcal(vis=mmsfile,
		  tablein='%s.tsys'%inbase,
		  caltable='%s.tsys'%inbase,
		  smoothtime=300.0)

os.system('rm -r %s.gcal'%inbase)
gencal(vis=mmsfile,\
	   caltype='gc',\
	   caltable='%s.gcal'%inbase,\
	   infile='%s.gc'%inbase)

flagdata(vis=mmsfile,
	     mode='list',
	     inpfile='%s.CASA.flags.txt'%inbase)

	#ft(vis=mmsfile,
	#   field='J1234+619',
	#   model='J1234+619_7.model',
	#   usescratch=True)
