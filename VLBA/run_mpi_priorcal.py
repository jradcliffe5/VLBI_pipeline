import os
#['a1','a2','b1','b2','c1','c2','c3','d1','d2','d3','e1','e2']
# bad c2 e1 e2
for j in ['all']:
	msfile='%s/VLBA_%s.ms' %(j,j)
	#mmsfile = '%s' % (msfile.split('.ms')[0]+'.mms')
	#mmsfile=msfile
	### Make mms data-set
	#os.system('rm -r %s*'%mmsfile)
	#partition(vis=msfile, outputvis=mmsfile)
	#os.system('rm -r %s'%msfile)
	#os.system('mv %s %s'%(mmsfile,msfile))
	mmsfile=msfile

	## DiFX correlator sampling corrections
	os.system('rm -r %s/VLBA.accor'%j)
	accor(vis=mmsfile,\
		  caltable='%s/VLBA.accor'%j,\
		  solint='inf')
	smoothcal(vis=mmsfile,
			  tablein='%s/VLBA.accor'%j,
			  caltable='%s/VLBA.accor'%j,
			  smoothtime=180.0)

	### Run prior-cals
	os.system('rm -r %s/VLBA.tsys'%j)
	gencal(vis=mmsfile,\
		   caltype='tsys',\
		   caltable='%s/VLBA.tsys'%j,\
		   uniform=False)
	flagdata(vis='%s/VLBA.tsys'%j,
			 mode='clip',
			 datacolumn='FPARAM',
			 clipminmax=[0,370])
	smoothcal(vis=mmsfile,
			  tablein='%s/VLBA.tsys'%j,
			  caltable='%s/VLBA.tsys'%j,
			  smoothtime=300.0)

	os.system('rm -r %s/VLBA.gcal'%j)
	gencal(vis=mmsfile,\
		   caltype='gc',\
		   caltable='%s/VLBA.gcal'%j,\
		   infile='VLBA.gc')

	#ft(vis=mmsfile,
	#   field='J1234+619',
	#   model='J1234+619_7.model',
	#   usescratch=True)
