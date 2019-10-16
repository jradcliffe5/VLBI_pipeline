import os
src = sys.argv[sys.argv.index(sys.argv[2])+1]
src = '%03d'%int(src)
mstransform(vis='VLBA_SRC%s.ms'%src,
	        createmms=False,
	        datacolumn='data',
			combinespws=True,
	        outputvis='VLBA_SRC%s_mstransform.ms'%src)
#os.system('rm  VLBA_SRC%s.ms; mv VLBA_SRC%s_2.ms VLBA_SRC%s.ms'%(src,src,src))