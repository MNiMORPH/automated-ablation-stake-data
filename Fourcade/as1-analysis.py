import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

#plt.ion()

def get_dates(datetime_list):
    out = []
    for item in datetime_list:
        out.append(item.date())
    return out
        
def linfit(x, a, b):
    return a*x+b
    
def linfit_noint(x, a):
    return a*x

def get_timestamp(datetime_list):
    out = []
    for item in datetime_list:
        out.append(item.timestamp())
    return np.array(out)

data = pd.read_csv('Melt_data_AS1_copy.csv', header=1)

# Correct time column
data['Time [UTC]'] = pd.to_datetime(data['Time [UTC]'])

# Remove error values from distance
data['Distance [mm]'][data['Distance [mm]'] > 4999] = np.nan
data['Distance [mm]'][data['Distance [mm]'] <= 500] = np.nan

dt = data['Time [UTC]']
date_list = get_dates(dt)
date_set = list(set(date_list))
dates = np.array(date_list)

# Subset by day
# Pandas has some built-in ways to do this sort of thing, but I didn't
# know how to use them when I wrote this quickly in Argentina.
T_mean = []
melt_mm_day = []
for date in date_set[1:-2]:
    data_on_date = data[dates == date]
    # Distance
    # FIX "DISTANCE"
    distfinite = data_on_date['Dist_cor'][np.isfinite(data_on_date['Dist_cor'])]
    time_in_day_distfinite = data_on_date['Time [UTC]'][np.isfinite(data_on_date['Dist_cor'])]
    secs_in_day_distfinite = get_timestamp(time_in_day_distfinite)
    secs_in_day_distfinite -= secs_in_day_distfinite[0]
    fract_of_day_distfinite = secs_in_day_distfinite / (24 * 60 * 60.)
    # Append to array if there are real data for the day
    if len(fract_of_day_distfinite) > 1:
        popt, pcov = curve_fit(linfit, fract_of_day_distfinite, distfinite)
        melt_mm_day.append(popt[0])
        # T
        T_mean.append( np.mean(data_on_date['Temp']) )
    
# POP the outlier -- fix this to be more rigorous later
melt_mm_day.pop(1)
T_mean.pop(1)
    
# Remove outlier by hand
melt_mm_day_nooutliers = melt_mm_day
T_mean_nooutliers = T_mean
melt_mm_day_outlier = melt_mm_day_nooutliers.pop(2)
T_mean_outlier = T_mean.pop(2)

# dz/dt (melt) = MeltFactor * T
popt, pcov = curve_fit(linfit_noint, T_mean, melt_mm_day)
print("Melt Factor =", popt[0], "mm / (degC day)")

poptI, pcovI = curve_fit(linfit, T_mean, melt_mm_day)
#print("Melt Factor =", popt[0], "mm / (degC day)")
#print("MFint =", popt[1], "mm / day")

# Time series
fig = plt.figure(figsize=(8,6))
ax1 = plt.subplot(2,1,1)
ax2 = plt.subplot(2,1,2)
ax1.plot(data['Time [UTC]'], data['Dist_cor'], 'k.', alpha=.1)
ax2.plot(data['Time [UTC]'], data['Temp'], 'r.', alpha=.1)
ax1.set_ylabel('Distance to\nice surface [mm]', fontsize=14)
ax2.set_ylabel('Temperature [$^\circ$C]', fontsize=14)
fig.autofmt_xdate()
fig.tight_layout()

# Melt-factor curve fit
fig2 = plt.figure()
axf2 = plt.subplot(1,1,1)
axf2.plot(T_mean_nooutliers, melt_mm_day_nooutliers, 'ko', label='Data')
axf2.plot(T_mean_outlier, melt_mm_day_outlier, 'wo', markeredgecolor='k',
          label='Outlier: rangefinder spun?\nCheck wind direction.')
_x_fit = np.array( axf2.get_xlim() )
_y_fit = linfit(_x_fit, *poptI)
_label = 'Intercept at '+'%.1f' %poptI[1]+' mm/day\n'+ \
              'melt factor = '+'%.1f' %poptI[0]+' mm/($^\circ$C day)'
axf2.plot(_x_fit, _y_fit, '.3', label=_label)
_label = 'Intercept at 0 mm/day\n'+ \
              'melt factor = '+'%.1f' %popt[0]+' mm/($^\circ$C day)'
_y_fit = linfit_noint(_x_fit, *popt)
axf2.plot(_x_fit, _y_fit, '.7', label=_label)
axf2.legend(fontsize=11)
axf2.set_xlabel('Mean daily temperature [$^\circ$C]', fontsize=14)
axf2.set_ylabel('Total daily melt [mm/day]', fontsize=14)
fig2.tight_layout()

plt.show()
