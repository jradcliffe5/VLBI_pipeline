## source find images
import glob
imstats = {}
images = glob.glob('../output_nopbcor/*image')
n=7
SNR_c = 0
Nim = 0
for image in images:
    ia.open(image)
    rms = ia.statistics(algorithm='fit-half')['rms'][0]
    source = ia.findsources(nmax=1)['component0']
    ia.close()
    if source['flux']['value'][0]/rms > n:
        imstats[image]= {}
        imstats[image]['RA'] = source['shape']['direction']['m0']['value']
        imstats[image]['Dec'] = source['shape']['direction']['m1']['value']
        imstats[image]['Flux'] = source['flux']['value'][0]*1e6
        imstats[image]['rms'] = rms
        imstats[image]['SNR'] = source['flux']['value'][0]/rms
        SNR_c = SNR_c + imstats[image]['SNR']
        Nim+=1

print(imstats)
print(SNR_c,Nim)