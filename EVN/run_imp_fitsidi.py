import os,sys

inbase = sys.argv[sys.argv.index(sys.argv[2])+1]
idifiles=[]
for i in os.listdir('./'):
	if i.startswith('%s_1_1'%inbase):
		idifiles.append('%s'%(i))

importfitsidi(fitsidifile=idifiles,vis='%s.ms'%(inbase),
	          constobsid=False, scanreindexgap_s=15.0)