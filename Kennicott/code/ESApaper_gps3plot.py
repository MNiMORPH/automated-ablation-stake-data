#! /usr/bin/python

from matplotlib import pyplot as plt
import numpy as np
from  datetime import datetime as dt
from scipy.stats import nanmean

# Originally for 2013 AGU poster
# Modified for ESA paper for Collin Bode

d = np.loadtxt('alog_gps3.txt')
d = d[d[:,0] < 1.363E9]
d[:,2:-1][d[:,2:-1] < 100] = np.nan
d[:,2:-1][d[:,2:-1] > 500] = np.nan

datetime_utc = []
for ts in d[:,0]:
  datetime_utc.append(dt.utcfromtimestamp(ts))
  
TdegC = d[:,1]
dist = []
for i in range(len(d)):
  try:
    dist.append(nanmean(d[i,2:-1]))
  except:
    dist.append(np.nan)
dist = np.array(dist)
snowdepth = (np.nanmax(dist) - dist)/100.

#dist = nanmean(d[2:-1], axis=1) -- totally removes nan rows though :(


plt.figure(figsize=(7,5.5))
plt.subplot(2,1,1)
plt.plot(datetime_utc, TdegC, 'k', linewidth=1)
plt.ylabel(r'Temperature [$^\circ$C]', fontsize=16)
#plt.title('Kennicott Glacier, Alaska', fontsize=24)
plt.subplot(2,1,2)
plt.plot(datetime_utc, snowdepth, 'k.', markersize=2)
plt.ylabel('Snow depth relative\nto minimum [m]', fontsize=16, multialignment='center')
plt.tight_layout()
plt.savefig('KennicottData.png', dpi=300)
plt.show()

