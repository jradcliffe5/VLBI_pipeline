import os
step = sys.argv[sys.argv.index(sys.argv[2])+1]
src = sys.argv[sys.argv.index(sys.argv[2])+2]
src = '%03d'%int(src)
target_path = '/users/jradcliffe5/idia/VLBA_GOODSN/targets/raw_fitsidi/'

coords = {'049':['12h36m23.5436s','+62d16m42.754s'],
		  '055':['12h37m16.6811s','+62d17m33.327s'],
		  '081':['12h36m42.2123s','+62d15m45.521s'],
		  '085':['12h37m16.3740s','+62d15m12.343s'],
		  '097':['12h36m52.8839s','+62d14m44.076s'],
		  '110':['12h36m42.0908s','+62d13m31.425s'],
		  '111':['12h36m46.3321s','+62d14m04.693s'],
		  '156':['12h36m44.3870s','+62d11m33.145s'],
		  '160':['12h37m21.2539s','+62d11m29.954s'],
		  '164':['12h36m08.1195s','+62d10m35.898s'],
		  '182':['12h37m00.2480s','+62d09m09.778s'],
		  '183':['12h37m14.9414s','+62d08m23.208s']}
#coords=coords[src]
if step == '1':
	idifiles = []
	for i in os.listdir(target_path):
		if 'SRC%s'%src in i:
			idifiles.append(target_path+i)
	idifiles.sort()
	print(idifiles)

	importfitsidi(fitsidifile=idifiles,
				  vis='VLBA_SRC%s_pre.ms'%src,constobsid=False, scanreindexgap_s=15.0)
	os.system('rm -r VLBA_SRC%s.ms*'%src)
	partition(vis='VLBA_SRC%s_pre.ms'%src,outputvis='VLBA_SRC%s.ms'%src)
	os.system('rm -r VLBA_SRC%s_pre.ms*'%src)

def find_refants(pref_ant,vis):
   tb.open('%s/ANTENNA'%vis)
   antennas = tb.getcol('NAME')
   tb.close()
   refant=[]
   for i in pref_ant:
      if i in antennas:
         refant.append(i)
   return ",".join(refant)

if step == '2':
	# 'all/J1234+619_1combine.p', 'all/J1234+619_2.p', 'all/J1234+619_3.p', 'all/J1234+619_4combine.ap', 'all/J1234+619_5.p', 'all/J1234+619_6combine.p' J1234+619_7combine.p'
	vis = 'VLBA_SRC%s.ms'%src
	refant = find_refants(['PT','BR','HN','FD','KP','MK','NL','OV','SC'],vis)
	gaintables = ['all/VLBA.tsys', 'all/VLBA.gcal', 'all/VLBA.accor', 'all/VLBA.sbd', 'all/VLBA.bpass', 'all/VLBA.mbd1', 'all/VLBA.mbd2', 'all/VLBA.mbd3','all/J1234+619_1combine.p', 'all/J1234+619_2.p', 'all/J1234+619_3.p', 'all/J1234+619_4combine.ap', 'all/J1234+619_5combine.ap', 'all/J1234+619_6.p','all/J1234+619_7combine.p']
	spwmap=[]
	interp=[]
	
	for j in gaintables: 
		if ('.mbd' in j) or ('combine' in j): 
			spwmap.append(8*[0])
			interp.append('linearperobs')
		else: 
			spwmap.append([])
			interp.append('linearperobs')
	applycal(vis=vis,
		     gaintable=gaintables[0:5],
			 field='%s'%(int(src)+1),
		     spwmap=spwmap[0:5],
		     applymode='calflag',
			 interp=interp,
		     parang=True)
	applycal(vis=vis,
			 field='%s'%(int(src)+1),
		     gaintable=gaintables,
		     spwmap=spwmap,
		     applymode='calonly',
			 interp=interp,
		     parang=True)
	
	split(vis=vis,field='%s'%(int(src)+1),\
		  outputvis='VLBA_SRC%s_2.ms'%src,datacolumn='corrected')
	os.system('rm -r VLBA_SRC%s.ms; mv VLBA_SRC%s_2.ms VLBA_SRC%s.ms'%(src,src,src))
	
	os.system('rm -r test_%s.*'%src)
	tclean(vis="VLBA_SRC%s.ms"%src,selectdata=True,field="0",spw="",timerange="",uvrange="",antenna="",scan="",observation="",intent="",datacolumn="corrected",imagename="test_%s"%src,imsize=4000,cell="1mas",stokes="I",projection="SIN",startmodel="",specmode="mfs",reffreq="",nchan=-1,start="",width="",outframe="LSRK",veltype="radio",restfreq=[],interpolation="linear",perchanweightdensity=False,gridder="standard",facets=1,psfphasecenter="",chanchunks=1,wprojplanes=1,vptable="",usepointing=False,mosweight=True,aterm=True,psterm=False,wbawp=True,conjbeams=False,cfcache="",computepastep=360.0,rotatepastep=360.0,pblimit=0.2,normtype="flatnoise",deconvolver="hogbom",scales=[],nterms=2,smallscalebias=0.6,restoration=True,restoringbeam=[],pbcor=False,outlierfile="",weighting="natural",robust=0.5,noise="1.0Jy",npixels=0,uvtaper=[],niter=0,gain=0.1,threshold=0.0,nsigma=0.0,cycleniter=-1,cyclefactor=1.0,minpsffraction=0.05,maxpsffraction=0.8,interactive=False,usemask="user",mask="",pbmask=0.0,sidelobethreshold=3.0,noisethreshold=5.0,lownoisethreshold=1.5,negativethreshold=0.0,smoothfactor=1.0,minbeamfrac=0.3,cutthreshold=0.01,growiterations=75,dogrowprune=True,minpercentchange=-1.0,verbose=False,fastnoise=True,restart=True,savemodel="none",calcres=True,calcpsf=True,parallel=False)
