import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

plt.ion()

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

def calc_r_squared(fitfcn, x, y, *popt):
    residuals = y - fitfcn(x, *popt)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum( (y - np.mean(y))**2 )
    _r_squared = 1 - (ss_res / ss_tot)
    return _r_squared


data = pd.read_csv('AS-1-full.csv', header=1)

# Correct time column
data['Time [UTC]'] = pd.to_datetime(data['Time [UTC]'])

# Remove error values from distance
# Amazingly, no error values, so this will be really easy to process.
# One might say, a textbook (journal page?) example!
# Though I guess a better one would involve more decisions.
# Still, when introducing the instrument for the first time, it might be good
# to leave my usual inclination to go all complexity all at once and be a bit
# more modest.
data['Distance [mm]'][data['Distance [mm]'] > 4999] = np.nan
data['Distance [mm]'][data['Distance [mm]'] <= 500] = np.nan
# Well, 7 are missing.
# Will just interpolate through them.
data['Distance [mm]'] = data['Distance [mm]'].interpolate()

dt = data['Time [UTC]']
date_list = get_dates(dt)
date_set = list(set(date_list))
dates = np.array(date_list)

# Melt -- First-hour average is the starting point
dist0 = np.mean(data['Distance [mm]'][:12])
melt_mm = data['Distance [mm]'] - dist0

# Positive degree days, cumulative
# All temp data are good, as in finite. Great.
measurement_dt = data.diff()['Time [UTC]']
dt_fract_days = measurement_dt / pd.Timedelta(days=1)

dT = 0
PDD = (data['Temp Atmos [C]'] + dT) * ((data['Temp Atmos [C]'] + dT) > 0) * dt_fract_days

# New DDF (PDD melt factor) every 50 degree days
DDF_list = []
offset_list = []
for max_degree_days in [50, 100, 150, 200]:
    min_degree_days = max_degree_days - 50
    _range = (np.cumsum(PDD) >= min_degree_days) * (np.cumsum(PDD) < max_degree_days)
    PDD_in_range = np.array(np.cumsum(PDD[_range]))
    start_PDD = np.array(np.cumsum(PDD)[_range])[0]
    melt_mm_in_range = np.array(melt_mm[_range])
    start_melt_mm = melt_mm_in_range[0]
    melt_mm_in_range -= melt_mm_in_range[0]
    popt, pcov = curve_fit(linfit_noint, PDD_in_range, melt_mm_in_range)
    DDF_list.append(popt[0])
    offset_list.append(start_melt_mm - popt[0]*start_PDD)
    print(popt)

print("LINEAR, ZERO INTERCEPT")
popt, pcov = curve_fit(linfit_noint, np.cumsum(PDD[1:]), melt_mm[1:])
print("Melt Factor =", popt[0], "mm / (degC day)")
print("R squared =", calc_r_squared(linfit_noint, np.cumsum(PDD[1:]), melt_mm[1:], popt))

# Total time and melt rate like Braithwaite
t_tot = (data['Time [UTC]'][len(data)-1] - data['Time [UTC]'][0]).total_seconds()/60**2/24.
dz_tot = np.mean(data['Distance [mm]'][-12:]) - np.mean(data['Distance [mm]'][:12])
T_mean = data['Temp Atmos [C]'].mean()
print("")
print("Melt factor cumulative simple:", dz_tot / (t_tot * T_mean) )

plt.figure()
plt.plot( np.cumsum(PDD[1:]), melt_mm[1:], '.', alpha=0.05 )
# Incremental DDFs
for i in range(4):
    _x_fit = np.array([i*50, (i+1)*50])
    _y_fit = DDF_list[i] * _x_fit + offset_list[i]
    plt.plot(_x_fit, _y_fit, '0.', label='DDF = '+'%.1f' %DDF_list[i])
_x_fit = np.array( plt.gca().get_xlim() )
_label = 'PDD melt factor = DDF = '+'%.1f' %popt[0]+' mm/(\u00b0C day)'
_y_fit = linfit_noint(_x_fit, *popt)
plt.plot(_x_fit, _y_fit, '.3', label=_label)
plt.xlabel('Cumulative positive degree days [\u00b0C day]', fontsize=14)
plt.ylabel('Cumulative ablation [mm]', fontsize=14)
plt.legend(fontsize=11)
plt.tight_layout()
#plt.savefig('AS-1_integral_2023.svg')

# dT 0 to -5: R2 .96 to .97. Not worrying about it!


# Time series -- humidity now included
fig = plt.figure(figsize=(8,8.5))
ax1 = plt.subplot(3,1,1)
ax2 = plt.subplot(3,1,2)
ax3 = plt.subplot(3,1,3)
ax1.plot(data['Time [UTC]'], data['Distance [mm]'], 'k.', alpha=.1)
ax2.plot(data['Time [UTC]'], data['Temp Atmos [C]'], 'r.', alpha=.1)
ax3.plot(data['Time [UTC]'], data['Humidity [%]'], 'b.', alpha=.1)
ax1.set_ylabel('Distance to\nice surface [mm]', fontsize=14)
ax2.set_ylabel('Temperature [\u00b0C]', fontsize=14)
ax3.set_ylabel('Relative humidity [%]', fontsize=14)
fig.autofmt_xdate()
fig.tight_layout()
#plt.savefig('AS-1_PeritoMoreno_dist_T_RH__2023.pdf')
#plt.savefig('AS-1_PeritoMoreno_T_dist.pdf')
#plt.savefig('AS-1_PeritoMoreno_T_dist.png')
#plt.savefig('AS-1_PeritoMoreno_T_dist.svg')


"""
plt.figure()
for dT in [-8, -5, -2, 0, 2, 5, 8]:
    measurement_dt = data.diff()['Time [UTC]']
    dt_fract_days = measurement_dt / pd.Timedelta(days=1)
    PDD = (data['Temp Atmos [C]'] + dT) * ((data['Temp Atmos [C]'] + dT) > 0) * dt_fract_days
    plt.plot( np.cumsum(PDD[1:]), melt_mm[1:], '.', alpha=0.05 )
"""

"""
dt = -5
measurement_dt = data.diff()['Time [UTC]']
dt_fract_days = measurement_dt / pd.Timedelta(days=1)
PDD = (data['Temp Atmos [C]'] + dT) * ((data['Temp Atmos [C]'] + dT) > 0) * dt_fract_days
plt.plot( np.cumsum(PDD[1:]), melt_mm[1:], '.', alpha=0.05 )
"""

# Test impact of relative humidity
_RH = data['Humidity [%]']/100. # RH 0 to 1
_Tpos = data['Temp Atmos [C]'] * (data['Temp Atmos [C]'] > 0)
_dist = melt_mm

def linfit_rh(X, a1, a2, b):
    T, RH = X
    return (a1 + a2*RH) * T + b

def linfit_noint_rh(X, a1, a2):
    T, RH = X
    return (a1 + a2*RH) * T

_pdd = _Tpos * dt_fract_days
_pdd_cumsum = np.cumsum(_pdd)
_rhd = _RH * dt_fract_days
_rhd_cumsum = np.cumsum(_rhd)

# rm NaN
_pdd_cumsum = _pdd_cumsum[ np.isnan(_dist) == False ][1:]
_rhd_cumsum = _rhd_cumsum[ np.isnan(_dist) == False ][1:]
_dist = _dist[ np.isnan(_dist) == False ][1:]


print("")

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

print("")

print("No intercept")

popt, pcov = curve_fit(linfit_noint_rh, _X, _dist)
print("Melt Factor =", popt[0], "mm / (degC day)")
print("RH Factor =", popt[1], "mm / day")

residuals = _dist - linfit_noint_rh(_X, *popt)
ss_res = np.sum(residuals**2)
ss_tot = np.sum(( _dist - np.mean(_dist))**2 )
r2 = 1 - ss_res/ss_tot
print ("R2: ", r2)

print("")

# Plot with humidity
fig = plt.figure()
ax = fig.add_subplot(1,1,1)
ax.plot( ( popt[0] + popt[1] * _rhd_cumsum ) * _pdd_cumsum, _dist, '.', alpha=.1)
# Kludge: hard-code minus sign
ax.set_xlabel('$\sum_t \left( %.1f' %popt[0]+' - %.1f' %-popt[1]+r'\phi \right) T^+$', fontsize=14)
ax.set_ylabel('Cumulative ablation [mm]', fontsize=14)
# Plot curve fit
_label = '1:1 line\n'+\
         'Ablation factor = $f_\mathcal{A}$ = '+'%.1f' %popt[0]+' mm/(\u00b0C day)\n'+\
         'RH factor = $f_{\mathcal{A},\phi}$ = '+'%.1f' %popt[1]+' mm/(\u00b0C day)'
ax.plot( ( popt[0] + popt[1] * _rhd_cumsum ) * _pdd_cumsum, linfit_noint_rh( _X, *popt), '.3', label=_label)
#ax.plot( ax.get_xlim(), ax.get_xlim() )
plt.legend(fontsize=11)
plt.tight_layout()
plt.show()
plt.savefig('PDD_RH_2023.svg')





# Subset by day
"""
# Pandas has some built-in ways to do this sort of thing, but I didn't
# know how to use them when I wrote this quickly in Argentina.
T_mean = []
melt_mm_day = []
for date in date_set[1:-2]:
    data_on_date = data[dates == date]
    # T
    T_mean.append( np.mean(data_on_date['Temp Atmos [C]']) )
    # Distance
    # FIX "DISTANCE"
    distfinite = data_on_date['Distance [mm]'][np.isfinite(data_on_date['Distance [mm]'])]
    time_in_day_distfinite = data_on_date['Time [UTC]'][np.isfinite(data_on_date['Distance [mm]'])]
    secs_in_day_distfinite = get_timestamp(time_in_day_distfinite)
    secs_in_day_distfinite -= secs_in_day_distfinite[0]
    fract_of_day_distfinite = secs_in_day_distfinite / (24 * 60 * 60.)
    popt, pcov = curve_fit(linfit, fract_of_day_distfinite, distfinite)
    melt_mm_day.append(popt[0])
"""
# 2023 update

# For new method: Prep data
_diff = data.diff()
_dt_days_multiplier = pd.Timedelta('1D')/_diff['Time [UTC]']
__dh = np.array(_dt_days_multiplier * _diff['Distance [mm]'])[1:]
__T_mid = np.array(data['Temp Atmos [C]'][1:] + data['Temp Atmos [C]'][1:])/2.
__t_mid = np.array(data['Time [UTC]'] - _diff['Time [UTC]']/2.)[1:]
d2 = pd.DataFrame( data=np.array([__T_mid, __dh]).transpose(),
                   index=__t_mid,
                   columns=('Temp Atmos [C]', 'Melt rate [mm/day]') )

_freq = '1D'
_bins = data.groupby(pd.Grouper(key='Time [UTC]', freq=_freq))
_group_ids = list(set(_bins.ngroup()))
melt_mm_day = []
for _id in _group_ids[1:-1]:
    _subset = data[_bins.ngroup() == _id]
    time = _subset['Time [UTC]']
    time -= time[time.idxmin()]
    dt_days = time.dt.total_seconds() / 86400
    dist = _subset['Distance [mm]']
    popt, pcov = curve_fit(linfit, dt_days, dist)
    melt_mm_day.append(popt[0])

# Bringing this in for the temperature
bins = d2.groupby(pd.Grouper(freq=_freq)).mean()

T_mean = bins['Temp Atmos [C]'][1:-1]
melt_mm_day = np.array(melt_mm_day)

# dz/dt (melt) = MeltFactor * T
print("LINEAR, ZERO INTERCEPT")
popt, pcov = curve_fit(linfit_noint, T_mean, melt_mm_day)
print("Melt Factor =", popt[0], "mm / (degC day)")
print("R squared =", calc_r_squared(linfit_noint, T_mean, melt_mm_day, popt))

print("")
print("LINEAR WITH NONZERO INTERCEPT")
poptI, pcovI = curve_fit(linfit, T_mean, melt_mm_day)
T0 = poptI[1] / poptI[0] # Temperature intercept; see pen + paper algebra
print("Melt Factor =", poptI[0], "mm / (degC day)")
# print("MFint =", poptI[1], "mm / day")
print("T0 =", T0, "degC")
print("R squared =", calc_r_squared(linfit, T_mean, melt_mm_day, *poptI))


# Melt-factor curve fit
fig2 = plt.figure()
axf2 = plt.subplot(1,1,1)
axf2.plot(T_mean, melt_mm_day, 'ko')#, label='Data')
_x_fit = np.array( axf2.get_xlim() )
_y_fit = linfit(_x_fit, *poptI)
_label = '$f_m$ = '+'%.1f' %poptI[0]+' mm/(\u00b0C day)\n'+ \
            '$T_0$ = '+'%.1f' %T0+' \u00b0C'
axf2.plot(_x_fit, _y_fit, '.7', label=_label)
_label = 'DDF = '+'%.1f' %popt[0]+' mm/(\u00b0C day)'
_y_fit = linfit_noint(_x_fit, *popt)
axf2.plot(_x_fit, _y_fit, '.3', label=_label)
axf2.legend(fontsize=11)
axf2.set_xlabel('Mean daily temperature [\u00b0C]', fontsize=14)
axf2.set_ylabel('Melt [mm/day]', fontsize=14)
fig2.tight_layout()
fig2.savefig('AS-1_scatter_2023.svg')


# Overall average melt rate
dz = data['Distance [mm]'][5396] - data['Distance [mm]'][0]
dt = (data['Time [UTC]'][5396] - data['Time [UTC]'][0]).total_seconds()
dt_hours = dt / (60*60)
dt_days = dt / (60*60*24)
average_melt_rate__mm_hr = dz / dt_hours
average_melt_rate__mm_day = dz / dt_days
print( "Mean melt rate:" )
print( average_melt_rate__mm_hr, "mm/hr" )

