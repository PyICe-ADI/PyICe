from ..lab_core import *
from PyICe.lab_utils.banners import print_banner
import math, numpy, os, socket

def bit_is_set(value, bit):
    return value & 2**bit == 2**bit
    
class scpi_SA(scpi_instrument):
    ''''''
    #todo abstract methods?
class keysight_e4440a(scpi_SA):
    ''''''
    def __init__(self, interface_visa, minimum_frequency, maximum_frequency, reset=True):
        '''interface_visa'''
        self._base_name = 'Keysight E4440a PSA signal analyzer'
        super(scpi_SA, self).__init__(f"Keysight E4440a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.maximum_frequency=maximum_frequency
        self.minimum_frequency=minimum_frequency
        self.max_power_ch = None
        self.preamp_channel = None
        self.flush_errors()
        if reset:
            self.get_interface().write('*RST') #Skip for collection of manually configured sweep
            self.get_interface().write(':INSTrument:SELect SA') #  BASIC|CDMA|CDMA1XEV|CDMA2K|EDGEGSM|NADC|NFIGURE|PDC|PNOISE|SA|WCDMA|WLAN|DMODULATION|MRECEIVE|TDSCDMA|TDDEMOD|EMC
        # When Auto All is selected:
            # • Resolution BW couples to: Span and Span/RBW
            # • Video BW couples to: Res BW and VBW/RBW
            # • Sweep Time couples to: Res BW; Video BW; Detector; Span and Center 
            # Frequency
            # • CF Step couples to: Span in swept spans, to Res BW in zero span
            # • Attenuation couples to: Ref Level; Ext Amp Gain; Atten Step; Max Mixer Lvl; 
            # and Int Preamp
            # • FFT & Sweep couples to: Res BW and Span
            # • PhNoise Opt (phase noise optimization) couples to: Res BW; Span and FFT & 
            # Sweep sweep type
            # • Detector couples to: marker functions; Avg/VBW Type; Average On Off; Max 
            # Hold and Min Hold
            # • Average Type couples to: the marker functions; Detector and Scale Type
            # • ADC Dither couples to: Sweep Type; Span; Res BW; ADC Ranging and 
            # FFTs/Span
            # • VBW/RBW ratio is set to 1.0
            # • Span/RBW ratio is set to Auto
             # 56 Chapter 2
            # Instrument Functions: A - L
            # Auto Couple
            # Instrument Functions: A - L
            # • Auto Sweep Time is set to Normal
            # • FFT & Sweep is set to Auto:Best Dynamic Range
            # • ADC Ranging is set to Autorange
            # • Marker Count, Gate Time is set to Auto
            # NOTE Marker Trace and Printer have an Auto setting, but are not affected by Auto All.
            # Remote Command: 
            self.get_interface().write(':COUPle ALL') # ALL|NONE
        
    def add_channel_system_preset(self, channel_name):
        '''Remote Command Notes: The SYSTem:PRESet command immediately presets the instrument state 
           to values dependent on the preset type that is currently selected (FACTory, USER, MODE). 
           SYSTem:PRESet does not reset "persistent" functions such as IP address, time/date 
           display style, or auto-alignment state to their factory defaults.
           Use SYSTem:PRESet:PERSistent.
           6.2.11 Reset
           *RST
           This command presets the instrument to a factory defined condition that is 
           appropriate for remote programming operation. In Spectrum Analysis Mode *RST
           is equivalent to performing the commands
           • :SYSTem:PRESet, with preset type set to MODE.
           • *CLS which clears the STATus bits and error queue
           *RST does not change the mode and only resets the parameters for the current 
           mode.
           The :SYSTem:PRESet command is equivalent to a front panel Preset key.
           '''
        new_channel = channel(name=channel_name, write_function=lambda : self.get_interface().write(':SYSTem:PRESet:TYPE FACTory;:SYSTem:PRESet'))
        new_channel._read = lambda: self.get_interface().ask(':SYSTem:PRESet:TYPE?')
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_system_preset.__doc__)
        return self._add_channel(new_channel)

    def _read_trace_data(self, trace_number):
        #ascii. TODO binary?
        # The number of trace points returned is set by [:SENSE]:SWE:POIN (from 101 to 8192).
        # :FORMat[:TRACe][:DATA] ASCii|INTeger,32|REAL,32|REAL,64
        # :FORMat[:TRACe][:DATA]?
        # Remote Command Notes: 
        # Example: FORM REAL,32
        # Corrected Trace Data Types for :TRACe:DATA?<trace_name>
        # Data Type Result
        # ASCii Amplitude Units
        # INTeger,32 (fastest) Internal Units
        # REAL,32 Amplitude Units
        # REAL,64 Amplitude Unit
        resp = self.get_interface().ask(f':TRACE:DATA? TRACE{trace_number}').split(',')
        # return [float(y) for y in resp]
        return numpy.array([float(y) for y in resp])
        
    def _compute_x_axis(self):
        start = float(self.get_interface().ask(f':SENSe:FREQuency:STARt?'))
        stop = float(self.get_interface().ask(f':SENSe:FREQuency:STOP?'))
        point_count = int(self.get_interface().ask(f':SENSe:SWEep:POINts?'))
        if stop > start:
            freqs = numpy.linspace(start=start, stop=stop, num=point_count, endpoint=True) # assume linear sweep
            assert len(freqs) == point_count, f'Swept-span point count error: {len(freqs)} vs. {point_count}.'
            return freqs
        elif start == stop:
            # Zero span
            # Changes the displayed frequency span to zero Hertz. The horizontal axis changes to time rather than 
            # frequency. The input signal that is at the current center frequency is the displayed amplitude. This is a 
            # special operation mode that changes several measurement functions and couplings. The instrument 
            # behavior is similar to an oscilloscope with a frequency selective detector installed in front of the 
            # oscilloscope. See Application Note 150 for more information on how to use this mode.
            
            # 4.8.1 Sweep Time 
                # Selects the length of time in which the spectrum analyzer sweeps the displayed frequency span. In swept 
                # spans, the sweep time varies from 1 millisecond to 2000 seconds plus time for setup which is not 
                # calculated as part of the sweep time. Reducing the sweep time increases the rate of sweeps. In zero span, 
                # the sweep time may be set from 1 μs to 6000 s. In FFT spans, the sweep time is not controlled by the 
                # user, but is an estimate of the time required to make FFT measurements. Sweep time is coupled to RBW 
                # and VBW, so changing those parameters may change the sweep time. When the analyzer has been set to
            time = float(self.get_interface().ask(':SENSe:SWEep:TIME?'))
            times = numpy.linspace(start=0, stop=time, num=point_count, endpoint=True)
            assert len(times) == point_count, f'Zero-span point count error: {len(times)} vs. {point_count}.'
            return times
        else:
            raise Exception(f"PSA _compute_x_axis(): start {start} greater than stop {stop}. Sorry can't sweep backwards.")
            
    def add_channel_ydata(self, channel_name, trace_number=1):
        '''trace data vector'''
        new_channel = channel(channel_name,read_function=lambda trace_number=trace_number: self._read_trace_data(trace_number))
        # self._configured_channels[trace_number]['v_sense'] = new_channel
        new_channel.set_attribute('trace_number', trace_number)
        new_channel.set_attribute('channel_type', 'y_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_ydata.__doc__)
        new_channel._set_type_affinity('PyICeBLOB')
        return self._add_channel(new_channel)
        
    def add_channel_xdata(self, channel_name):
        '''frequency sweep data vector'''
        new_channel = channel(channel_name,read_function=self._compute_x_axis)
        # self._configured_channels[trace_number]['v_sense'] = new_channel
        new_channel.set_attribute('channel_type', 'x_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_xdata.__doc__)
        new_channel._set_type_affinity('PyICeBLOB')
        return self._add_channel(new_channel)
        
    def add_channel_sweep_control(self, channel_name):
        ''''''
        start_channel = channel(f'{channel_name}_start',write_function=lambda freq: self.get_interface().write(f':SENSe:FREQuency:STARt {freq}'))
        # start_channel._set_value(float(self.get_interface().ask(f':SENSe:FREQuency:STARt?')))
        start_channel._read = lambda: float(self.get_interface().ask(':SENSe:FREQuency:STARt?'))
        start_channel.set_attribute('channel_type', 'x_control')
        start_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_control.__doc__)
        self._add_channel(start_channel)
        
        stop_channel = channel(f'{channel_name}_stop',write_function=lambda freq: self.get_interface().write(f':SENSe:FREQuency:STOP {freq}'))
        # stop_channel._set_value(float(self.get_interface().ask(f':SENSe:FREQuency:STOP?')))
        stop_channel._read= lambda: float(self.get_interface().ask(':SENSe:FREQuency:STOP?'))
        stop_channel.set_attribute('channel_type', 'x_control')
        stop_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_control.__doc__)
        self._add_channel(stop_channel)
        
        center_channel = channel(f'{channel_name}_center',write_function=lambda freq: self.get_interface().write(f':SENSe:FREQuency:CENTer {freq}'))
        # center_channel._set_value(float(self.get_interface().ask(':SENSe:FREQuency:CENTer?')))
        center_channel._read = lambda: float(self.get_interface().ask(':SENSe:FREQuency:CENTer?'))
        center_channel.add_preset(0, 'Zero-span (time domain) mode')
        center_channel.set_attribute('channel_type', 'x_control')
        center_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_control.__doc__)
        self._add_channel(center_channel)
        
        span_channel = channel(f'{channel_name}_span',write_function=lambda freq: self.get_interface().write(f':SENSe:FREQuency:SPAN {freq}'))
        # span_channel._set_value(float(self.get_interface().ask(':SENSe:FREQuency:SPAN?')))
        span_channel._read = lambda: float(self.get_interface().ask(':SENSe:FREQuency:SPAN?'))
        span_channel.add_preset(0, 'Zero-span (time domain) mode')
        span_channel.set_attribute('channel_type', 'x_control')
        span_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_control.__doc__)
        self._add_channel(span_channel)
        
        point_count_channel = channel(f'{channel_name}_point_count', write_function=lambda points: self.get_interface().write(f':SENSe:SWEep:POINts {points}'))
        # doesn't quite fit 13 bit integer channel because of +1 offset.
        # point_count_channel._set_value(int(self.get_interface().ask(f':SENSe:SWEep:POINts?')))
        point_count_channel._read = lambda: int(self.get_interface().ask(f':SENSe:SWEep:POINts?'))
        point_count_channel.set_attribute('channel_type', 'x_control')
        point_count_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_control.__doc__)
        point_count_channel.add_preset(8192, "Maximum Setting")
        self._add_channel(point_count_channel)

        return (start_channel, stop_channel, center_channel, span_channel, point_count_channel)
    
    def add_channel_sweep_type(self, channel_name):
        '''2.2.2 FFT & Sweep
            Selects the FFT vs. Sweep key functions.
            NOTE FFT “sweeps” should not be used when making EMI measurements. When an EMI
            detector is selected, Manual:FFT is grayed out. If Manual:FFT is selected first, the EMI
            detectors are grayed out.
            Key Path: Auto Couple
            Remote Command:
            [:SENSe]:SWEep:TYPE AUTO|FFT|SWEep changes the sweep type to FFT or swept, or it lets the
            analyzer automatically choose the type of analysis to use based on current instrument settings.
            [:SENSe]:SWEep:TYPE?
            Example: SWE:TYPE FFT

            2.2.2.1 Auto: Best Dynamic Range
            This function is automatically activated when Auto All is selected. Selecting Auto: Best Dynamic
            Range tells the analyzer to choose between swept and FFT analysis, with a primary goal of optimizing
            the dynamic range. If the dynamic range is very close between swept and FFT, then it chooses the faster
            one.
            While Zero Span is selected, this key is grayed out. The status of the FFT & Swept selection is saved
            when entering zero span and is restored when leaving zero span.
            Key Path: Auto Couple, FFT & Sweep
            Saved State: Saved in Instrument State
            Remote Command:
            [:SENSe]:SWEep:TYPE:AUTO:RULes SPEed|DRANge selects the rules to use when
            SWE:TYPE AUTO is selected. This setting, combined with your current analyzer setup, is used to select
            either FFT or swept mode.
            [:SENSe]:SWEep:TYPE:AUTO:RULes?
            Example: SWEep:TYPE AUTO selects the automatic mode.
            SWE:TYPE:AUTO:RUL DRAN sets the rules for the auto mode to dynamic range.
            2.2.2.2 Auto: Best Speed
            Selecting Auto: Best Speed tells the analyzer to choose between FFT or swept analysis based on the
            fastest analyzer speed. While Zero Span is selected, this key is grayed out. The auto-couple settings are
            kept in memory and are restored whenever leaving Zero Span.
            Key Path: Auto Couple, FFT & Sweep
            Saved State: Saved in Instrument State
            Remote Command:
            [:SENSe]:SWEep:TYPE:AUTO:RULes SPEed|DRANge selects the rules to use when
            SWE:TYPE AUTO is selected. This setting, combined with your current analyzer setup, is used to select
            either FFT or swept mode.
            See “Auto: Best Dynamic Range” on page 57.
            Example: SWEep:TYPE AUTO selects the automatic mode.
            SWE:TYPE:AUTO:RUL SPE sets the rules for the auto mode to speed
            2.2.2.3 Manual: Swept
            Manually selects swept analysis, so it cannot change automatically to FFT.
            While Zero Span is selected, this key is grayed out. The status of the FFT & Swept selection is saved
            when entering zero span and is restored when leaving zero span.
            Key Path: Auto Couple, FFT & Sweep
            Saved State: Saved in Instrument State
            Remote Command:
            Use [:SENSe]:SWEep:TYPE AUTO|FFT|SWEep
            See “FFT & Sweep” on page 56.
            Example: SWE:TYPE SWE
            2.2.2.4 Manual: FFT
            Manually selects FFT analysis, so it cannot change automatically to swept.
            While Zero Span is selected, this key is grayed out. The status of the FFT & Swept selection is saved
            when entering zero span and is restored when leaving zero span.
            TIP Making Gated FFT Measurements With Your PSA
            The process of making a spectrum measurement with FFTs is inherently a “gated”
            process, in that the spectrum is computed from a time record of short duration, much like
            a gate signal in swept-gated analysis.
            The duration of the time record is 1.83 divided by the RBW, within a tolerance of about
            3% for bandwidths up through 1 MHz. Therefore, unlike swept gated analysis, the
            duration of the analysis is fixed by the RBW, not by the gate signal. Because FFT analysis
            is inherently faster than swept analysis, the gated FFT measurements can have better
            frequency resolution (a narrower RBW) than would swept analysis for a given duration of
            the signal to be analyzed.
            FFT analysis in the PSA usually involves making autoranged measurements, and the time
            required to autorange the FFT can be both long and inconsistent. The PSA hardware
            automatically sets the ADC Ranging to Bypass when any trigger, except Free Run is
            selected.
            To make a gated FFT measurement, set the analyzer as follows.
            1. Press Auto Couple, FFT & Sweep to select ManuaL: FFT.
            2. Set the resolution bandwidth to 1.83 divided by the required analysis time, or higher,
            by pressing BW/Avg, Res BW.
            3. Set the trigger source to the desired trigger, by pressing Trig.
            4. Set the trigger delay to observe the signal starting at the required time relative to the
            trigger. Negative delays are possible, by pressing Trig, Trig Delay.
            Key Path: Auto Couple, FFT & Sweep
            Remote Command:
            Use [:SENSe]:SWEep:TYPE AUTO|FFT|SWEep
            See “FFT & Sweep” on page 56.
            Example: SWE:TYPE FFT
            2.2.2.5 FFTs/Span
            Displays and controls the number of FFT segments used to measure the entire Span. This key is
            unavailable (grayed out) unless Sweep Type has been set to FFT. If Sweep Type is set to Auto and FFTs
            are selected, FFTs/Span is still unavailable, and the number of FFTs automatically selected is shown. If
            Sweep Type is set to Manual:FFT, FFTs/Span becomes available. Press FFTs/Span and an integer can
            be entered. The analyzer will try to use the number entered, but it may need to use more due to hardware
            or software limitations.
            An FFT can only be performed over a limited span or segment (also known as the FFT width). Several
            FFT widths may need to be combined to measure the entire span. The “FFT Width” is
            (Span)/(FFTs/Span), and affects the ADC Dither function. (See Auto Couple).
            FFT measurements require that the signal level driving the A/D converter in the IF be small enough to
            avoid overloading, and that the gain that controls that signal level remain fixed during the measurement
            of an entire FFT segment. This constraint can allow higher dynamic ranges in swept mode in some cases,
            but increasing FFTs/Span can restore that dynamic range to FFT measurements, at the expense of losing
            some of the speed advantages of the FFT.
            For example, in pulsed-RF measurements such as radar, it is often possible to make high dynamic range
            measurements with signal levels approaching the compression threshold of the analyzer in swept spans
            (well over 0 dBm), while resolving the spectral components to levels below the maximum IF drive level
            (about –8 dBm at the input mixer). But FFT processing experiences overloads at the maximum IF drive
            level even if the RBW is small enough that no single spectral component exceeds the maximum IF drive
            level. If the user reduces the width of an FFT using the FFTs/Span function, an analog filter is placed
            before the ADC that is about 1.3 times as wide as the FFT segment width. This spreads out the pulsed RF
            in time and reduces the maximum signal level seen by the ADC. Therefore, the input attenuation can be
            reduced and the dynamic range increased without overloading the ADC.
            Further improvement in the dynamic range is possible by changing the ADC gain. In swept analysis in
            the PSA, the gain is normally autoranged such that it can track the signal power as the analyzer sweeps
            through CW-like signals. Since FFT processing cannot autorange the gain within the measurement of a
            single FFT segment, the autoranging advantage is lost for single FFT measurements. But if the segments
            are reduced in width by using more FFTs/Span, then individual FFT segments can use higher gains,
            improving the dynamic range.
            Additional information about selecting FFTs/Span can be found in a product note, "PSA Series Swept
            and FFT Analysis", literature number 5980-3081EN, available on-line:
            http://www.agilent.com
            Key Path: Auto Couple, FFT & Sweep
            State Saved: Saved in Instrument State
            Factory Preset: 1
            Range: 1 to 400000
            Remote Command:
            [:SENSe]:SWEep:FFT:SPAN:RATio <integer>
            [:SENSe]:SWEep:FFT:SPAN:RATio?
            Example: SWE:FFT:SPAN:RAT 20
        '''
        type_channel = channel(f'{channel_name}',write_function=lambda t: self.get_interface().write(f':SENSe:SWEep:TYPE {t}'))
        type_channel._read = lambda: self.get_interface().ask(':SENSe:SWEep:TYPE?')
        type_channel.add_preset('AUTO')
        type_channel.add_preset('FFT')
        type_channel.add_preset('SWEep')
        type_channel.set_attribute('channel_type', 'x_control')
        type_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_type.__doc__)
        self._add_channel(type_channel)
    
        # TODO
        # [:SENSe]:SWEep:FFT:SPAN:RATio <integer>
        # [:SENSe]:SWEep:FFT:SPAN:RATio?
    
        return (type_channel, )
    
    def add_channel_RBW(self, channel_name):
        '''2.3.1 Res BW
            Enables you to select the 3.01 dB resolution bandwidth (RBW) of the analyzer in 10% steps from 1 Hz to 
            3 MHz, plus bandwidths of 4, 5, 6, or 8 MHz. If an unavailable bandwidth is entered with the numeric 
            keypad, the closest available bandwidth is selected.
            Sweep time is coupled to RBW. As the RBW changes, the sweep time (if set to Auto) is changed to 
            maintain amplitude calibration. 
            Video bandwidth (VBW) is coupled to RBW. As the resolution bandwidth changes, the video bandwidth 
            (if set to Auto) changes to maintain the ratio set by VBW/RBW.
            When Res BW is set to Auto, resolution bandwidth is autocoupled to span, except when using the 
            CISPR and MIL detectors (Quasi Peak, EMI Average EMI Peak and MIL Peak). For these detectors, 
            Auto RBW coupling is to the center frequency. The ratio of span to RBW is set by Span/RBW
            (described on page 74). The factory default for this ratio is approximately 106:1 when auto coupled. 
            When Res BW is set to Man, bandwidths are entered by the user, and these bandwidths are used 
            regardless of other analyzer settings.
            NOTE In zero span, the auto/manual function of this key is not applicable. When Res BW 
            (Auto) is selected in non-zero span, any changes to Res BW while in zero span will revert 
            to the Auto value when you return to non-zero span. When Res BW (Man) is selected in 
            non-zero span, any changes to Res BW while in zero span will be maintained when you 
            return to non-zero span.
            NOTE When the Quasi Peak or one of the EMI detectors are selected, the resolution bandwidths 
            available are restricted to the set defined in Table 2-2 on page 83. When the MIL Peak 
            detector is selected, the resolution bandwidths available are restricted to the set defined in 
            Table 2-4 on page 85.
            A # mark appears next to Res BW on the bottom of the analyzer display when it is not coupled. To 
            couple the resolution bandwidth, press Res BW (Auto) or Auto All.
            NOTE For applications that require 6 dB resolution bandwidths, it is possible to use an 
            equivalent 3 dB resolution bandwidth. Because the analyzer has Gaussian RBW, the 
            equivalent 6 dB bandwidth of any RBW filter can be determined using the following 
            formula: 6 dB RBW = 3 dB RBW x 1.414. For example, if a 6 dB RBW of 100 kHz is 
            required, the equivalent 3 dB RBW Filter would be 100 kHz/1.414 = 70.7 kHz. The 
            closest RBW filter for the analyzer that would be used is 68 kHz.'''
        def _set_RBW(bw):
            self.get_interface().write(f':SENSe:BANDwidth:RESolution:AUTO OFF')
            self.get_interface().write(f':SENSe:BANDwidth:RESolution {bw}')
        set_channel = channel(channel_name, write_function=_set_RBW)
        set_channel._set_value(float(self.get_interface().ask(':SENSe:BANDwidth:RESolution?')))
        set_channel._read = lambda: int(float(self.get_interface().ask(':SENSe:BANDwidth:RESolution?')))
        set_channel.set_attribute('channel_type', 'x_control')
        set_channel.set_description(self.get_name() + ': ' + self.add_channel_RBW.__doc__)        
        return self._add_channel(set_channel)

    def add_channel_RBW_auto(self, channel_name):
        '''Tracks the state of the AUTO setting for the resolution bandwidth'''
        new_channel = integer_channel(name=channel_name, size=1, write_function=lambda on : self.get_interface().write(f':SENSe:BANDwidth:RESolution:AUTO {"ON" if on else "OFF"}'))
        new_channel._read = lambda: int(self.get_interface().ask(':SENSe:BANDwidth:RESolution:AUTO?'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_RBW_auto.__doc__)
        return self._add_channel(new_channel)

    def add_channel_VBW(self, channel_name):
        '''2.3.2 Video BW 
Enables you to change the analyzer post-detection filter from 1 Hz to 8 MHz in approximately 10% steps 
between 1 Hz and 3 MHz plus the bandwidths of 4, 5, 6, and 
8 MHz. In addition, a wide-open video filter bandwidth (VBW) may be chosen by selecting 50 MHz. 
Video BW (Auto) selects automatic coupling of the Video BW filter to the resolution bandwidth filter 
using the VBW/RBW ratio set by the VBW/RBW key.
NOTE Sweep Time is coupled to Video Bandwidth (VBW). As the VBW is changed, the sweep 
time (when set to Auto) is changed to maintain amplitude calibration. This occurs 
because of common hardware between the two circuits, even though the Video BW filter 
is not actually “in-circuit” when the detector is set to Average. Because the purpose of the 
average detector and the VBW filter are the same, either can be used to reduce the 
variance of the result.
Although the VBW filter is not “in-circuit” when using the average detector, the Video 
BW key can have an effect on (Auto) sweep time, and is not disabled. In this case, 
reducing the VBW setting increases the sweep time, which increases the averaging time, 
producing a lower-variance trace. 
However, when the EMI Average detector is selected, the Video BW is restricted to 1 Hz 
while the sweep time is set to Auto.
When using the average detector with either Sweep Time set to Man, or in zero span, the 
VBW setting has no effect and is disabled (grayed out).

2.3.3 VBW/RBW 
Selects the ratio between the video and resolution bandwidths in a 1, 3, 10 sequence. A Video bandwidth 
wider than the resolution bandwidth (VBW/RBW ratio > 1.000), provides the best peak measurements of 
signals such as wideband radar pulses. A VBW narrower than the RBW (VBW/RBW ratio < 1.000) 
reduces the variance of noise-like signals and makes spectral components close to the noise floor easier 
to view. The knob and step keys change the ratio in a 1, 3, 10 sequence. If the numbered keys are used, 
the VBW/RBW ratio will be rounded to the nearest 1, 3, or 10 response. Pressing Preset or selecting 
Auto Couple, Auto All sets the ratio to 1.000 X. When VBW/RBW (Auto) is selected, the ratio is 
determined as indicated in Table 2-1 on page 70'''
        def _set_vbw(bw):
            self.get_interface().write(f':SENSe:BANDwidth:VIDeo:AUTO OFF')
            self.get_interface().write(f':SENSe:BANDwidth:VIDeo {bw}')
        set_channel = channel(channel_name,write_function=_set_vbw)
        set_channel._set_value(float(self.get_interface().ask(':SENSe:BANDwidth:VIDeo?')))
        set_channel._read = lambda: int(float(self.get_interface().ask(':SENSe:BANDwidth:VIDeo?')))
        set_channel.add_preset(1e0)
        set_channel.add_preset(1e1)
        set_channel.add_preset(1e2)
        set_channel.add_preset(1e3)
        set_channel.add_preset(1e4)
        set_channel.add_preset(1e5)
        set_channel.add_preset(1e6)
        set_channel.set_attribute('channel_type', 'x_control')
        set_channel.set_description(self.get_name() + ': ' + self.add_channel_VBW.__doc__)
        return self._add_channel(set_channel)
        
    def add_channel_VBW_auto(self, channel_name):
        '''Tracks the state of the AUTO setting for the video bandwidth and the RBW/VBW ratio channel.'''
        auto_channel = integer_channel(name=channel_name, size=1, write_function=lambda on: self.get_interface().write(f':SENSe:BANDwidth:VIDeo:AUTO {"ON" if on else "OFF"}'))
        auto_channel._read = lambda: int(self.get_interface().ask(':SENSe:BANDwidth:VIDeo:AUTO?'))
        auto_channel.set_attribute('channel_type', 'y_control')
        auto_channel.set_description(self.get_name() + ': ' + self.add_channel_VBW_auto.__doc__)
        self._add_channel(auto_channel)
        
        ratio_channel = channel(name=f'{channel_name}_RBW_VBW_ratio', write_function=lambda r: self.get_interface().write(f':SENSe:BANDwidth:VIDeo:RATio {r}'))
        ratio_channel._read = lambda: float(self.get_interface().ask(':SENSe:BANDwidth:VIDeo:RATio?'))
        ratio_channel.set_attribute('channel_type', 'y_control')
        ratio_channel.set_description(self.get_name() + ': ' + self.add_channel_VBW_auto.__doc__)
        self._add_channel(ratio_channel)
        
        auto_ratio_channel = integer_channel(name=f'{channel_name}_RBW_VBW_auto', size=1, write_function=lambda on: self.get_interface().write(f':SENSe:BANDwidth:VIDeo:RATio:AUTO {"ON" if on else "OFF"}'))
        auto_ratio_channel._read = lambda: int(self.get_interface().ask(':SENSe:BANDwidth:VIDeo:RATio:AUTO?'))
        auto_ratio_channel.set_attribute('channel_type', 'y_control')
        auto_ratio_channel.set_description(self.get_name() + ': ' + self.add_channel_VBW_auto.__doc__)
        self._add_channel(auto_ratio_channel)

        return (auto_channel, ratio_channel, auto_ratio_channel)

    def add_channel_average(self, channel_name):
        '''2.3.4 Average
            Initiates a digital averaging routine that averages the trace points in a number of successive sweeps, 
            resulting in trace “smoothing.” You can select the number of sweeps (average number) with the numeric 
            keypad (not the knob or step keys). Increasing the average number further smooths the trace. To select 
            the type of averaging used, press BW/Avg, Avg/VBW Type.
            Averaging restarts when any of the following occurs:
            • a new average number is entered.
            • any measurement related parameter (for example, center frequency) is changed.
            • Restart is pressed.
            • Single Sweep is pressed.
            In single sweep, the specified number of averages is taken, then the sweep stops. In continuous sweep, 
            the specified number of averages is taken, then the averaging continues, with each new sweep averaged 
            in with a weight of and the old average reduced by multiplying it by . 
            

            2.3.5 Avg/VBW Type 
                Displays the functions that enable you to automatically or manually choose one of the following 
                averaging scales: log-power (video), power (RMS), or voltage averaging.
                NOTE When you select log-power averaging, the measurement results are the average of the 
                signal level in logarithmic units (decibels). When you select power average (RMS), all 
                measured results are converted into power units before averaging and filtering operations, 
                and converted back to decibels for displaying. Remember: there can be significant 
                differences between the average of the log of power and the log of the average power.
                The following are the averaging processes within a spectrum analyzer, all of which are affected by this 
                setting:
                • Trace averaging (see BW/Avg) averages signal amplitudes on a trace-to-trace basis.
                • Average detector (see Detector, Average) averages signal amplitudes during the time or frequency 
                interval represented by a particular measurement point.
                • Noise Marker (see Marker Noise) averages signal amplitudes across measurement points to reduce 
                variations for noisy signals.
                • VBW filtering adds video filtering which is a form of averaging of the video signal.
                When manual is selected, the type is shown on the left side of the display with a #. When auto is 
                selected, the analyzer chooses the type of averaging. When one of the average types is selected manually, 
                the analyzer uses that type regardless of other analyzer settings, and sets Avg/VBW Type to Man.'''
        def _write_avg(count):
            if count == 0:
                self.get_interface().write(':SENSe:AVERage:STATe OFF')
                # [:SENSe]:AVERage[:STATe]?
                # [:SENSe]:AVERage:COUNt <integer>
                # [:SENSe]:AVERage:COUNt?
            elif count > 0:
                self.get_interface().write(f':SENSe:AVERage:COUNt {count}')
                self.get_interface().write(':SENSe:AVERage:STATe ON')
        count_channel = channel(f'{channel_name}_count',write_function=_write_avg)
        count_channel.set_attribute('channel_type', 'y_control')
        
        def _read_avg():
            resp = int(self.get_interface().ask(':SENSe:AVERage:STATe?'))
            if resp:
                return int(self.get_interface().ask(':SENSe:AVERage:COUNt?'))
            else:
                return 0
        count_channel._read = _read_avg
        count_channel.add_preset(0)
        count_channel.add_preset(10)
        count_channel.add_preset(100)
        count_channel.add_preset(8192)
        count_channel.set_description(self.get_name() + ': ' + self.add_channel_average.__doc__)
        self._add_channel(count_channel)

        type_channel = channel(f'{channel_name}_type',write_function=lambda typ: self.get_interface().write(f':SENSe:AVERage:TYPE {typ}')) 
            # [:SENSe]:AVERage:TYPE:AUTO OFF|ON|0|1
            # [:SENSe]:AVERage:TYPE:AUTO?'))
        type_channel.set_attribute('channel_type', 'y_control')
        type_channel._read = lambda: self.get_interface().ask(':SENSe:AVERage:TYPE?')
        # type_channel.add_preset('Auto') # TODO, readback
        type_channel.add_preset('RMS')
        type_channel.add_preset('LOG')
        type_channel.add_preset('SCALar')
        type_channel.set_description(self.get_name() + ': ' + self.add_channel_average.__doc__)
        self._add_channel(type_channel)
        return (count_channel, type_channel)
        
    def all_markers_off(self):
        self.get_interface().write(f':CALCulate:MARKer1:STATe OFF')
        self.get_interface().write(f':CALCulate:MARKer2:STATe OFF')
        self.get_interface().write(f':CALCulate:MARKer3:STATe OFF')
        self.get_interface().write(f':CALCulate:MARKer4:STATe OFF')
        
    def flush_errors(self):
        while self.get_interface().ask(':SYSTem:ERROr?') != '+0,"No error"':
            pass

    def add_channel_detector(self, channel_name):
        '''2.4.1 Detector
This menu allows you to select a specific type of detector, or choose Auto to let the instrument select the 
appropriate detector for a particular measurement.
When discussing detectors, it is important to understand the concept of a trace “bucket.” For every trace 
point displayed in swept and zero-span analysis, there is a finite time during which the data for that point 
is collected. The analyzer has the ability to look at all of the data collected during that time and present a 
single point of trace data based on the detector mode. We call the interval during which the data for that 
trace point is being collected, the “bucket.” The data is sampled rapidly enough within a “bucket” that it 
must be reduced in some fashion to yield a single data point for each bucket. There are a number of ways 
to do this and which way is used depends on the detector selected. Details on how each detector does this 
are presented below.
In FFT analysis, the bucket represents just a frequency interval. The detector in an FFT mode determines 
the relationship between the spectrum computed by the FFT and the single data point displayed for the 
bucket.
When the Detector choice is Auto, the detector selected depends on marker functions, trace functions, 
and the trace averaging function. 
See “Auto Rules For Detector Selection” on page 80 for information on the Auto detector selection.
When you manually select a detector (instead of selecting Auto), that detector is used regardless of other 
analyzer settings.
The detector choices are:
• Normal − displays the peak of CW-like signals and maximums and minimums of noise-like signals. 
• Average − displays the average of the signal within the bucket. The averaging method depends upon 
Avg Type selection (voltage, power or log scales).
• Peak − displays the maximum of the signal within the bucket.
• Sample − displays the instantaneous level of the signal at the center of the bucket represented by 
each display point.
• Negative Peak − displays the minimum of the signal within the bucket.
• Quasi Peak − a fast-rise, slow-fall detector used in making CISPR compliant EMI measurements.
• EMI Average − displays the instantaneous level of the signal at the center of the bucket, just like the 
sample detector. It also changes the auto coupling of VBW, RBW and Avg/VBW Type and the set of 
available RBWs. This detector is used in making CISPR-compliant measurements.
• EMI Peak − the same as the Peak detector but uses CISPR related bandwidths.
• MIL Peak − the same as the Peak detector but uses MIL related bandwidths.
Because they may not find the true peak of a spectral component, neither average nor sample detectors 
measure amplitudes of CW signals as accurately as peak or normal, but they do measure noise without 
the biases of peak detection.
The detector in use is indicated on the left side of the display, just below Reference level. The 
 78 Chapter 2
Instrument Functions: A - L
Det/Demod
Instrument Functions: A - L
designators are: 
• Norm − Normal detector
• Avg − Average detector
• Peak − Peak detector
• Samp − Sample detector
• NPk − Negative Peak detector
• EmiQP − Quasi Peak detector
• EmiAv − ΕMI Average detector
• EmiPk − Peak detector with CISPR bandwidths
• MILPk − Peak detector with MIL bandwidths
If the detector has been manually selected, a # appears next to it.'''
        new_channel = channel(channel_name,write_function=lambda det_type: self.get_interface().write(f':SENSe:DETector:FUNCtion {det_type}'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel._set_value(self.get_interface().ask(f':SENSe:DETector:FUNCtion?'))
        # new_channe._read = lambda: self.get_interface().ask(f':SENSe:DETector:FUNCtion?')
        new_channel.add_preset('NORMal', 'Normal')
        new_channel.add_preset('AVERage', 'Average')
        new_channel.add_preset('POSitive', 'Peak')
        new_channel.add_preset('SAMPle', 'Sample')
        new_channel.add_preset('NEGative', 'Negative peak')
        new_channel.add_preset('QPEak', 'Quasi Peak')
        new_channel.add_preset('EAVerage', 'EMI Average')
        new_channel.add_preset('EPOSitive', 'EMI Peak')
        new_channel.add_preset('MPOSitive', 'MIL Peak')
        new_channel.add_preset('RMS', 'RMS (alias). The query returns a name that corresponds to the detector mode. The RMS selection is an alias which selects the Average detector and Power Averaging. Therefore, if RMS has been selected, the query will return the AVER string.')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_detector.__doc__)
        return self._add_channel(new_channel)

    def add_channel_attenuator(self, channel_name):
        '''Allows you to adjust the input attenuation. Press Atten Step to set the attenuation step so that attenuation 
        will change in 2 dB or 10 dB increments. The analyzer input attenuator reduces the power level of the 
        input signal delivered to the input mixer. If set manually, the attenuator is recoupled when Attenuation 
        (Auto) is selected. To enter a value below 6 dB, you must use the front-panel numeric keypad.
        Attenuation is coupled to Reference Level, so adjusting the Reference Level may change the 
        Attenuation. The analyzer selects an Attenuation setting that is as small as possible while keeping the 
        Ref Level at or below the Max Mixer Lvl setting. The current value is indicated by Atten at the top of 
        the display. A # appears in front of Atten when Attenuation (Man) is selected.
        CAUTION To prevent damage to the input mixer, do not exceed a power level of +30 dBm at the 
        input.
        
        To prevent signal compression, keep the power at the input mixer below 
        0 dBm (10 MHz - 200 MHz), below 3 dBm (200 MHz - 6.6 GHz), and below –2 dBm 
        (6.6 GHz - 50.0 GHz). With the attenuator set to Auto, a signal at or below the reference 
        level results in a mixer level at or below −10 dBm'''
        def _set_attenuator(value):
            if value in range(0,72,2):
                self.get_interface().write(':SENSe:POWer:RF:ATTenuation:AUTO OFF')
                self.get_interface().write(f':SENSe:POWer:RF:ATTenuation {value}')
            else:
                raise Exception(f"\nPSA: Sorry, can't set attentuator level to {value}.\nValue must be a multiple of 2 between 0dB and 70dB inclusive.")
        self.attenuator_channel = channel(channel_name, write_function=_set_attenuator)
        self.attenuator_channel.set_attribute('channel_type', 'y_control')
        self.attenuator_channel.set_description(self.get_name() + ': ' + self.add_channel_attenuator.__doc__)
        self.attenuator_channel._set_value(int(float(self.get_interface().ask(f':SENSe:POWer:RF:ATTenuation?'))))
        self.attenuator_channel._read = lambda: int(float(self.get_interface().ask(f':SENSe:POWer:RF:ATTenuation?')))
        return self._add_channel(self.attenuator_channel)
        
    def add_channel_attenuator_auto(self, channel_name):
        '''Tracks the state of the AUTO setting for the front end attenuators'''
        new_channel = integer_channel(name=channel_name, size=1, write_function=lambda on : self.get_interface().write(f':SENSe:POWer:RF:ATTenuation:AUTO {"ON" if on else "OFF"}'))
        new_channel._read = lambda: int(self.get_interface().ask(':SENSe:POWer:RF:ATTenuation:AUTO?'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_attenuator_auto.__doc__)
        return self._add_channel(new_channel)

    def add_channel_max_power(self, channel_name):
        '''To prevent signal compression, keep the power at the input mixer below 
        0 dBm (10 MHz - 200 MHz), below 3 dBm (200 MHz - 6.6 GHz), and below –2 dBm 
        (6.6 GHz - 50.0 GHz). With the attenuator set to Auto, a signal at or below the reference 
        level results in a mixer level at or below −10 dBm.
        
        The Low Band Preamp (1DS) has a nominal gain of 30 dB and contains two 
        electro-mechanical coax switches. The frequency range of the preamp is 
        100 kHz to 3 GHz. The input signal level at the preamp should not 
        exceed −30 dBm.
        ************************************************************************************************
        * This is a proxy for the attenuator level so we don't have to always be computing it by hand  *
        ************************************************************************************************'''
        limits = [  
                    {"MINFREQ": 6.6e12, "MAXFREQ": 50e12,   "POWER_dBm": -2},
                    {"MINFREQ": 200e6,  "MAXFREQ": 6.6e12,  "POWER_dBm": 3},
                    {"MINFREQ": 0,      "MAXFREQ": 200e6,   "POWER_dBm": 0},
                 ]
        def pmax_of_freqs():
            if self.maximum_frequency > 50e12:
                raise Exception(f"PSA: You said you wanted to run the PSA at {self.maximum_frequency}Hz. The PSA series signal analyzer isn't rated to go above 50GHz.")
            if self.preamp_channel is None:
                raise Exception("Now what? Channel isn't necessarily defined! Should this just read the scpi setting directly????")
            elif self.preamp_channel.read():
                pmax = -30#dBm
            else:
                pmax = 3 # Default to worst case for a range that extends wider than one of the given ranges? TODO default to the worset case of the 2 ranges that are specified?
                for limit in limits:
                    if self.minimum_frequency >= limit["MINFREQ"] and self.maximum_frequency < limit["MAXFREQ"]:
                        pmax = limit["POWER_dBm"]                    
            print(f"Setting pmax to {pmax}. Preamp is {'ON' if self.preamp_channel.read() else 'OFF'}.")
            return pmax
        def nearest_even_value(value):
            return math.ceil(value / 2) * 2
        def attenuation_level(pmax, power_in):
            print(f"Returning attenuation level of {nearest_even_value(max(min(power_in - pmax, 70), 0))}")
            return nearest_even_value(max(min(power_in - pmax, 70), 0))

        self.max_power_ch = channel(channel_name, write_function=lambda value: self.attenuator_channel.write(attenuation_level(pmax_of_freqs(), value)))
        self.max_power_ch.set_attribute('channel_type', 'y_control')
        return self._add_channel(self.max_power_ch)

    def add_channel_preamp(self, channel_name):
        '''(Options 1DS and 110 only.) Turns the internal preamp on and off. Option 1DS preamp functions over a 
frequency range of 100 kHz to 3 GHz. Option 110 preamp functions over a frequency range of 100 kHz 
to 50 GHz. When the preamp is on, an automatic adjustment compensates for the gain of the preamp so 
that the displayed amplitude readings still accurately reflect the value at the analyzer input connector. 
The Option 1DS preamp is switched off for frequencies above 3 GHz, and the correction is not applied, 
even though the PA annotation remains on screen. For signal frequencies below 100 kHz, the preamp is 
not automatically switched out, but signal amplitude roll-off occurs even in the “DC” setting of the RF 
Coupling control.
The gain of the preamp is nominally 30 dB. This functionality is not available when using external 
mixing.'''
        self.preamp_channel = integer_channel(channel_name, size=1, write_function=lambda on: self.get_interface().write(f':SENSe:POWer:RF:GAIN:STATe {"ON" if on else "OFF"}'))
        self.preamp_channel._read = lambda: int(self.get_interface().ask(':SENSe:POWer:RF:GAIN:STATe?'))
        self.preamp_channel.set_attribute('channel_type', 'y_control')
        self.preamp_channel.set_description(self.get_name() + ': ' + self.add_channel_preamp.__doc__)
        def maxp_atten_cb(ch, val):
            #preamp setting change. Force attenuator recomputation.
            if self.max_power_ch is not None and self.max_power_ch.read() is not None:
                self.max_power_ch.write(self.max_power_ch.read())
        self.preamp_channel.add_write_callback(maxp_atten_cb)
        return self._add_channel(self.preamp_channel)
        
    # def add_chanel_peak_marker(self, channel_name, marker_number=1, trace_number=1):
    #
    # TODO NEEDS Work, Doesn't service NEXT command, etc.
    #
        # '''spot measurmeent scalar at given frequency
        # threshold and excursion thresholds measured in dBm, for now. Could be changed.
        # '''
        # #handling of marker mode is a little crude. TODO - keep track of already used marker and trace numbers better.
        # self.get_interface().write(f':CALCulate:MARKer{marker_number}:STATe ON') # OFF|ON|0|1
        # self.get_interface().write(f':CALCulate:MARKer{marker_number}:TRACe {trace_number}') # Puts the marker on the specified trace and turns Auto OFF for that marker.
        # self.get_interface().write(f':CALCulate:MARKer{marker_number}:MODE POSition') # POSition|DELTa|BAND|SPAN|OFF
        # self.get_interface().write(f':CALCulate:MARKer{marker_number}:FUNCtion OFF') # BPOWer|NOISe|OFF
        # self.get_interface().write(f':CALCulate:MARKer:PEAK{marker_number}:SEARch:MODE MAXimum') # PARameter|MAXimum
        # self.get_interface().write(f':CALCulate:MARKer{marker_number}:CPEak:STATe ON') # OFF|ON|0|1 (or :CALCulate:MARKer[1]|2|3|4:MAXimum)
        
        # search_position_channel = channel(f'{channel_name}_peak_search',write_function=lambda freq, marker_number=marker_number: self.get_interface().write(f':CALCulate:MARKer{marker_number}:X {freq}'))
        # search_position_channel.set_attribute('channel_type', 'meas_control')
        # search_position_channel.set_description(self.get_name() + ': ' + self.add_chanel_peak_marker.__doc__)
        # self._add_channel(search_position_channel)
        
        # peak_position_channel = channel(f'{channel_name}_peak_find',read_function=lambda marker_number=marker_number: self.get_interface().ask(f':CALCulate:MARKer{marker_number}:X?'))
        # peak_position_channel = channel(f'{channel_name}_peak_frequency',read_function=lambda marker_number=marker_number: self.get_interface().ask(f':CALCulate:MARKer{marker_number}:X?'))
        # peak_position_channel.set_attribute('channel_type', 'x_data')
        # peak_position_channel.set_description(self.get_name() + ': ' + self.add_chanel_peak_marker.__doc__)
        # self._add_channel(peak_position_channel)
        
        # amplitude_channel = channel(f'{channel_name}_peak_amplitude',read_function=lambda marker_number=marker_number: float(self.get_interface().ask(f':CALCulate:MARKer{marker_number}:Y?')))
        # amplitude_channel.set_attribute('channel_type', 'y_data')
        # amplitude_channel.set_description(self.get_name() + ': ' + self.add_chanel_peak_marker.__doc__)
        # self._add_channel(amplitude_channel)
        
        # search_threshold_channel = channel(f'{channel_name}_peak_search_threshold',write_function=lambda ampl, marker_number=marker_number: self.get_interface().write(f':CALCulate:MARKer{marker_number}:PEAK:THReshold {ampl}'))
        # search_threshold_channel.set_attribute('channel_type', 'meas_control')
        # search_threshold_channel._set_value(float(self.get_interface().ask(f':CALCulate:MARKer{marker_number}:PEAK:THReshold?')))
        # search_threshold_channel.set_description(self.get_name() + ': ' + self.add_chanel_peak_marker.__doc__)
        # self._add_channel(search_threshold_channel)
        
        # search_excursion_channel = channel(f'{channel_name}_peak_search_excursion',write_function=lambda rel_ampl, marker_number=marker_number: self.get_interface().write(f':CALCulate:MARKer{marker_number}:PEAK:EXCursion {rel_ampl}'))
        # search_excursion_channel.set_attribute('channel_type', 'meas_control')
        # search_excursion_channel._set_value(float(self.get_interface().ask(f':CALCulate:MARKer{marker_number}:PEAK:EXCursion?')))
        # search_excursion_channel.set_description(self.get_name() + ': ' + self.add_chanel_peak_marker.__doc__)
        # self._add_channel(search_excursion_channel)
        
        # return (peak_position_channel, amplitude_channel, search_position_channel, search_threshold_channel, search_excursion_channel)
        
    def add_channel_max_marker(self, channel_name, marker_number=1, trace_number=1):
        '''Spot measurment scalar finds the maximum value on the screen.
        This instrument is very screen memory centric.'''
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:STATe ON') # OFF|ON|0|1
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:TRACe {trace_number}') # Puts the marker on the specified trace and turns Auto OFF for that marker.
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:MODE POSition') # POSition|DELTa|BAND|SPAN|OFF
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:FUNCtion OFF') # BPOWer|NOISe|OFF
        
        def _single_abort_trigger_wait(run_mode):
            if run_mode == 'FIND':
                self.get_interface().write(f':CALCulate:MARKer{marker_number}:MAX')
            elif run_mode == 'STDBY':
                pass
            else:
                raise Exception(f'''PSA Max Marker Trigger, sorry don't know how to: {run_mode}. Try "FIND"?''')

        def _single_write_cb(ch, v):
            if v == 'FIND':
                ch._set_value('STDBY')

        trigger_channel = channel(f'{channel_name}_trigger', write_function = _single_abort_trigger_wait)
        trigger_channel.add_preset('FIND')
        trigger_channel.add_preset('STDBY')
        trigger_channel.add_write_callback(_single_write_cb)
        self._add_channel(trigger_channel)
        
        frequency_channel = channel(f'{channel_name}_frequency', read_function=lambda marker_number=marker_number: self.get_interface().ask(f':CALCulate:MARKer{marker_number}:X?'))
        frequency_channel.set_attribute('channel_type', 'x_data')
        frequency_channel.set_description(self.get_name() + ': ' + self.add_channel_max_marker.__doc__)
        self._add_channel(frequency_channel)
        
        amplitude_channel = channel(f'{channel_name}_amplitude', read_function=lambda marker_number=marker_number: float(self.get_interface().ask(f':CALCulate:MARKer{marker_number}:Y?')))
        amplitude_channel.set_attribute('channel_type', 'y_data')
        amplitude_channel.set_description(self.get_name() + ': ' + self.add_channel_max_marker.__doc__)
        self._add_channel(amplitude_channel)
        
        return (trigger_channel, frequency_channel, amplitude_channel)
        
    def add_channel_noise_marker(self, channel_name, marker_number=1, trace_number=1):
        '''spot measurmeent scalar at given frequency
        
            Activates a noise marker for the selected marker. If the selected marker is off it is turned on and located 
            at the center of the display. Reads out the average noise level, normalized to a 1 Hz noise power 
            bandwidth, around the active marker. The noise marker averages 5% of the trace data values, centered on 
            the location of the marker. 
            The data displayed (if the marker is in Normal mode) is the noise density around the marker. The value 
            readout is followed by “(1 Hz)” to remind you that display is normalized to a one Hz bandwidth.
            
            To guarantee accurate data for noise-like signals, a correction for equivalent noise bandwidth is made by 
            the analyzer. The Marker Noise function accuracy is best when the detector is set to Average or 
            Sample, because neither of these detectors will peak-bias the noise. The trade off between sweep time 
            and variance of the result is best when Avg/VBW Type is set to Power Averaging. Auto coupling, 
            therefore, normally chooses the Average detector and Power Averaging. Though the Marker Noise 
            function works with all settings of detector and Avg/VBW Type, using the positive or negative peak 
            detectors gives less accurate measurement results
        '''
        #handling of marker mode is a little crude. TODO - keep track of already used marker and trace numbers better.
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:STATe ON') # OFF|ON|0|1
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:TRACe {trace_number}') # Puts the marker on the specified trace and turns Auto OFF for that marker.
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:MODE POSition') # POSition|DELTa|BAND|SPAN|OFF
        self.get_interface().write(f':CALCulate:MARKer{marker_number}:FUNCtion NOISe') # BPOWer|NOISe|OFF
        position_channel = channel(f'{channel_name}_frequency',write_function=lambda freq, marker_number=marker_number: self.get_interface().write(f':CALCulate:MARKer{marker_number}:X {freq}'))
        # todo - readback in case somebody touches front panel???
        position_channel.set_attribute('channel_type', 'meas_control')
        position_channel.set_description(self.get_name() + ': ' + self.add_channel_noise_marker.__doc__)
        self._add_channel(position_channel)
        
        amplitude_channel = channel(f'{channel_name}_amplitude',read_function=lambda marker_number=marker_number: float(self.get_interface().ask(f':CALCulate:MARKer{marker_number}:Y?')))
        amplitude_channel.set_attribute('channel_type', 'y_data')
        amplitude_channel.set_description(self.get_name() + ': ' + self.add_channel_noise_marker.__doc__)
        self._add_channel(amplitude_channel)
        return (position_channel, amplitude_channel)
        
    def add_channel_bandpower_marker(self, channel_name, marker_number=1):
        '''3.2.3 Band/Intvl Power
            Measures the power in a bandwidth (non-zero span) or time interval (zero span) specified by the user. If 
            no marker is on, this key activates the delta pair marker mode. If the detector mode is set to Auto, the 
            average detector is selected. If the Avg/VBW type is set to Auto, Power Averaging is selected, other 
            choices of detector and Avg/VBW type will usually cause measurement inaccuracy. The active marker 
            pair indicate the edges of the band. Only Delta Pair and Span Pair marker control modes can be used 
            while in this function, selecting any other mode (for example, Normal or Delta) turns off this function'''
        #TODO
        # :CALCulate:MARKer[1]|2|3|4:FUNCtion BPOWer|NOISe|OFF
        # :CALCulate:MARKer[1]|2|3|4:FUNCtion?
        
        # :CALCulate:MARKer[1]|2|3|4:TRACe 1|2|3  Puts the marker on the specified trace and turns Auto OFF for that marker.   :CALCulate:MARKer[1]|2|3|4:TRACe
        # :CALCulate:MARKer[1]|2|3|4:MODE POSition|DELTa|BAND|SPAN|OFF :CALCulate:MARKer[1]|2|3|4:MODE?
        # :CALCulate:MARKer[1]|2|3|4:X <param> Sets the marker X position to a specified point on the X axis in the current X-axis units (frequency or time). If the frequency or time chosen would place the marker off screen, the marker will be placed at the left or right side of the display, on the trace. This command has no effect if the marker is OFF.
        # :CALCulate:MARKer[1]|2|3|4:X?
        # :CALCulate:MARKer[1]|2|3|4:STATe OFF|ON|0|1
        # :CALCulate:MARKer[1]|2|3|4:STATe?
        
    def add_channel_trigger(self, channel_name):
        ''''''
        def _single_abort_trigger_wait(run_mode):
            if run_mode == 'Single':
                self.get_interface().write(f':INITiate:CONTinuous OFF')
            elif run_mode == 'Continuous':
                self.get_interface().write(f':INITiate:CONTinuous ON')
            else:
                raise Exception(f'Unknown trigger/run mode {run_mode}. Expected "Single" or "Continuous"')
            # self.get_interface().write(f':ABORt') #This restarts the sweep!
            # time.sleep(0.1)
            # Bit Condition Operation
                # 0 Calibrating The instrument is busy executing its automatic alignment process
                # 3 Sweeping The instrument is busy taking a sweep.
                # 5 Waiting for trigger The instrument is waiting for the trigger conditions to be met, then it will trigger a sweep or measurement.
            # status = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
            # assert not status, f'Expected status 0 (idle). Got {status} ({type(status)})'
            # while status != 2**5:
                # print(f'Expected status 2**5. Got {status} ({type(status)})')
                # status = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
            expected_time = float(self.get_interface().ask(':SENSe:SWEep:TIME?'))
            self.get_interface().write(f':INITiate:IMMediate') #probably not right now that we have trigger source controls coming....
            print(f'{datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")} trigger time. Expected sweep time {expected_time}s.')
            if run_mode == 'Continuous':
                return
            status = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
            while status:
                time.sleep(0.1) #?!?
                status = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
                # print(f'Waiting for status 0 (idle). Got {status} ({type(status)})')
        def _single_write_cb(ch, v):
            # print(f'{ch.get_name()} writtent to {v}')
            if v == 'Single':
                ch._set_value('Stop')
        mode_channel = channel(f'{channel_name}_mode',write_function=_single_abort_trigger_wait)
        # mode_channel._read = lambda: None #Don't cache value that only has side-effect value
        mode_channel.add_preset('Single')
        mode_channel.add_preset('Continuous')
        mode_channel.add_write_callback(_single_write_cb)
        mode_channel.set_attribute('channel_type', 'trig_control')
        mode_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(mode_channel)
        
        
        source_channel = channel(f'{channel_name}_source',write_function=lambda s: self.get_interface().write(':TRIGger:SEQuence:SOURce {s}')) # IMMediate|VIDeo|LINE|EXTernal[1]|EXTernal2|RFBurst
        source_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:SOURce?')
        source_channel.add_preset('IMMediate', 'Free Run triggering')
        source_channel.add_preset('VIDeo', '''Triggers on the video signal level
        4.11.2 Video
            Activates the trigger condition that allows the next sweep to start if the detected RF envelope voltage
            crosses a level set by the video trigger level. When Video is pressed, a line appears on the display. The
            analyzer triggers when the input signal exceeds the trigger level at the left edge of the display. You can
            change the trigger level using the step keys, the knob, or the numeric keypad. The line remains as long as
            video trigger is the trigger type.
            Key Path:. Trig
            Dependencies/Couplings:. Trigger Delay adjustment is not available with Video triggering.
            Video triggering is not available when the detector type is Average. Marker Functions
            that set the detector to average (such as Marker Noise or Band/Intvl Power) are not
            available when the video trigger is on.
            This function is not available when the Resolution Bandwidth is less than 1 kHz. If a
            Resolution Bandwidth less than 1 kHz is selected while in Video Trigger mode, the
            Trigger mode changes to Free Run.
            Factory Preset:. –25 dBm
            Range:. Using logarithmic scale: from 10 display divisions below the reference level, up to the
            reference level
            Using linear scale: from 100 dB below the reference level, up to the reference level
            For more information, see “Scale Type” on page 38.''')
        source_channel.add_preset('LINE', 'Line – Triggers on the power line signal')
        source_channel.add_preset('EXTernal1', 'External Front – Enables you to trigger on an externally connected trigger source')
        source_channel.add_preset('EXTernal2', 'External Rear – Enables you to trigger on an externally connected trigger source')
        source_channel.add_preset('RFBurst', 'Allows the analyzer to be triggered by an RF burst envelope signal.')
        source_channel.set_attribute('channel_type', 'trig_control')
        source_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(source_channel)
        # Remote Command Notes: Other trigger-related commands are found in the INITiate and ABORt subsystems.

        level_channel = channel(f'{channel_name}_video_level',write_function=lambda l: self.get_interface().write(':TRIGger:SEQuence:VIDeo:LEVel {l}'))
        level_channel._read = lambda: float(self.get_interface().ask(':TRIGger:SEQuence:VIDeo:LEVel?'))
        level_channel.set_attribute('channel_type', 'trig_control')
        level_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(level_channel)
        
        slope_channel = channel(f'{channel_name}_slope',write_function=lambda s: self.get_interface().write(':TRIGger:SEQuence:SLOPe {s}'))
        slope_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:SLOPe?')
        slope_channel.add_preset('POSitive')
        slope_channel.add_preset('NEGative')
        slope_channel.set_attribute('channel_type', 'trig_control')
        slope_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(slope_channel)

        # delay_channel = channel(f'{channel_name}_trigger_slope',write_function=lambda s: self.get_interface().write(':TRIGger:SEQuence:SLOPe {s}'))
        # delay_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:SLOPe?')
        # 4.11.8 Trig Delay
            # Allows you to control a time delay during which the analyzer will wait to begin a sweep after receiving
            # an external or line trigger signal. You can use negative delay to pre-trigger the instrument.
            # NOTE Trigger Delay is not available in Free Run, so turning Free Run on turns off Trigger
            # Delay, but preserves the value of Trigger Delay.
            # Key Path: Trig
            # Dependencies/
            # Couplings: This function is not available when Trigger is Free Run or Video.
            # This function is not available when Gate is on.
            # State Saved: Saved in Instrument State.
            # Factory Preset: Off, 1 μs
            # Range: –150 ms to +500 ms
            # History: Added with firmware revision A.02.00
            # Remote Command:
            # :TRIGger[:SEQuence]:DELay <time>
            # :TRIGger[:SEQuence]:DELay?
            # :TRIGger[:SEQuence]:DELay:STATe OFF|ON|0|1
            # :TRIGger[:SEQuence]:DELay:STATe?
            # Example: TRIG:DEL:STAT ON
            # TRIG:DEL 100 ms
        # 4.11.9 Trig Offset (Remote Command Only)
            # This command sets the trigger offset. Trigger offset refers to the specified time interval before or after
            # the trigger event from which data is to be written to the trace, and then displayed. Ordinarily, the trigger
            # offset value is zero, and trace data is displayed beginning at the trigger event. A negative trigger offset
            # value results in the display of trace data prior to the trigger event. A positive trigger offset value results in
            # an effective delay in the display of trace data after the trigger event.
            # The trigger offset value used when the feature is enabled depends on the following parameters:
            # • Nominal trigger offset value originally entered
            # • Specific instrument hardware in use
            # • Sweep time
            # • Number of sweep points
            # The effective trigger offset value are re-calculated whenever any of these parameters change.
            # State Saved: Saved in Instrument State.
            # Factory Preset: 0 –500 ms
            # Range: Hardware specific; dependent upon the ADC being used, current state and the number
            # of sweep points.
            # History: Added with firmware revision A.02.00
            # Remote Command:
            # :TRIGger[:SEQuence]:OFFSet <time>
            # :TRIGger[:SEQuence]:OFFSet?
            # :TRIGger[:SEQuence]:OFFSet:STATe OFF|ON|0|1
            # :TRIGger[:SEQuence]:OFFSet:STATe?
            # Remote Command Notes: Trigger offset can only be turned on when in zero span and the resolution
            # bandwidth is 1 kHz or greater. Trigger offset is available for all trigger modes.
            # Example: TRIG:OFFS 100 ms
            # TRIG:OFFS:STAT ON turns on the trigger offset.
        return (mode_channel, source_channel, level_channel, slope_channel)
        #todo read_delegated blocking / autotrigger??

    def add_channel_sweep_time(self, channel_name):
        '''calculated time for single sweep, dependent on start/stop/points/rbw/etc'''
        def _set_sweep_time(t):
            self.get_interface().write(':SENSe:SWEep:TIME:AUTO OFF')
            self.get_interface().write(f':SENSe:SWEep:TIME {t}')
        force_channel = channel(f'{channel_name}',write_function=_set_sweep_time)
        force_channel.set_attribute('channel_type', 'meas_control')
        force_channel._set_value(float(self.get_interface().ask(':SENSe:SWEep:TIME?')))
        force_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_time.__doc__)
        force_channel._read = lambda: int(float(self.get_interface().ask(':SENSe:SWEep:TIME?')))        
        return self._add_channel(force_channel)       
        
    def add_channel_sweep_time_auto(self, channel_name):
        '''Tracks the state of the AUTO setting for the sweep time'''
        new_channel = integer_channel(name=channel_name, size=1, write_function=lambda on : self.get_interface().write(f':SENSe:SWEep:TIME:AUTO {"ON" if on else "OFF"}'))
        new_channel._read = lambda: int(self.get_interface().ask(':SENSe:SWEep:TIME:AUTO?'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_time_auto.__doc__)
        return self._add_channel(new_channel)

    def add_channel_message(self, channel_name):
        '''write message to lower left corner of screen display'''
        def _disp_msg(msg):
            if msg is None:
                self.get_interface().write(':SYSTem:MESSage:OFF')
            else:
                self.get_interface().write(f':SYSTem:MESSage "{msg}"')
        message_channel = channel(channel_name,write_function=_disp_msg)
        message_channel.set_attribute('channel_type', 'meas_control')
        message_channel.set_description(self.get_name() + ': ' + self.add_channel_message.__doc__)
        message = f"*PLEASE DON'T TOUCH* In use by {os.getlogin()} on {socket.gethostname()}." # 64 characters max
        message_channel.write(message)
        return self._add_channel(message_channel)

    def add_channel_y_disp(self, channel_name):
        '''The settings of Y Axis Units and Scale Type, affect how the data is read over the 
            remote interface. When using the remote interface no units are returned, so you must 
            know what the Y-Axis units are to interpret the results
        
        When Scale Type (Log) is selected, the vertical graticule divisions are scaled in logarithmic units. The 
        top line of the graticule is the Reference Level and uses the scaling per division, Scale/Div to assign 
        values to the other locations on the graticule. 
        When Scale Type (Lin) is selected, the vertical graticule divisions are linearly scaled with the reference 
        level value at the top of the display and zero volts at the bottom. Each vertical division of the graticule 
        represents one-tenth of the Reference Level.

        When the _units is set to "V" that is RMS not amplitude, A, as in A•sin(ωt)
        It will give 0.707•A.
'''
        reference_level_channel = channel(f'{channel_name}_reference_level',write_function=lambda ampl: self.get_interface().write(f':DISPlay:WINDow1:TRACe:Y:SCALe:RLEVel {ampl}'))
        reference_level_channel.set_attribute('channel_type', 'y_disp')
        reference_level_channel.add_preset(1)
        reference_level_channel.add_preset(10e-3)
        reference_level_channel.add_preset(1e-3)
        reference_level_channel.add_preset(0)
        reference_level_channel.add_preset(-20)
        reference_level_channel.add_preset(-80)
        # reference_level_channel._set_value(float(self.get_interface().ask(':DISPlay:WINDow1:TRACe:Y:SCALe:RLEVel?')))
        reference_level_channel._read = lambda: float(self.get_interface().ask(':DISPlay:WINDow1:TRACe:Y:SCALe:RLEVel?'))
        reference_level_channel.set_description(self.get_name() + ': ' + self.add_channel_y_disp.__doc__)
        self._add_channel(reference_level_channel)
        
        units_channel = channel(f'{channel_name}_units',write_function=lambda unit: self.get_interface().write(f':UNIT:POWer {unit}')) # DBM|DBMV|DBMA|V|W|A|DBUV|DBUA|DBUVM|DBUAM|DBPT|DBG
        units_channel.set_attribute('channel_type', 'y_disp')
        units_channel._set_value(self.get_interface().ask(':UNIT:POWer?'))
        # units_channel._read = ??
        units_channel.add_preset('DBM', 'Sets the amplitude units to dBm.')
        units_channel.add_preset('DBMV', 'Sets the amplitude units to dBmV.')
        units_channel.add_preset('DBMA', 'Sets the amplitude units to dBmA.')
        units_channel.add_preset('V', 'Sets the amplitude units to volts.')
        units_channel.add_preset('W', 'Sets the amplitude units to watts.')
        units_channel.add_preset('A', 'Sets the amplitude units to amps.')
        units_channel.add_preset('DBUV', 'Sets the amplitude units to dBμV.')
        units_channel.add_preset('DBUA', 'Sets the amplitude units to dBμA.')
        units_channel.add_preset('DBUVM', 'Sets the amplitude units to dBμV/m. This is a unit specifically applicable to EMI field strength measurements. In the absence of a correction factor this unit is treated by the instrument exactly as though it were dBμV. You must load an appropriate correction factor using amplitude corrections for this unit to generate meaningful results. Therefore, this key is unavailable unless one of the corrections is turned on (in Amplitude, Corrections menu) and Apply Corrections is set to Yes.')
        units_channel.add_preset('DBUAM', 'Sets the amplitude units to dBμA/m. This is a unit specifically applicable to EMI field strength measurements. In the absence of a correction factor this unit is treated by the instrument exactly as though it were dBμV. You must load an appropriate correction factor using amplitude corrections for this unit to generate meaningful results. Therefore, this key is unavailable unless one of the corrections is turned on (in Amplitude, Corrections menu) and Apply Corrections is set to Yes.')
        units_channel.add_preset('DBPT', 'Sets the amplitude units to dBpT. This is a unit specifically applicable to EMI field strength measurements. In the absence of a correction factor this unit is treated by the instrument exactly as though it were dBμV. You must load an appropriate correction factor using amplitude corrections for this unit to generate meaningful results. Therefore, this key is unavailable unless one of the corrections is turned on (in Amplitude, Corrections menu) and Apply Corrections is set to Yes.')
        units_channel.add_preset('DBG', 'Sets the amplitude units to dBG. This is a unit specifically applicable to EMI field strength measurements. In the absence of a correction factor this unit is treated by the instrument exactly as though it were dBμV. You must load an appropriate correction factor using amplitude corrections for this unit to generate meaningful results. Therefore, this key is unavailable unless one of the corrections is turned on (in Amplitude, Corrections menu) and Apply Corrections is set to Yes.')
        units_channel.set_description(self.get_name() + ': ' + self.add_channel_y_disp.__doc__)
        self._add_channel(units_channel)
        
        spacing_channel = channel(f'{channel_name}_spacing',write_function=lambda spac: self.get_interface().write(f':DISP:WIND:TRAC:Y:SPAC {spac}'))
        spacing_channel.set_attribute('channel_type', 'y_disp')
        spacing_channel._set_value(self.get_interface().ask(':DISP:WIND:TRAC:Y:SPAC?'))
        # spacing_channel._read = lambda: self.get_interface().ask(':DISP:WIND:TRAC:Y:SPAC?')
        spacing_channel.add_preset('LINear')
        spacing_channel.add_preset('LOGarithmic')
        spacing_channel.set_description(self.get_name() + ': ' + self.add_channel_y_disp.__doc__)
        self._add_channel(spacing_channel)
        
        scale_channel = channel(f'{channel_name}_scale',write_function=lambda power: self.get_interface().write(f':DISPlay:WINDow1:TRACe:Y:SCALe:PDIVision {power}'))
        scale_channel.set_attribute('channel_type', 'y_disp')
        scale_channel.add_preset(10)
        scale_channel.add_preset(20) 
        # scale_channel._set_value(float(self.get_interface().ask(':DISPlay:WINDow1:TRACe:Y:SCALe:PDIVision?')))
        scale_channel._read = lambda: float(self.get_interface().ask(':DISPlay:WINDow1:TRACe:Y:SCALe:PDIVision?'))
        scale_channel.set_description(self.get_name() + ': ' + self.add_channel_y_disp.__doc__)
        self._add_channel(scale_channel)
        
        offset_channel = channel(f'{channel_name}_reference_level_offset',write_function=lambda dB: self.get_interface().write(f':DISPlay:WINDow1:TRACe:Y:SCALe:RLEVel:OFFSet {dB}'))
        offset_channel.set_attribute('channel_type', 'y_disp')
        offset_channel.add_preset(0)
        offset_channel.add_preset(20) #450 ohm divider
        offset_channel._read = lambda: float(self.get_interface().ask(':DISPlay:WINDow1:TRACe:Y:SCALe:RLEVel:OFFSet?'))
        offset_doc_str = '''2.1.9 Ref Lvl Offset
            Allows you to add an offset value to the displayed reference level. The reference level is the absolute
            using the numeric keypad or programming commands. The knob and step keys are not active.
            Offsets are used when a gain or loss occurs between a device under test and the analyzer input. Thus, the
            signal level measured by the analyzer may be thought of as the level at the input of an external amplitude
            conversion device. Entering an offset does not affect the trace position or attenuation value, just the
            displayed value readouts such as reference level and marker amplitudes.
            The maximum reference level available is dependent on the reference level offset. That is, Ref Level −
            Ref Level Offset must be in the range −170 to +30 dBm.
            For example, the reference level value range can be initially set to values from −170 dBm to 30 dBm
            with no reference level offset. If the reference level is first set to −20 dBm, then the reference level offset
            can be set to values of −50 to +150 dB.
            If the reference level offset is first set to −30 dB, then the reference level can be set to values of −200
            dBm to 0 dBm. In this case, the reference level is “clamped” at 0 dBm because the maximum limit of
            +30 dBm is reached with a reference level setting of 0 dBm with an offset of −30 dB. If instead, the
            reference level offset is first set to 30 dB, then the reference level can be set to values of −140 to +60
            dBm.
            When a reference level offset is entered, the offset value appears on the left side of the display under
            Offst (as opposed to frequency offsets which appear at the bottom of the display.) To eliminate an
            offset, press Ref Lvl Offst, 0, and dB.'''
        offset_channel.set_description(f'{self.get_name()}: {self.add_channel_y_disp.__doc__}\n\n{offset_doc_str}')
        self._add_channel(offset_channel)
        # 2.1.12 Ext Amp Gain
            # Compensates for external gain or loss. The function is similar to the Ref Lvl Offset function, however 
            # Chapter 2 53
            # Instrument Functions: A - L
            # AMPLITUDE / Y Scale
            # Instrument Functions: A - L
            # this value is considered, along with the maximum mixer level setting, to determine the attenuation 
            # required (10 dB of Attenuation is added for every 10 dB of External Amp Gain). The gain is subtracted 
            # from the amplitude readout so that the displayed signal level represents the signal level at the input of the 
            # external device.
            # Gains may only be entered with the numeric keypad or programming commands, not the knob or step 
            # keys
        # [:SENSe]:CORRection:OFFSet[:MAGNitude] <relative_power> (in dB)
        # [:SENSe]:CORRection:OFFSet[:MAGNitude]?
        
        return (reference_level_channel, units_channel, spacing_channel, scale_channel, offset_channel)
        
    def add_channel_coupling(self, channel_name):
        '''Specifies alternating current (AC) or direct current (DC) coupling at the analyzer RF input port. 
Selecting AC coupling switches in a blocking capacitor that blocks any DC voltage present at the 
analyzer input. This decreases the input frequency range of the analyzer, but prevents damage to the 
input circuitry of the analyzer if there is a DC voltage present at the RF input.
In AC coupling mode, signals less than 20 MHz are not calibrated. You must switch to DC coupling to 
see calibrated frequencies of less than 20 MHz. Note that the message DC Coupled will be displayed 
on the analyzer when DC is selected.
Some amplitude specifications apply only when coupling is set to DC. Refer to the appropriate 
amplitude specifications and characteristics for your analyzer. 
CAUTION When operating in DC coupled mode, ensure protection of the input mixer by limiting the 
input level to within 200 mV of 0 Vdc. In AC or DC coupling, limit the input RF power to 
+30 dBm'''
        coupling_channel = channel(f'{channel_name}',write_function=lambda c: self.get_interface().write(f':INPut:COUPling {c}'))
        coupling_channel.set_attribute('channel_type', 'meas_control')
        coupling_channel._set_value(self.get_interface().ask(':INPut:COUPling?'))
        coupling_channel.add_preset('AC')
        coupling_channel.add_preset('DC')
        coupling_channel.set_description(self.get_name() + ': ' + self.add_channel_coupling.__doc__)
        return self._add_channel(coupling_channel)

    def add_channel_1st_IF_overload(self, channel_name):
        '''Corresponds to "1st IF Overload" on screen.
        Indicates that the input to the mixer is overloaded after the attenutors and preamplifier.
        Increase the declared power level or manually coerce the attenuation level up (not recommended).'''
        scpi        = ':STATus:QUEStionable:POWer:CONDition?'
        decode_bit  = 6
        message1, message2, message3 = '*** ERROR ***', 'PSA indicates an overload on the 1st IF stage.', 'Correct the attenuation level!'
        def get_status():
            error = bit_is_set(int(self.get_interface().ask(scpi)), decode_bit)
            if error:
                print_banner(message1, message2, message3)
            return error
        new_channel = channel(channel_name, read_function=lambda : get_status())
        new_channel.set_attribute('channel_type', 'status')
        new_channel._set_value( get_status())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_1st_IF_overload.__doc__)
        return self._add_channel(new_channel)
        
    def add_channel_final_IF_overload(self, channel_name):
        '''Corresponds to "Final IF Overload" on screen.
        Indicates that the input to the second stage is overloaded after the first mixer (?).
        Increase the declared power level or manually coerce the attenuation level up (not recommended).'''
        scpi        = ':STATus:QUEStionable:INTegrity:CONDition?'
        decode_bit  = 4
        message1, message2, message3 = '*** ERROR ***', 'PSA indicates an overload on the final IF stage.', 'Correct the attenuation level!'
        def get_status():
            error = bit_is_set(int(self.get_interface().ask(scpi)), decode_bit)
            if error:
                print_banner(message1, message2, message3)
            return error
        new_channel = channel(channel_name, read_function=lambda : get_status())
        new_channel.set_attribute('channel_type', 'status')
        new_channel._set_value(get_status())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_final_IF_overload.__doc__)
        return self._add_channel(new_channel)
        
    def add_channel_measurement_uncalibrated(self, channel_name):
        '''Signal Integrity Issue.
        Indicates that the signal is out of range for calibration somewhere along the signal path(?).
        Increase the declared power level or manually coerce the attenuation level up (not recommended).'''
        scpi        = ':STATus:QUEStionable:INTegrity:CONDition?'
        decode_bit  = 3
        message1, message2, message3 = '*** ERROR ***', 'PSA indicates measurement uncalibrated.', 'Correct the attenuation level!'
        def get_status():
            error = bit_is_set(int(self.get_interface().ask(scpi)), decode_bit)
            if error:
                print_banner(message1, message2, message3)
            return error
        new_channel = channel(channel_name, read_function=lambda : get_status())
        new_channel.set_attribute('channel_type', 'status')
        new_channel._set_value(get_status())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_measurement_uncalibrated.__doc__)
        return self._add_channel(new_channel)

    def add_channel_calibration_error(self, channel_name):
        '''Signal Integrity Issue.
        Indicates that the signal is out of range for calibration somewhere along the signal path(?).
        Increase the declared power level or manually coerce the attenuation level up (not recommended).'''
        scpi        = 'STATus:QUEStionable:INTegrity:UNCalibrated:CONDition?'
        decode_bit  = 0
        message1, message2, message3 = '*** ERROR ***', 'PSA indicates measurement uncalibrated.', 'Correct the attenuation level!'
        def get_status():
            error = bit_is_set(int(self.get_interface().ask(scpi)), decode_bit)
            if error:
                print_banner(message1, message2, message3)
            return error
        new_channel = channel(channel_name, read_function=lambda : get_status())
        new_channel.set_attribute('channel_type', 'status')
        new_channel._set_value(get_status())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_calibration_error.__doc__)
        return self._add_channel(new_channel)
        
    def add_channel_questionable(self, channel_name):
        '''Aggregation (catchall) of various status questionable bits.
        This should always be zero if the data is to be trusted.
        For non zero values see the programmer's manual pages 347 and 379:
        https://swarm.adsdesign.analog.com/files/adi/equipment_info/north_chelmsford/TRUNK/Keysight/Signal%20Analyzer/PSA/Doc/E444x%20programmers%20manual%209018-01328.pdf).'''
        scpi = 'STATus:QUEStionable:CONDition?'
        message1, message2, message3 = '*** ERROR ***', 'PSA indicates generally questionable data.', 'Correct the attenuation level!'
        def get_status():
            error = int(self.get_interface().ask(scpi))
            if error:
                print_banner(message1, message2, message3)
            return error
        
        new_channel = channel(channel_name, read_function=lambda : get_status())
        new_channel.set_attribute('channel_type', 'status')
        new_channel._set_value(get_status())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_questionable.__doc__)
        return self._add_channel(new_channel)

    def add_channel_fullscreen(self, channel_name):
        '''Turns off the screen buttons temporarily for more usful viewing. They will come back on if other user inputs require them.'''
        new_channel = integer_channel(name=channel_name, size=1, write_function=lambda on : self.get_interface().write(f':DISPlay:FSCReen:STATe {"ON" if on else "OFF"}'))
        new_channel._read = lambda: int(self.get_interface().ask(':DISPlay:FSCReen:STATe?'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_fullscreen.__doc__)
        return self._add_channel(new_channel)
        
    def add_channel_syst_error(self, channel_name):
        '''Returns the response to :SYSTem:ERROr? to see if there are any commands making the instrument angry. Perform repeated reads to get them all and clear the buffer.'''
        new_channel = channel(name=channel_name, read_function=lambda : self.get_interface().ask(':SYSTem:ERROr?'))
        new_channel.set_attribute('channel_type', 'y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_syst_error.__doc__)
        return self._add_channel(new_channel)

    # def add_channel_undertemp(self, channel_name):
    # STATus:QUEStionable:TEMPerature:CONDition?
    # Register map on page 347 doesn't show any bits doing anything
    # but on page 356 it says:
    # Bit 4
    # Temperature summary
    # The instrument is still warming up.
    # So what gives?

    def add_channels(self, channel_name):
        ''''''
        channels = []
        channels.append(self.add_channel_xdata(f'{channel_name}_xpoints'))
        channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1))
        channels.extend(self.add_channel_sweep_control(f'{channel_name}')) # _start, _stop, _center, _span, _point_count
        channels.extend(self.add_channel_sweep_type(f'{channel_name}_sweep_type'))
        channels.extend(self.add_channel_y_disp(f'{channel_name}')) # _reference_level, _units, _spacing, _scale, _reference_level_offset
        channels.append(self.add_channel_RBW(f'{channel_name}_RBW'))
        channels.append(self.add_channel_RBW_auto(f'{channel_name}_RBW_auto'))
        channels.append(self.add_channel_VBW(f'{channel_name}_VBW'))
        channels.extend(self.add_channel_VBW_auto(f'{channel_name}_VBW_auto')) # '', _RBW_VBW_ratio, _RBW_VBW_auto
        channels.extend(self.add_channel_average(f'{channel_name}_average'))
        channels.append(self.add_channel_detector(f'{channel_name}_detector'))
        channels.append(self.add_channel_attenuator(f'{channel_name}_attenuator'))
        channels.append(self.add_channel_attenuator_auto(f'{channel_name}_attenuator_auto'))
        channels.append(self.add_channel_max_power(f'{channel_name}_max_power'))
        channels.append(self.add_channel_preamp(f'{channel_name}_preamp'))
        channels.extend(self.add_channel_trigger(f'{channel_name}_trigger')) # _mode, _source, _video_level, _slope
        channels.append(self.add_channel_sweep_time(f'{channel_name}_sweep_time'))
        channels.append(self.add_channel_sweep_time_auto(f'{channel_name}_sweep_time_auto'))
        channels.append(self.add_channel_message(f'{channel_name}_message'))
        channels.append(self.add_channel_coupling(f'{channel_name}_coupling'))
        channels.append(self.add_channel_1st_IF_overload(f'{channel_name}_input_overload'))
        channels.append(self.add_channel_final_IF_overload(f'{channel_name}_final_overload'))
        channels.append(self.add_channel_calibration_error(f'{channel_name}_uncalibrated'))
        channels.append(self.add_channel_fullscreen(f'{channel_name}_fullscreen'))
        channels.append(self.add_channel_syst_error(f'{channel_name}_syst_error'))
        #
        # TODO:
        # These next two are confusing.
        # They seem to indicate true no matter what.
        # One of them reado False when read from the Keysight VISA direct GUI in real time while simultaneously reading True from Python
        # What the heck gives with that? Need to go down that rabbit hole at some point.
        #
        # channels.append(self.add_channel_measurement_uncalibrated(f'{channel_name}_measurement_uncal'))
        # channels.append(self.add_channel_questionable(f'{channel_name}_reading_questionable'))
        return channels
        
    # TODO!
   
    # VIDBW control
    # FFT controls
    # waveform/basic?
    # zero span controls
    # trigger source controls
    # averaging type controls
    
    # averaging controls
    # :DISPlay:WINDow:TRACe:Y:DLINe <ampl>
    # :DISPlay:WINDow:TRACe:Y:DLINe?
    # :DISPlay:WINDow:TRACe:Y:DLINe:STATe OFF|ON|0|1
    # :DISPlay:WINDow:TRACe:Y:DLINe:STATe?
    # :CALCulate:LLINe[1]|2:DATA 
    # <x-axis>, <ampl>, <connected>{,<x-axis>,<ampl>,<connected>}
    # :CALCulate:LLINe[1]|2:DATA
    
    
    # synchronize with sweep time
    # sweep trigger/mode controls / completion readback / delegator
    # :STATus:OPERation:CONDition?
    
    
    # :INITiate:CONTinuous OFF|ON. See “SWEEP” on page 211
    # On receiving the :INITiate[:IMMediate] command, it will go through a single trigger cycle, and then return to the “idle” state.
    
    # spot measurement scalars at frequency :CALCulate:MARKer[1]|2|3|4:TRACe 1|2|3  Puts the marker on the specified trace and turns Auto OFF for that marker.   :CALCulate:MARKer[1]|2|3|4:TRACe
    # :CALCulate:MARKer[1]|2|3|4:MODE POSition|DELTa|BAND|SPAN|OFF :CALCulate:MARKer[1]|2|3|4:MODE?
    # :CALCulate:MARKer[1]|2|3|4:X <param> Sets the marker X position to a specified point on the X axis in the current X-axis units (frequency or time). If the frequency or time chosen would place the marker off screen, the marker will be placed at the left or right side of the display, on the trace. This command has no effect if the marker is OFF.
    # :CALCulate:MARKer[1]|2|3|4:X?
    # :CALCulate:MARKer[1]|2|3|4:STATe OFF|ON|0|1
    # :CALCulate:MARKer[1]|2|3|4:STATe?
    # Sets or queries the state of a marker. Setting a marker to state ON or 1 selects that marker. Setting a marker which is OFF to state ON or 1 puts it in Normal mode and places it at the center of the display. Setting a marker to state OFF or 0 selects that marker and turns it off. The response to the query will be 0 if OFF, 1 if ON.
    
    # 3.2.2 Marker Noise
    # Activates a noise marker for the selected marker. If the selected marker is off it is turned on and located 
    # at the center of the display. Reads out the average noise level, normalized to a 1 Hz noise power 
    # bandwidth, around the active marker. The noise marker averages 5% of the trace data values, centered on 
    # the location of the marker. 
    # The data displayed (if the marker is in Normal mode) is the noise density around the marker. The value 
    # readout is followed by “(1 Hz)” to remind you that display is normalized to a one Hz bandwidth.
    # :CALCulate:MARKer[1]|2|3|4:FUNCtion BPOWer|NOISe|OFF
    # :CALCulate:MARKer[1]|2|3|4:FUNCtion?
    # To guarantee accurate data for noise-like signals, a correction for equivalent noise bandwidth is made by 
    # the analyzer. The Marker Noise function accuracy is best when the detector is set to Average or 
    # Sample, because neither of these detectors will peak-bias the noise. The trade off between sweep time 
    # and variance of the result is best when Avg/VBW Type is set to Power Averaging. Auto coupling, 
    # therefore, normally chooses the Average detector and Power Averaging. Though the Marker Noise 
    # function works with all settings of detector and Avg/VBW Type, using the positive or negative peak 
    # detectors gives less accurate measurement results
    # 3.2.3 Band/Intvl Power
    # Measures the power in a bandwidth (non-zero span) or time interval (zero span) specified by the user. If 
    # no marker is on, this key activates the delta pair marker mode. If the detector mode is set to Auto, the 
    # average detector is selected. If the Avg/VBW type is set to Auto, Power Averaging is selected, other 
    # choices of detector and Avg/VBW type will usually cause measurement inaccuracy. The active marker 
    # pair indicate the edges of the band. Only Delta Pair and Span Pair marker control modes can be used 
    # while in this function, selecting any other mode (for example, Normal or Delta) turns off this function
    
    # amplitude units :UNIT:POWer DBM|DBMV|DBMA|V|W|A|DBUV|DBUA|DBUVM|DBUAM|DBPT|DBG  :UNIT:POWer?
    
    
    #tODO display format strings
    # todo f<50k
    # todo fft mode control
    # todo spec/test limit lines and interp control
    # :CALCulate:LLINe[1]|2:DATA <x-axis>, <ampl>, <connected>{,<x-axis>,<ampl>,<connected>}
    # :CALCulate:LLINe[1]|2:DATA
    # :CALCulate:LLINe[1]|2:STATe OFF|ON|0|1 to turn limit lines on or off.
    # :CALCulate:LLINe[1]|2:STATe?
    # :CALCulate:LLINe[1]|2:FAIL?
    # :CALCulate:LLINe[1]|2:MARGin:STATe OFF|ON|0|1 turns on margins on or off. If the margin 
    # and limit display are both turned off, limit test is automatically turned off.
    # :CALCulate:LLINe[1]|2:MARGin:STATe?
    # Responds with the margin state; 0 = off 1 = on.
    # :CALCulate:LLINe[1]|2:MARGin <ampl_rel> 
    # Defines the amount of measurement margin that is added to the designated limit line.
    # :CALCulate:LLINe[1]|2:MARGin?