#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""      
###############################################################################
## Adaptación a Python del original:
##
##  https://es.mathworks.com/matlabcentral/fileexchange/29187-swept-sine-analysis
##  Developed at Oygo Sound LLC
##
##  (i) Queda comentado el código original Octave y debajo el equivalente Python
##
###############################################################################
"""
import sys
import numpy as np
from scipy import signal
from grpdelay2phase import grpdelay2phase

## function [sweep invsweepfft sweepRate] = synthSweep(T,FS,f1,f2,tail,magSpect)
def synthSweep(T, FS, f1, f2, tail=0, magSpect=None):

    ##
    ## % SYNTHSWEEP Synthesize a logarithmic sine sweep.
    ## %   [sweep invsweepfft sweepRate] = SYNTHSWEEP(T,FS,f1,f2,tail,magSpect)
    ## %   generates a logarithmic sine sweep that starts at frequency f1 (Hz),
    ## %   stops at frequency f2 (Hz) and duration T (sec) at sample rate FS (Hz).
    ## %
    ## %   usePlots indicates whether to show frequency characteristics of the
    ## %   sweep, and the optional magSpect is a vector of length T*FS+1 that
    ## %   indicates an artificial spectral shape for the sweep to have
    ##
    ##      NOTA: me temo que el vector opcional 'magSpect' 
    ##            no se procesa de la forma que se anuncia arriba.
    ##            'usePlots' tampoco se contempla.
    ##            Probablemente sea un asunto inacabado.
    ##            :-/
    ##
    ## %
    ## %   Developed at Oygo Sound LLC
    ## %
    ## %   Equations from Muller and Massarani, "Transfer Function Measurement
    ## %   with Sweeps."
    ##
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%             DO SOME PREPARATORY STUFF
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ##
    ## %%% number of samples / frequency bins
    ## N = real(round(T*FS));
    N = np.real(np.round(T * FS))
    ##
    ## (i) Detecta si no se proporciona un valor para 'tail' y lo deja a 0.
    ##     Se pone por defecto en la declaración de la función Python
    ## if (nargin < 5)
    ##     tail = 0;
    ## end
    ##
    ##
    ## %%% make sure start frequency fits in the first fft bin
    ## f1 = ceil( max(f1, FS/(2*N)) );
    f1 = np.ceil( max(f1, FS/(2.0*N)) )
    ##
    ## %%% set group delay of sweep's starting freq to one full period length of
    ## %%% the starting frequency, or N/200 if thats too small, or N/10 if its too
    ## %%% big
    ## Gd_start = ceil(min(N/10,max(FS/f1, N/200)));
    Gd_start = np.ceil( min( N/10.0, max( FS/f1, N/200.0) ) )
    ##
    ## %%% set fadeout length
    ## postfade = ceil(min(N/10,max(FS/f2,N/200)));
    postfade = int( np.ceil( min( N/10.0, max( FS/f2, N/200.0) ) ) )
    ##
    ## %%% find the length of the actual sweep when its between f1 and f2
    ## Nsweep = N - tail - Gd_start - postfade;
    Nsweep = N - tail - Gd_start - postfade
    ##
    ## %%% length in seconds of the actual sweep
    ## tsweep = Nsweep/FS;
    tsweep = Nsweep/FS
    ##
    ## sweepRate = log2(f2/f1)/tsweep;
    sweepRate = np.log2(f2/f1) / tsweep
    ##
    ## %%% make a frequency vector for calcs (This  has length N+1) )
    ## f = ([0:N]*FS)/(2*N);
    f = np.linspace(0, FS/2.0, N+1)      # es  ODD N+1 con el bin zero
    ##
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%             CALCULATE DESIRED MAGNITUDE
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## %%% create PINK (-10dB per decade, or 1/(sqrt(f)) spectrum
    ## mag = [sqrt(f1./f(1:end))];
    ## mag(1) = mag(2);
    mag = np.sqrt( f1 /f)   # warning porque mag[0] => 'inf', lo solucionamos
    mag[0] = mag[1]         # copiando el valor del bin siguiente.
    ##
    ## %%% Create band pass magnitude to start and stop at desired frequencies
    ## [B1 A1] = butter(2,f1/(FS/2),'high' );  %%% HP at f1
    ## [B2 A2] = butter(2,f2/(FS/2));          %%% LP at f2
    B1, A1 = signal.butter(2, f1/(FS/2.0), 'high')  # LP at f1
    B2, A2 = signal.butter(2, f2/(FS/2.0), 'low')   # LP at f1
    ##
    ## %%% convert filters to freq domain
    ## [H1 W1] = freqz(B1, A1, N+1, FS);        # (i) Matlab calcula las freq físicas
    ## [H2 W2] = freqz(B2, A2, N+1, FS);        #     si se le indica la FS, pero 
    W1, H1 = signal.freqz(B1, A1, worN=(N+1))   #     Scipy no usa la FS. Hay que calcular
    W2, H2 = signal.freqz(B2, A2, worN=(N+1))   #     aparte las freq físicas.
    W1 = W1 / (2*np.pi) * FS                    #  freq normalizadas --> físicas
    W2 = W2 / (2*np.pi) * FS
    ##
    ## %%% multiply mags to get final desired mag spectrum
    ## mag = mag.*abs(H1)'.*abs(H2)';
    mag = mag * np.abs(H1) * np.abs(H2)

    ##
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%            CALCULATE DESIRED GROUP DELAY
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## %%% calc group delay for arbitrary mag spectrum with contant time envelope
    ## %%% from Muller eq's 11 and 12
    ## C = tsweep ./ sum(mag.^2);
    ## Gd = C * cumsum(mag.^2);
    ## Gd = Gd + Gd_start/FS;       % add predelay
    ## Gd = Gd*FS/2;                % convert from secs to samps
    C  = tsweep / np.sum( mag**2 )
    Gd = C * np.cumsum( mag**2 )
    Gd = Gd + Gd_start/FS
    Gd = Gd * FS/2.0

    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%            CALCULATE DESIRED PHASE
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## Se detecta si se proporciona el opcional 'magSpect'
    ## (!)  PERO este código no hace uso de 'magSpect' que se supone que es
    ##      una especie de envelope según se indica al principio.
    ##      Parece ser que procesa la existencia de magSpect de tipo boolean,
    ##      entonces regenera 'mag' de una forma que no entiendo el sentido ¿!?
    ## if (nargin > 5)
    ##     mag = linspace(0.1, 1, length(mag));
    ## end
    if magSpect: 
        mag = np.linspace(0.1, 1, len(mag))
    ##
    ##
    ## %%% integrate group delay to get phase
    ## ph = grpdelay2phase(Gd);
    ph = grpdelay2phase(Gd)
    ##
    ## %%% force the phase at FS/2 to be a multiple of 2pi using Muller eq 10
    ## %%% (but ending with mod 2pi instead of zero ...)
    ## ph = ph - (f/(FS/2)) * mod(ph(end),2*pi);
    ph = ph - (f/(FS/2)) * ( ph[-1] % (2*np.pi) )
    ##
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%             SYNTHESIZE COMPLEX FREQUENCY RESPONSE
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## %%% put mag and phase together in polar form
    ## cplx = mag.*exp(sqrt(-1)*ph);
    cplx = mag * np.exp( (0+1j) * ph )
    ## %%% conjugate, flip, append for WHOLE SPECTRUM
    ## cplx = [ cplx conj( fliplr( cplx(2:end-1 ) ) ) ];
    cplxR = np.conj( np.flipud( cplx[1:-1] ) )              # aquí con flipud
    cplx = np.concatenate( [cplx, cplxR] )
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%             EXTRACT IMPULSE RESPONSE WITH IFFT AND WINDOW
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## ir = real(ifft(cplx));
    ir = np.real( np.fft.ifft( cplx ) )
    ## %%% if this is not really tiny then something is wrong:
    ## err = max(abs(imag(ifft(cplx))));
    err = np.max( np.abs( np.imag ( np.fft.ifft(cplx) ) ) )
    #
    #           octave:66> max(abs(imag(ifft(cplx))))
    #           ans =    1.3636e-19
    #           
    #           In [54]: np.max( np.abs( np.imag ( np.fft.ifft(cplx) ) ) )
    #           Out[54]: 1.0842755210898343e-19
    #           ;-) bien por Numpy
    #
    ##
    ## %%% create window for fade-in and apply
    ## w = hann(2*Gd_start)';
    ## I = 1:Gd_start;
    ## ir(I) = ir(I).*w(I);
    w = np.hanning( 2*Gd_start )
    I = np.arange(Gd_start, dtype=int)  # OjO índices Pythpn desde cero
    ir[I] = ir[I] * w[I]
    ##
    ## %%% create window for fade-out and apply
    ## w = hann(2*postfade)';
    ## I = Gd_start+Nsweep+1:Gd_start+Nsweep+postfade;
    ## ir(I) = ir(I).*w(postfade+1:end);
    w = np.hanning( 2*postfade)
    I = np.arange(Gd_start+Nsweep, Gd_start+Nsweep+postfade, dtype=int)
    ir[I] = ir[I] * w[postfade:]
    ##
    ## %%% force the tail beyond the fadeout to zeros
    ## I = Gd_start+Nsweep+postfade+1:length(ir);
    ## ir(I) = zeros(1,length(I));
    I = np.arange(Gd_start+Nsweep+postfade, len(ir), dtype=int)
    ir[I] = np.zeros(len(I))
    ##
    ## %%% cut the sweep down to its correct size
    ## ir = ir(1:end/2);
    ir = ir[:len(ir)/2]
    ##
    ## %%% normalize
    ## ir = ir/(max(abs(ir(:))));
    ir = ir / max( abs(ir) )
    ##
    ##
    ## %%% get fft of sweep to verify that its okay and to use for inverse
    ## irfft = fft(ir);
    irfft = np.fft.fft(ir)
    ##
    ##
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ## %%%             CREATE INVERSE SPECTRUM
    ## %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    ##
    ## %%% start with the true inverse of the sweep fft
    ## %%% this includes the band-pass filtering, whos inverse could go to
    ## %%% infinity!!!
    ## invirfft = 1./irfft;
    invirfft = 1/irfft
    ##
    ## %%% so we need to re-apply the band pass here to get rid of that
    ## [H1 W1] = freqz(B1,A1,length(irfft),FS,'whole');
    ## [H2 W2] = freqz(B2,A2,length(irfft),FS,'whole');
    ## [H1 W1] = freqz(B1,A1,length(irfft),'whole',FS); # (!!!) Operandos mal colocados
    ## [H2 W2] = freqz(B2,A2,length(irfft),'whole',FS);
    W1, H1 = signal.freqz(B1, A1, worN=len(irfft), whole=True)
    W2, H2 = signal.freqz(B2, A2, worN=len(irfft), whole=True)
    # (i) Matlab calcula las freq físicas si se le indica la FS, pero 
    #     Scipy no usa la FS. Hay que calcular aparte las freq físicas:
    W1 = W1 / (2*np.pi) * FS
    W2 = W2 / (2*np.pi) * FS

    ##
    ## %%% apply band pass filter to inverse magnitude
    ## invirfftmag  = abs(invirfft).*abs(H1)'.*abs(H2)';
    invirfftmag  = abs(invirfft) * abs(H1) * abs(H2)
    ##
    ## %%% get inverse phase
    ## invirfftphase = angle(invirfft);
    invirfftphase = np.angle(invirfft);
    ##
    ## %%% re-synthesis inverse fft in polar form
    ## invirfft = invirfftmag.*exp(sqrt(-1)*invirfftphase);
    invirfft = invirfftmag * np.exp( (0+1j) * invirfftphase)
    ##
    ##
    ## %%% assign outputs
    ## invsweepfft = invirfft;
    ## sweep = ir;
    return sweep, invsweepfft, sweepRate
