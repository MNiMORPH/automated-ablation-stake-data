import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
from string import ascii_lowercase

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
# BETTER SOLUTION LATER
data['Distance [mm]'] = data['Distance [mm]'].interpolate()

# Limit data to full days

# Maybe not needed?
dt = data['Time [UTC]']
date_list = get_dates(dt)
date_set = list(set(date_list))
dates = np.array(date_list)

# For new method: Prep data
_diff = data.diff()
_dt_days_multiplier = pd.Timedelta('1D')/_diff['Time [UTC]']
__dh = np.array(_dt_days_multiplier * _diff['Distance [mm]'])[1:]
__T_mid = np.array(data['Temp Atmos [C]'][1:] + data['Temp Atmos [C]'][1:])/2.
__t_mid = np.array(data['Time [UTC]'] - _diff['Time [UTC]']/2.)[1:]
d2 = pd.DataFrame( data=np.array([__T_mid, __dh]).transpose(),
                   index=__t_mid,
                   columns=('Temp Atmos [C]', 'Melt rate [mm/day]') )

#windows = [1/4., 1/2., 1, 2, 4, 6, 8, 12, 24, 48, 36, 48]
windows = [1/2., 1, 2, 4, 6, 8, 12, 24, 36, 48, 72, 96]
#windows = [6.] # for test
fig2 = plt.figure(figsize=(10,12))
ax_i=1
fM_list = []
T0_list = []
R2_list = []
for _window in windows:

    """
    # OLD METHOD
    # 'min' for minutes; 'H' for hours
    _freq = str(_window)+'H'
    _freq2 = str(_window/2.)+'H'
    bins_raw = data.groupby(pd.Grouper(key='Time [UTC]', freq=_freq)).mean()
    bins = pd.DataFrame( index=bins_raw.index[:-1] + pd.Timedelta(_freq2),
                         columns=('Temp Atmos [C]', 'Melt rate [mm/day]') )
    bins['Temp Atmos [C]'] = ( np.array( bins_raw['Temp Atmos [C]'][1:] ) +
                               np.array( bins_raw['Temp Atmos [C]'][:-1] ) ) / 2.
    bins['Melt rate [mm/day]'] = pd.Timedelta('1D')/pd.Timedelta(_freq) * \
                                 np.array(bins_raw.diff()['Distance [mm]'][1:])
    """
    
    """
    # NEW METHOD: COMPUTE MIDPOINT T AND MELT RATES FIRST AND THEN AVERAGE
    _freq = str(_window)+'H'
    bins = d2.groupby(pd.Grouper(freq=_freq)).mean()
    bins = bins[1:-1] # ends may be missing some data


    # For both methods    
    _T = bins['Temp Atmos [C]']
    _dh = bins['Melt rate [mm/day]'] 
    """

    # My old regression method -- will give a little different answer,
    # and likely more accurate
    _freq = str(_window)+'H'
    print( _freq )
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

    _T = bins['Temp Atmos [C]'][1:-1]
    _dh = np.array(melt_mm_day)

    print("WINDOW: ", end='')
    print(str(_window), end='')
    print(" hr")
    # dz/dt (melt) = MeltFactor * T
    #print("LINEAR, ZERO INTERCEPT")
    #popt, pcov = curve_fit(linfit_noint, T_mean, melt_mm_day)
    #print("Melt Factor =", popt[0], "mm / (degC day)")
    #print("R squared =", calc_r_squared(linfit_noint, T_mean, melt_mm_day, popt))
    #print("")
    print("LINEAR WITH NONZERO INTERCEPT")
    poptI, pcovI = curve_fit(linfit, _T, _dh)
    T0 = poptI[1] / poptI[0] # Temperature intercept; see pen + paper algebra
    print("Melt Factor =", poptI[0], "mm / (degC day)")
    # print("MFint =", poptI[1], "mm / day")
    print("T0 =", T0, "degC")
    R2 = calc_r_squared(linfit, _T, _dh, *poptI)
    print("R squared =", R2)
    print("")
    
    fM_list.append(poptI[0])
    T0_list.append(T0)
    R2_list.append(R2)

    # Melt-factor curve fit
    axf2 = plt.subplot(4,3,ax_i)
    axf2.set_title(str(_window)+'-hour window')
    axf2.plot(_T, _dh, 'ko')#, label='Data')
    _x_fit = np.array( axf2.get_xlim() )
    _y_fit = linfit(_x_fit, *poptI)
    _label = '$f_m$='+'%.1f' %poptI[0]+' mm/(\u00b0C d)\n'+ \
                '$T_0$='+'%.1f' %T0+'\u00b0C\n'+ \
                '$R^2$='+'%0.3f' %R2
    axf2.plot(_x_fit, _y_fit, '.7', label=_label)
    axf2.legend(fontsize=8, loc='upper left')
    # And the subplot letter
    axf2.text( 0.97, 0.03, ascii_lowercase[ax_i-1], fontsize=16,
                fontweight='bold', horizontalalignment='right',
                verticalalignment='bottom', transform=axf2.transAxes )
    ax_i += 1

fig2.supxlabel('Temperature [\u00b0C]', fontsize=16)
fig2.supylabel('Ablation rate [mm/day]', fontsize=16)
fig2.tight_layout()

plt.savefig('ablation_rate_12panel.pdf')

fig = plt.figure(figsize=(6,6))
ax = fig.add_subplot(3, 1, 1)
ax.plot(windows, fM_list, 'k-s')
ax.text( 0.97, 0.03, 'a', fontsize=22,
          fontweight='bold', horizontalalignment='right',
          verticalalignment='bottom', transform=ax.transAxes )
ax.set_ylabel('$f_m$', fontsize=18)
ax = fig.add_subplot(3, 1, 2)
ax.plot(windows, T0_list, 'k-s')
ax.text( 0.97, 0.93, 'b', fontsize=22,
          fontweight='bold', horizontalalignment='right',
          verticalalignment='top', transform=ax.transAxes )
ax.set_ylabel('$T_0$', fontsize=18)
ax = fig.add_subplot(3, 1, 3)
ax.plot(windows, R2_list, 'k-s')
ax.text( 0.97, 0.03, 'c', fontsize=22,
          fontweight='bold', horizontalalignment='right',
          verticalalignment='bottom', transform=ax.transAxes )
ax.set_ylabel('$R^2$', fontsize=18)
ax.set_xlabel('Time-window length [hr]', fontsize=18)
plt.tight_layout()

plt.savefig('ablation_rate_time_window.pdf')

