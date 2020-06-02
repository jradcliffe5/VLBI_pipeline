import os, sys

epoch=sys.argv[sys.argv.index(sys.argv[2])+1]
cwd=sys.argv[sys.argv.index(sys.argv[2])+2]
idifiles=[]
os.system('rm -r %s.ms*'%epoch)
for i in os.listdir('%s'%(cwd)):
	if i.startswith('%s_1_1.IDI'%epoch):
		idifiles.append('%s/%s'%(cwd,i))
importfitsidi(fitsidifile=idifiles,vis='%s/%s.ms'%(cwd,epoch),
	          constobsid=True, scanreindexgap_s=15.0)

os.system('rm %s/%s.listobs.txt'%(cwd,epoch))
listobs(vis='%s/%s.ms'%(cwd,epoch),listfile='%s/%s.listobs.txt'%(cwd,epoch))
