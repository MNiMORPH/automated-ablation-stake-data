%% Clean & Filter: Ablation Stake Distance to Surface Measurements

excel_fil = 'C:\Users\mclau\Documents\Andes_Data\Glacier Data\Hans Meyer\GS04\GS04.xlsx';
num = xlsread(excel_fil, 'GS04', '','basic'); %reads in excel file with dates being read in as numbers rather than strings

%Assign date and time to vectors, make correction from excel to matlab
%time, and create datetime array
date = num(:,4);
Cdate = date + 693960; %correct excel date number to matlab date time
time = num(:,5);
Datetime = Cdate + time;

% assign data to variables
temp1 = num(:,7);
RH = num(:,9);
temp2 =num(:,11);
INCy =num(:,15);
INCx=num(:,14);
distance_mm =num(:,16:25);

%% 

% Filter out distance msmts >3 m

Dist_mm = distance_mm;
Dist_mm(distance_mm > 3000) = nan;

% Take mean across rows
Avg = nanmean(Dist_mm,2);

% Get St Dev across rows
StDev = nanstd(Dist_mm,[], 2);
idx = find(StDev>16);

% assign values in Avg with st dev's above 16 to nan
Avg(idx) = nan;

% Plot Mean against DateTime

figure
plot(Datetime, Avg, 'k.')
ylabel('Distance (mm)')
title('GS04 Distance to Surface')
set(gca, 'XTickLabelRotation', 45);
datetick('x','mm/dd/yy','keepticks');



