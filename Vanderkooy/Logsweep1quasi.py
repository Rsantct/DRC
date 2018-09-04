#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
        WORK IN PROGRESSSSSS

    Traslación  a Python del original en Matlab 'Logsweep1quasi.m':
    
    ********************************************************************************
    Logsweep1quasi.m *** Logsweep to get TF, and reflection-free h(t) & H(f)
    the left channel (ref) can be looped to determine the record latency,
    while the right channel (dut) measures the system.
    for most sound cards, the player is delayed wrt the recorder.
    the reference, if not detected, will be the sweep file (sweep).
    
    sweep is padded with zeros, giving 1/4 length clearance at sweep end. 
    the excitation sweep is windowed at both LF and HF (windosweep).
    TF is obtained from DUT/SWEEP, using unwindowed sweep.
    this allows sensible behaviour at LF and HF.
    TF2 is calculated from DUT/REF, nicely normalized but noisy near Nyquist.

    John Vanderkooy, March 2017, Audio Research Group, University of Waterloo
    ********************************************************************************

"""
import sys
from matplotlib import pyplot as plt
from numpy import *
import sounddevice as sd

print '----------------start of program--------------------'
print
print "(i) We use LEFT  CHANNEL as DUT"
print "           RIGHT CHANNEL as REFERENCE"
print

Po  =   2e-5        # SPL reference pressure
c   =   343         # speed of sound
dBclearance = 10    # white space above TF plots
dBspan      = 80    # total scale of TF plots

# ----------------enter important parameters-----------------
sig_frac = 0.5      # fraction of full scale
fs = 48000          # must ensure that Windows settings are the same!
N = 2**17           # make this larger if there is insufficient time clearance

# --- enter value for your soundcard:
## S_dac=-1.22;% UCA202
## S_adc=-1.40;% UCA202 (gain=3 Windows 7). This avoids ADC overload
## S_dac=0.98;% UA-1ex
## S_adc=0.5;% UA-1ex 
## S_dac=2.17*sqrt(2);% UA-25 May have internal +/-5V supply?
## S_adc=+6.0;% UA-25 also high.  
## S_dac=+1.59;% Focusrite 2i2 No, it does not inverts its DAC as article says
## S_adc=+1.16;% Focusrite 2i2 line input gain @ 12:00 o'clock
## S_dac=+1.148;% USB Dual Pre peak volts out for digital Full Scale 
## S_adc=+1.49;% USB Dual Pre JV pot minimum (gain=3, Windows 7)
S_dac=1.0
S_adc=1.0

# ---------------system calibration factor CF for dut--------------------
system_type     = 'electronic'  # 'acoustic', 'electronic', 'level-dependent'
power_amp_gain  = 10            # V/V acoustic
mic_cal         = 0.012         # V/Pa acoustic
mic_preamp_gain = 10.0          # V/V acoustic
Vw              = 1.0           # 2.83 V/watt8ohms acoustic Leave this=1 if not wanted
electronic_gain = 1.0           # total gain in series with electronic system

if system_type == 'acoustic':
    # SPL calibration factor:
    CF = Vw / (power_amp_gain * mic_cal * mic_preamp_gain * Po)
elif system_type == 'electronic':
    CF = 1 / electronic_gain
else:
    # SPL level-dependent
    CF =1 / (sig_frac * mic_cal * mic_preamp_gain * Po)

# ------------- system parameters ----------------------------
Npad    = N/4                       # total zeropad, added to end of play file
Ns      = N - Npad                  # most of array is used for sweep
t  = linspace(0, (N-1)/fs,  N)      # column vector
ts = linspace(0, (Ns-1)/fs, Ns)     # to calculate sweep
print 'fs: ' + str(fs), ' N: '  + str(N), 'duration: ' + str(N/fs)
print 'signal fraction: ' + str(sig_frac), 'time clearance: ' + str( round(N/(4.0*fs),2) )

## (1) -----------------------calculate logsweep-----------------------------
f_start = 5.0               # beginning of turnon half-Hann
f1      = 10.0              # end of turnon half-hann
f2      = 0.91 * fs / 2     # beginning of turnoff half-Hann
f_stop  = fs/2.0            # end of turnoff half-Hann
Ts      = Ns/fs             # sweep duration. Lenght N-Npad samples.
Ls      = Ts / log(f_stop/f_start) # time for frequency to increase by factor e
sweep   = zeros(N)       # initialize
sweep[0:Ns] = sin(2*pi * f_start * Ls * (exp(ts/Ls) - 1) ) #  LOGSWEEP

# ------------------tapered sweep window------------------------------
indexf1 = int(round(fs * Ls * log(f1/f_start) ) + 1)     # end of starting taper
indexf2 = int(round(fs * Ls * log(f2/f_start) ) + 1)     # beginning of ending taper
windo   = ones(N)
# pre-taper
windo[0:indexf1]  = 0.5 * (1 - cos(pi * arange(0, indexf1)    / indexf1     ) )
# post-taper
windo[indexf2:Ns] = 0.5 * (1 + cos(pi * arange(0, Ns-indexf2) / (Ns-indexf2)) )
windo[Ns:N]       = 0        # zeropad end of sweep
windosweep = windo * sweep   # tapered at each end for output to DAC

plt.figure(10)
plt.plot(t, sweep ,'blue')
plt.grid() # % grid on;hold on
plt.plot(t, windosweep, 'red')
plt.xlabel('time[s]')
plt.xlim(0, N/fs); plt.ylim(-1.5, 1.5)       # axis([0 N/fs -1.5 1.5])
plt.legend(['raw sweep', 'windowed sweep'])
plt.title('Sweep')
print 'f_start*Ls: ' + str(round(f_start*Ls, 2)),  'Ls: ' + str(round(Ls,2))
print 'finished sweep generation...'

#plt.show()

## (2)------------data gathering: send out sweep, record system output------%
# antiphase avoids codec midtap modulation:
y = sig_frac * concatenate([windosweep, -windosweep]) 
print 'starting recording...'
## rec = audiorecorder(fs,16,2);
## ply = audioplayer(y,fs,16);
## play(ply); %this should play and allow immediate further execution
## recordblocking(rec,N/fs);% program waits until all samples recorded
## z = getaudiodata(rec,'double');% this retrieves the recorded data
sd.default.samplerate = fs
sd.default.channels = 2
z = sd.playrec(y, blocking=True)
print 'finished recording...'
print 'Some sound cards act strangely. Check carefully!'
maxdBFS_0 = 20 * log10( max(abs( z[:, 0] )) )
maxdBFS_1 = 20 * log10( max(abs( z[:, 1] )) )
if  maxdBFS_0 >= 0:
    print 'Check for ch0 DUT record saturation!', round(maxdBFS_0, 1), 'dBFS'
else:
    print 'No clipping on DUT ch0 :-)', "max:", round(maxdBFS_0, 1), 'dBFS'
if maxdBFS_1 >= 0:
    print 'Check for ch1 REF record saturation!', round(maxdBFS_1, 1), 'dBFS'
else:
    print 'No clipping on REF ch1 :-)', "max:", round(maxdBFS_0, 1), 'dBFS' 
#%----------------------- end of data gathering ---------------------


## %load('Logsweep1data.mat');
ref = z[:, 1]  # we use RIGHT CHANNEL as REFERENCE
dut = z[:, 0]
N = len(dut)
## %save('Logsweep1data.mat','sweep','z','N','fs','sig_frac','CF');
# clear y z; NO es posible en Python

print 'ref_rms_LSBs: ', round(sqrt( 2**30 * sum(ref**2) / N ), 2)
print 'dut_rms_LSBs: ', round(sqrt( 2**30 * sum(dut**2) / N ), 2)


plt.figure(20)
plt.plot(concatenate([t,t]), dut, 'blue', label='raw dut')
plt.plot(concatenate([t,t]), ref + 1.0, 'grey', label='raw ref (offset+1.0)')
plt.grid() # grid on;hold on
plt.xlim(0, N/fs); plt.ylim(-1.5, 2.5)       # axis([0 N/fs -1.5 1.5])
plt.legend()
plt.xlabel('Time [s]')
plt.title('Recorded responses');
plt.show()

sys.exit()

"""
%% 3----------determine record/play delay using crosscorrelation----------%
lags=N/2;% large enough to catch most delays
if max(ref) < 0.1*max(dut) % automatic reference selection
    X=xcorr(sweep,dut,lags);% in case reference is low, use data itself
else
    X=xcorr(sweep,ref,lags);% this uses recorded reference
end
[~,nmax]=max(abs(X));

figure(30)
tl=t-lags/fs;% centred plot
plot(tl(1:N),X(1:N))
grid on
legend('crosscorrelation')
xlabel('time [s]')
title('recorder leads player-----|------recorder lags player')

offset=nmax-lags-1;
disp(['record offset: ' num2str(offset) '  time: ' num2str(offset/fs)])
if abs(offset) > Npad 
    disp('******INSUFFICIENT TIME CLEARANCE!******')
    disp('******INSUFFICIENT TIME CLEARANCE!******')
    disp('******INSUFFICIENT TIME CLEARANCE!******')
end
disp('negative offset means player lags recorder!')

lwindo=ones(N,1);
lwindo(1:indexf1)=0.5*(1-cos(pi*(1:indexf1)/indexf1));% LF pre-taper
lwindosweep=lwindo.*sweep;
% remove play-record delay by shifting computer sweep array
%sweep=circshift(sweep,-offset);
lwindosweep=circshift(lwindosweep,-offset);
%% 4-----------calculate TFs using Frequency Domain ratios----------------%
% all frequency variables are meant to be voltage spectra
%SWEEP=sig_frac*S_dac*fft(sweep);
LWINDOSWEEP=sig_frac*S_dac*fft(lwindosweep);
REF=S_adc*fft(ref);
DUT=CF*S_adc*fft(dut);

TF=DUT./LWINDOSWEEP;% this has good Nyquist behaviour
%TF=DUT./SWEEP;
TF2=DUT./REF;
ft=((1:N/2+1)'-1)*fs/N;
ft(1)=NaN;% this avoids non-positive data in semilogx warning from Octave

top=20*log10(max(abs(TF(2:N/2+1))));% highest dB in plot
figure(100);
semilogx(ft,20*log10(abs(TF(1:N/2+1))),'b');
grid on;
axis([fs/N fs/2 top+dBclearance-dBspan top+dBclearance])
legend('DUT/SWP')
xlabel('frequency [Hz]');ylabel('dB')
title('Transfer Function');

top=20*log10(max(abs(TF2(2:N/2+1))));% highest dB in plot
figure(110);
semilogx(ft,20*log10(abs(TF2(1:N/2+1))),'b');
grid on;
axis([fs/N fs/2 top+dBclearance-dBspan top+dBclearance])
legend('DUT/REF')
xlabel('frequency [Hz]');ylabel('dB')
title('Transfer Function 2');
%% 5---------------load previous file and compare TF ---------------------%
try
    load('old_TF.mat')% loads old_TF
    % this figure will appear when file exists
    top=20*log10(max(abs(TF(2:N/2+1))));% highest dB in plot
    figure(120);
    semilogx(ft,20*log10(abs(TF(1:N/2+1))),'b');
    grid on;hold on
    if length(old_TF) == length(TF)
     semilogx(ft,20*log10(abs(old_TF(1:N/2+1))),'r');
    else
     disp('Different file lengths: do another run')   
    end %if length
    axis([1 fs/2 top+dBclearance-dBspan top+dBclearance])
    legend('new DUT/SWP','old DUT/SWP')
    xlabel('frequency [Hz]');ylabel('dB')
    title('old & new Transfer Functions');
catch
    disp('continuing...')
end %try
old_TF=TF;
save('old_TF.mat','old_TF');% saves current TF file
% all the programs are the same to this point--------------------

%% 6----------------obtain impulse response ------------------------------%
h=real(ifft(TF));% 'real' should not be neccesary
figure(160);% has spike at t near zero, so may spill to negative time
plot(t,h,'b')
grid on;
axis([-.05*N/fs 1.05*N/fs min(h)-0.05*max(h) 1.2*max(h)])
xlabel('time [s]')
ylabel('impulse response')
title('h(t) from DUT/SWP');

hpre=circshift(h,floor(0.002*fs));% precursor view
figure(165);% zoomed, shifted to show precursor
plot(t,hpre,'b')
grid on;
axis([0 .015 min(h)-0.05*max(h) 1.2*max(h)]) % show 15ms for editing
xlabel('time [s]')
ylabel('impulse response')
title('zoomed h(t) with precursor');

%% 7---------Edit h(t) for quasi-anechoic response with miniGUI-----------%
xl=xlim();yl=ylim();
x=xl(1)+0.05*(xl(2)-xl(1));
y=yl(1)+0.1*(yl(2)-yl(1));
text(x,y,'Click-Select Anechoic: start, tzero, end','fontsize',14);
%set(gcf, 'cursor','crosshair')
[X,Y]=ginput(3);% gives X,Y values for 3 mouse clicks
tstart=X(1);nstart=round(tstart*fs);
tzero=X(2);nzero=round(tzero*fs);
tend=X(3);nend=round(tend*fs);
% edit hpre.  We could add a taper-down portion as well, using 4 clicks
hpre=circshift(hpre,-nstart);% start is now at beginning
hpre(nend-nstart+1:N)=0;% remove unwanted tail
hpre=circshift(hpre,-(nzero-nstart));% shift zero time into position
%% 8--------------plot quasi-anechoic TF phase & magnitude----------------%
% plot first half of TF. 2nd half is repeat conjugate even, since h is real
TF=fft(hpre);
oct_width=1/3;% power-preserving relative frequency smoothing for TF
%TF=pwroctsmooth(TF,oct_width);% this takes time in Octave
%-----------------------display phase---------------------------
d=180/pi;
figure(180);
plot(ft,d*angle(TF(1:N/2+1)),'b');
grid on;
axis([0 fs/2 -200 200])
xlabel('frequency [Hz]')
ylabel('phase[deg]')
title('DUT/SWP Quasi-Anechoic TF phase');
%-------------------------display TF to end program---------------------%
top=20*log10(max(abs(TF(2:N/2+1))));% highest dB in plot
figure(185);
semilogx(ft,20*log10(abs(TF(1:N/2+1))),'b');
grid on;hold on;
axis([fs/10000 fs/2 top+dBclearance-dBspan top+dBclearance])
xlabel('frequency [Hz]')
ylabel('SPL [dB]')
title('DUT/SWP Quasi-Anechoic Frequency Response');
disp(' ')
disp(['Frequency resolution [Hz]: ' num2str(round(1/(X(3)-X(2))) )])
disp('-------------------finished--------------------') 
"""
