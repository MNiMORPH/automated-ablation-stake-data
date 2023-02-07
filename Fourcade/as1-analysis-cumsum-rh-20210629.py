import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

# Silence warning
pd.options.mode.chained_assignment = None  # default='warn'

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

data = pd.read_csv('Melt_data_AS1_copy.csv', header=1, parse_dates=True, infer_datetime_format=True, index_col='Time [UTC]')

# Remove error values from distance
data['Distance [mm]'][data['Distance [mm]'] > 4999] = np.nan
data['Distance [mm]'][data['Distance [mm]'] <= 500] = np.nan
data['Dist_cor'][np.isnan(data['Distance [mm]'])] = np.nan
data['Dist_cor'][np.isnan(data['Distance [mm]'])] = np.nan

dt = data.index
date_list = get_dates(dt)
date_set = list(set(date_list))
dates = np.array(date_list)

# Extract a set of days
start_date = '2021-02-11'
end_date = '2021-02-18'
start_date = '2020-12-26'
end_date = '2021-01-01'
#start_date = '2021-01-04'
#end_date = '2021-01-09'
mask = (data.index >= start_date) * (data.index <= end_date)

_Tpos = data['Temp'][mask] * (data['Temp'][mask] > 0)
_dist = data['Dist_cor'][mask]
_RH = data[' Humidity [%]'][mask]/100. # RH 0 to 1

# Check that this is every five minutes -- normalize by time as necessary
# Can't figure out how to convert internally from ns to days
_dt = np.diff(data.index[mask]).astype(float) / (1E9 * 60 * 60 * 24)
# Kludge
_dt = np.hstack((_dt, [_dt[-1]]))

# How to best add in the melt factor? Curve fit -- M = not just a param?

def linfit_rh(X, a1, a2, b):
    T, RH = X
    return (a1 + a2*RH) * T + b

_pdd = _Tpos * _dt
_pdd_cumsum = np.cumsum(_pdd)
_rhd = _RH * _dt
_rhd_cumsum = np.cumsum(_rhd)

# rm NaN
_pdd_cumsum = _pdd_cumsum[ np.isnan(_dist) == False ]
_rhd_cumsum = _rhd_cumsum[ np.isnan(_dist) == False ]
_dist = _dist[ np.isnan(_dist) == False ]


print("")
print(start_date, '--', end_date)

_X = np.vstack((_pdd_cumsum, _rhd_cumsum))

popt, pcov = curve_fit(linfit_rh, _X, _dist)
print("Melt Factor =", popt[0], "mm / (degC day)")
print("RH Factor =", popt[1], "mm / day")

residuals = _dist - linfit_rh(_X, *popt)
ss_res = np.sum(residuals**2)
ss_tot = np.sum(( _dist - np.mean(_dist))**2 )
r2 = 1 - ss_res/ss_tot
print ("R2: ", r2)

print("")


fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot( ( popt[0] + popt[1] * _rhd_cumsum ) * _pdd_cumsum, _dist, 'k.', alpha=.1)
ax.set_xlabel('Cumulative positive humidity degree days [K day]', fontsize=14)
ax.set_ylabel('Distance to glacier surface [mm]', fontsize=14)

# Plot curve fit
#ax.plot( ax.get_xlim(), linfit_rh( np.array(ax.get_xlim()), *popt), 'k-', linewidth=2)

plt.tight_layout()
plt.show()

