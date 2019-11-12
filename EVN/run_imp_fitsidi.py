import os,sys
#['a1','a2','b1','b2','c1','c2','c3','d1','d2','d3','e1','e2']
# bad c1 e1 e2
inbase = sys.argv[sys.argv.index(sys.argv[2])+1]
for i in os.listdir('./'):
	if i.startswith('%s._1_1'%inbase):
		idifiles.append('%s'%(i))

importfitsidi(fitsidifile=idifiles,vis='%s.ms'%(inbase),
	          constobsid=False, scanreindexgap_s=15.0)