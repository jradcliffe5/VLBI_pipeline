import os

def find_refants(pref_ant,vis):
	tb.open('%s/ANTENNA'%vis)
	antennas = tb.getcol('NAME')
	tb.close()
	refant=[]
	for i in pref_ant:
		if i in antennas:
			refant.append(i)
	return ",".join(refant)

x = find_refants(['PT','BR','HN','FD','KP','MK','NL','OV','SC'],'a1/VLBA_a1.ms')
print(x)