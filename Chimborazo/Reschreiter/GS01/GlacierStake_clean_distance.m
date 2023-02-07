%% Clean & Filter: Ablation Stake Distance to Surface Measurements

excel_fil = 'C:\Users\mclau\Documents\Andes_Data\Glacier Data\Reschrieter\GS01\GS01.xlsx';
num = xlsread(excel_fil, 'GS01', '','basic'); %reads in excel file with dates being read in as numbers rather than strings

%Assign date and time to vectors, make correction from excel to matlab
%time, and create datetime array
date = num(:,3);
Cdate = date + 693960; %correct excel date number to matlab date time
time = num(:,4);
Datetime = Cdate + time;

% assign data to variables
temp1 = num(:,6);
RH = num(:,8);
temp2 =num(:,10);
INCy =num(:,14);
INCx=num(:,13);
distance_mm =num(:,15:24);

%% 

% Filter out distance msmts >3 m

Dist_mm = distance_mm;
Dist_mm(distance_mm > 3000) = nan;

% Take mean across rows
Avg = nanmean(Dist_mm,2);

% Get St Dev across rows
StDev = nanstd(Dist_mm,[], 2);
idx = find(StDev> 16);

% assign values in Avg with st dev's above 16 to nan
Avg(idx) = nan;

% Plot Mean against DateTime

figure
plot(Datetime, Avg, 'k.')
ylabel('Distance (mm)')
title('GS01 Distance to Surface')
set(gca, 'XTickLabelRotation', 45);
datetick('x','mm/dd/yy','keepticks');



