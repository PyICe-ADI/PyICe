print("\n\nComputing, Please wait...")
import numpy as np
from PyICe import LTC_plot
from PyICe.lab_utils.ordered_pair import ordered_pair
from PyICe.lab_utils.ranges import floatRangeInc
from PyICe.lab_utils.eng_string import eng_string
import random

def dBV(data):
    N = len(data) # For FFT Normalization
    return [20 * np.log10(v) for v in np.abs(data)[:N // 2] * 2 / N] # /N for FFT normalization and only use positive frequencies

def frequencies(BW, N, xscale):
    return np.linspace(0, 2*BW, N)[:N // 2] / xscale

def times(T, time_step):
    return floatRangeInc(0, T, time_step)

dt          = 5e-9                  # Fsample is reciprocal this
xscale      = 1e6                   # Work in MHz
T           = 0.01                  # Record duration (seconds)
RBW         = 1/T                   # Resolution Bandwidth is 1 / Record Duration
N           = round(T/dt)           # Number of samples
Fs          = 1/dt                  # Sampling Frequency
BW          = Fs/2                  # Bandwidth
sin_ampl    = 1                     # 1V Peak
fsin        = 1e6                   # 1MHz - why not?
nsd         = 1e-6                  # Vrms/√Hz
sigma       = nsd * BW**0.5         # Sigma of sampled random is RMS of continuous
t           = times(T, dt)
noise       = []

signal      = sin_ampl * np.sin([2*np.pi*fsin*x for x in t])
[noise.append(random.gauss(mu=0.0, sigma=sigma)) for value in signal]
noise       = np.asarray(noise)
noisysignal = signal + noise
fft_both    = np.fft.fft(noisysignal)
fft_noise   = np.fft.fft(noise)
freqs       = frequencies(BW, N, xscale=xscale)

G0 = LTC_plot.plot( plot_title      = "",
                    plot_name       = "",
                    xaxis_label     = "FREQUENCY (MHz)",
                    yaxis_label     = r"FFT $(dBV_{RMS})$" + f" / √{eng_string(RBW,units='Hz')}",
                    xlims           = (10e3/xscale, BW/xscale),
                    ylims           = (-120, 20),
                    xminor          = 1,
                    xdivs           = BW/10e3,
                    yminor          = 2,
                    ydivs           = 7,
                    logx            = True,
                    logy            = False)

G0.add_trace(   axis            = 1,
                data            = list(zip(freqs, dBV(fft_both))),
                color           = LTC_plot.LT_RED_1,
                marker          = "",
                markersize      = 0,
                linestyle       = "-",
                legend          = "")
                
noise_filtered = ordered_pair(zip(freqs, dBV(fft_noise)))
noise_filtered.smooth_y(window = 11, extrapolation_window = None, iterations = 10)

G0.add_trace(   axis            = 1,
                data            = noise_filtered,
                color           = LTC_plot.LT_BLACK,
                marker          = "",
                markersize      = 0,
                linestyle       = "--",
                legend          = "")
 
note =         f"Sin Cyles: {eng_string(T*fsin)}"
note += "\n" + f"N Samples: {eng_string(N)}"
note += "\n" + f"Sigal RMS: {eng_string(np.sqrt(np.mean(signal**2)), fmt=':.3f', units='Vrms')}"
note += "\n" + f"Sine Peak: {eng_string(np.sqrt(np.mean(signal**2))*2**0.5, fmt=':.3f', units='Vpk')}"
note += "\n" + f"Noise RMS: {eng_string(np.sqrt(np.mean(noise**2)), fmt=':.3f', units='Vrms')}"
note += "\n" + f"Noise NSD: {eng_string(np.sqrt(np.mean(noise**2))/BW**0.5, fmt=':.3f', units='Vrms/√Hz')}"
note += "\n" + f"Bandwidth: {eng_string(BW, units='Hz')}"
note += "\n" + f"Res Bandw: {eng_string(RBW, units='Hz')}"
note += "\n" + f"F Sample : {eng_string(Fs, units='S/s')}"
xpos, ypos = 0.02, 0.98
G0.add_note(note=note, location=[xpos, ypos], use_axes_scale=False, fontsize=10, axis=1, horizontalalignment="left", verticalalignment="top")

Page1 = LTC_plot.Page(rows_x_cols=(1, 1), page_size=None)
Page1.add_plot(G0, position=1, plot_sizex=8, plot_sizey=6)
Page1.create_svg(file_basename = "FFT")
Page1.create_pdf(file_basename = "FFT")
print("Complete!!!")
