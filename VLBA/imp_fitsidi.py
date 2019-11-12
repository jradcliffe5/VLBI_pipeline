import os
#['a1','a2','b1','b2','c1','c2','c3','d1','d2','d3','e1','e2']
# bad c1 e1 e2
for j in ['all']:
	idifiles=[]
	os.system('rm -r %s'%j)
	if j == 'all':
		for k in ['a1','a2','b1','b2','c1','c2','c3','d1','d2','d3','e1','e2']:
			for i in os.listdir('/users/jradcliffe5/idia/VLBA_GOODSN/%s'%k):
				if i.endswith('.idifits'):
					idifiles.append('/users/jradcliffe5/idia/VLBA_GOODSN/%s/%s'%(k,i))
	else:
		for i in os.listdir('/users/jradcliffe5/idia/VLBA_GOODSN/%s'%j):
			if i.endswith('.idifits'):
				idifiles.append('/users/jradcliffe5/idia/VLBA_GOODSN/%s/%s'%(j,i))
	os.system('mkdir %s'%j)
	importfitsidi(fitsidifile=idifiles,vis='%s/VLBA_%s.ms'%(j,j),
	          constobsid=False, scanreindexgap_s=15.0)