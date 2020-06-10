os.system('rm -r target_test_rms.*')
tclean(vis='all/test_target.ms',
	   cell='0.001arcsec',
	   imsize=[640,640],
	   pblimit=1e-5,
	   imagename='target_test_rms',
	   parallel=False)