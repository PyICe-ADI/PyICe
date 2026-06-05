"""Pattern generators utilities.

>>> from PyICe.data_utils.pattern_generators import TWI_Pattern

"""
from PyICe.lab_utils.eng_string import eng_string
from PyICe import LTC_plot


class TWI_Pattern():
    """This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.

    It's meant to feed into a pattern generator instrument such as the old HP8110A dual pattern generator or its modern equivalent.
    It has two channels, one for the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.

    >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
    >>> TWI_Pattern is not None
    True

    """
    class Leader():
        def __init__(self, pattern, SCL, SDA, tleader, strobe=False):
            """Initialize leader.
            Initializes 5 instance attributes that configure the object's
            behavior.

            Initializes 5 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                SCL: Scl to use.
                SDA: Sda to use.
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                tleader: Tleader to use.
            """
            self.pattern = pattern
            self.tleader = pattern.quantize(tleader)
            self.SCL = SCL
            self.SDA = SDA
            self.STB = strobe

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``Leader`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.Leader, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            self.pattern.dwell(
                SCL=self.SCL,
                SDA=self.SDA,
                STB=self.STB,
                tdwell=self.tleader)

    class Start():
        def __init__(self, pattern, thd_sta, strobe=False):
            """Initialize start.
            Stores configuration in ``STB``, ``pattern``, ``thd_sta`` for use
            by other methods.

            Initializes 3 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                thd_sta: Thd sta to use.
            """
            self.pattern = pattern
            self.thd_sta = pattern.quantize(thd_sta)
            self.STB = strobe

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``Start`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.Start, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            self.pattern.dwell(SCL=1, SDA=0, STB=self.STB, tdwell=self.thd_sta)

    class Stop():
        def __init__(self, pattern, tsu_sto, tbuf, strobe=False):
            """Initialize stop.
            Initializes 4 instance attributes that configure the object's
            behavior.

            Initializes 4 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                tbuf: Tbuf to use.
                tsu_sto: Tsu sto to use.
            """
            self.pattern = pattern
            self.tsu_sto = pattern.quantize(tsu_sto)
            self.tbuf = pattern.quantize(tbuf)
            self.STB = strobe

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``Stop`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.Stop, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            self.pattern.dwell(SCL=1, SDA=0, STB=self.STB, tdwell=self.tsu_sto)
            self.pattern.dwell(SCL=1, SDA=1, STB=self.STB, tdwell=self.tbuf)

    class Bitend():
        def __init__(self, pattern, tdwell, strobe=False):
            """Initialize bitend.
            Stores configuration in ``STB``, ``pattern``, ``tdwell`` for use
            by other methods.

            Initializes 3 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                tdwell: Tdwell to use.
            """
            self.pattern = pattern
            self.STB = strobe
            self.tdwell = tdwell

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``Bitend`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.Bitend, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            if previous_item.thd_dat >= 0:  # Previous bit had Positive or Zero hold time
                self.pattern.dwell(
                    SCL=0,
                    SDA=previous_item.value,
                    STB=self.STB,
                    tdwell=previous_item.thd_dat)
                self.pattern.dwell(SCL=0, SDA=0, STB=0, tdwell=self.tdwell)
            else:                           # Previous bit had Negative hold time
                self.pattern.dwell(
                    SCL=0, SDA=0, STB=self.STB, tdwell=self.tdwell)

    class SDA_Spike():
        def __init__(self, pattern, value, tstart, twidth, strobe=False):
            """Initialize s d a_ spike.
            Initializes 5 instance attributes that configure the object's
            behavior.

            Initializes 5 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                tstart: Tstart to use.
                twidth: Twidth to use.
                value: Value to set.
            """
            self.pattern = pattern
            self.value = value
            self.tstart = pattern.quantize(tstart)
            self.twidth = pattern.quantize(twidth)
            self.STB = strobe
            assert self.twidth > 0, f"TWI Pattern Generator: Requested SDA spike starting at {tstart} rounded to 0 width in pattern, not acheivable."

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``SDA_Spike`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.SDA_Spike, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            self.pattern.sda_spikes.append(self)

    class SCL_Spike():
        def __init__(self, pattern, value, tstart, twidth, strobe=False):
            """Initialize s c l_ spike.
            Initializes 5 instance attributes that configure the object's
            behavior.

            Initializes 5 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> TWI_Pattern is not None
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                tstart: Tstart to use.
                twidth: Twidth to use.
                value: Value to set.
            """
            self.pattern = pattern
            self.value = value
            self.tstart = pattern.quantize(tstart)
            self.twidth = pattern.quantize(twidth)
            self.STB = strobe
            assert self.twidth > 0, f"TWI Pattern Generator: Requested SCL spike starting at {tstart} rounded to 0 width in pattern, not acheivable."

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``SCL_Spike`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.SCL_Spike, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            self.pattern.scl_spikes.append(self)

    class Bit():
        """The data bit cycle starts by bringing SCL low.

        The previous data bit is held until its hold time (THD_DAT Prev) expires or is brought low immediately if the pervious bit's hold time is 0.
        It then dwells with SCL low until the setup time of this bit whereupon SDA goes to the value for this bit.
        It then dwells for the setup time for this bit and then SCL goes high.
        SCL stays high for the duration of THIGH.
        If the hold time of this bit is negative, SDA is brought low before this bit's cycle ends.
        _____________________________
        |
    SCL ___________________________________|

        _________                   _____________________________________
    SDA  D (PREV)|                 |             D (THIS ONE)
        _________|_________________|_____________________________________

        <- THD ->|                 |<-TSU->|
        (PREV)  |                 |       |
        <------------ TLOW --------------->|<--------- THIGH ----------->
        |                 |       |
        █••••••••█•••••••••••••••••█•••••••█••••••••••••••••••••••••••••• <------ █ (Blocks) Denote where changes occur, • (Dots) denote time slices
        """
        def __init__(self, pattern, value, tlow, thigh,
                     tsu_dat, thd_dat, strobe=False):
            """Initialize bit.
            Initializes 7 instance attributes that configure the object's
            behavior.

            Initializes 7 instance attributes that configure the object's behavior.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern, '__init__')
            True

            Args:
                pattern: Bit pattern or regex pattern string.
                strobe: Strobe signal pin or enable flag.
                thd_dat: Thd dat to use.
                thigh: Thigh to use.
                tlow: Tlow to use.
                tsu_dat: Tsu dat to use.
                value: Value to set.
            """
            self.pattern = pattern
            self.value = value
            self.tlow = pattern.quantize(tlow)
            self.thigh = pattern.quantize(thigh)
            self.tsu_dat = pattern.quantize(tsu_dat)
            self.thd_dat = pattern.quantize(thd_dat)
            self.STB = strobe

        def extend(self, previous_item):
            """Run the extend step.

            Supports the ``Bit`` workflow by performing the described operation.


            >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
            >>> hasattr(TWI_Pattern.Bit, "extend")
            True

            Args:
                previous_item: The preceding item for comparison or linking.
            """
            if isinstance(previous_item, self.pattern.Start):
                previous_thd_dat = 0
                previous_value = 0
            elif isinstance(previous_item, self.pattern.Leader):
                previous_thd_dat = previous_item.tleader
                previous_value = previous_item.SDA
            else:
                previous_thd_dat = previous_item.thd_dat
                previous_value = previous_item.value
            if previous_thd_dat >= 0:    # Previous bit had Positive or Zero hold time
                self.pattern.dwell(
                    SCL=0,
                    SDA=previous_value,
                    STB=0,
                    tdwell=previous_thd_dat)
                self.pattern.dwell(
                    SCL=0,
                    SDA=0,
                    STB=0,
                    tdwell=self.tlow -
                    previous_thd_dat -
                    self.tsu_dat)
                self.pattern.dwell(
                    SCL=0, SDA=self.value, STB=0, tdwell=self.tsu_dat)
            else:                         # Previous bit had Negative hold time
                self.pattern.dwell(
                    SCL=0, SDA=0, STB=0, tdwell=self.tlow - self.tsu_dat)
                self.pattern.dwell(
                    SCL=0, SDA=self.value, STB=0, tdwell=self.tsu_dat)
            if self.thd_dat >= 0:         # Current bit has Positive or Zero hold time
                self.pattern.dwell(
                    SCL=1,
                    SDA=self.value,
                    STB=self.STB,
                    tdwell=self.thigh)
            else:                         # Current bit has Negative hold time
                self.pattern.dwell(
                    SCL=1,
                    SDA=self.value,
                    STB=self.STB,
                    tdwell=self.thigh +
                    self.thd_dat)
                self.pattern.dwell(
                    SCL=1, SDA=0, STB=self.STB, tdwell=-self.thd_dat)
    '''
    Here's the start of the actual TWI pattern class.
    '''
    def __init__(self, tstep, max_record_size):
        """Initialize t w i_ pattern.
        Stores configuration in ``max_record_size``, ``tstep`` for use by
        other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> TWI_Pattern is not None
        True

        Args:
            max_record_size: Max record size to use.
            tstep: Tstep to use.
        """
        self.tstep = tstep
        self.max_record_size = max_record_size

    def initialize(self):
        """Call this whenever you want to start a new pattern or flush an existing pattern to change settings.

        Otherwise the pattern will keep on growing if you keep adding items.

        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'initialize')
        True

        """
        self.items = []
        self.SDA = []
        self.SCL = []
        self.STB = []
        self.sda_spikes = []
        self.scl_spikes = []

    def add_item(self, item):
        """Add a item.

        Appends a new item entry to the object's internal collection.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'add_item')
        True

        Args:
            item: Item to process or look up.
        """
        self.items.append(item)

    def quantize(self, time):
        """Return the quantize.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'quantize')
        True

        Args:
            time: Time to use.

        Returns:
            The quantized value.
        """
        return round(time / self.tstep) * self.tstep

    def dwell(self, SCL, SDA, STB, tdwell):
        """Run the dwell step.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'dwell')
        True

        Args:
            SCL: Scl to use.
            SDA: Sda to use.
            STB: Stb to use.
            tdwell: Tdwell to use.
        """
        cycles = round(tdwell / self.tstep)
        assert cycles >= 0, f"TWI Pattern Generator: tdwell of {tdwell} results in the addition of a negative time slice, not acheivable."
        self.SCL.extend([SCL] * cycles)
        self.SDA.extend([SDA] * cycles)
        self.STB.extend([STB] * cycles)

    def pad_out(self):
        """Perform pad out operation.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.

        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'pad_out')
        True

        """
        cycles = self.max_record_size - len(self.SCL)
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)

    def finalize(self):
        """Run the finalize step.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.

        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'finalize')
        True

        """
        previous = None
        for item in self.items:
            item.extend(previous)
            previous = item
        for sda_spike in self.sda_spikes:
            for index in range(len(self.SDA)):
                if index > sda_spike.tstart / \
                        self.tstep and index <= (sda_spike.tstart + sda_spike.twidth) / self.tstep:
                    if sda_spike.value:
                        self.SDA[index] |= 1
                    else:
                        self.SDA[index] &= 0
        for scl_spike in self.scl_spikes:
            for index in range(len(self.SCL)):
                if index > scl_spike.tstart / \
                        self.tstep and index <= (scl_spike.tstart + scl_spike.twidth) / self.tstep:
                    if scl_spike.value:
                        self.SCL[index] |= 1
                    else:
                        self.SCL[index] &= 0
        self.audit()

    def get_SDA(self):
        """Return the current sda.
        Returns the stored sda value from the object's internal state.
        Returns the stored sda from the object's internal state.

        Returns the stored SDA from the object's internal state.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'get_SDA')
        True

        Returns:
            The current sda.
        """
        return self.SDA

    def get_SCL(self):
        """Return the current scl.
        Returns the stored scl value from the object's internal state.
        Returns the stored scl from the object's internal state.

        Returns the stored SCL from the object's internal state.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'get_SCL')
        True

        Returns:
            The current scl.
        """
        return self.SCL

    def get_STB(self):
        """Return the current stb.
        Returns the stored stb value from the object's internal state.
        Returns the stored stb from the object's internal state.

        Returns the stored STB from the object's internal state.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'get_STB')
        True

        Returns:
            The current stb.
        """
        return self.STB

    def get_ALL(self, SCL_channel, SDA_channel, STB_channel):
        """Build up the compound record of instrument Channels 1, 2 and 3 (Strobe).

        On the HP8110a, for example, the two output channels and the Strobe channel are binarily weighted so it takes values of 0-7 for 3 bits.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'get_ALL')
        True

        Args:
            SCL_channel: Scl channel to use.
            SDA_channel: Sda channel to use.
            STB_channel: Stb channel to use.

        Returns:
            The current all.
        """
        values = []
        for position in range(len(self.SCL)):
            values.append(self.SCL[position] *
                          2**(SCL_channel -
                              1) +
                          self.SDA[position] *
                          2**(SDA_channel -
                              1) +
                          self.STB[position] *
                          2**(STB_channel -
                              1))
        return values

    def audit(self):
        """Run the audit step.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.

        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'audit')
        True

        """
        assert len(
            self.SDA) == len(
            self.SCL), "TWI Pattern Generator: SDA and SCL records unequal length!"
        assert len(
            self.SCL) == len(
            self.STB), "TWI Pattern Generator: SCL and STB records unequal length!"
        assert len(
            self.SCL) <= self.max_record_size, f"TWI Pattern Generator: Record size of {len(self.SCL)} exceeds max record size of {self.max_record_size}!"

    def visualize(self, title=None, file_basename=None, offset_SCL=5,
                  offset_SDA=3, offset_STB=1, plot_sizex=5, plot_sizey=4):
        """Run the visualize step.

        Supports the ``TWI_Pattern`` workflow by performing the described operation.


        >>> from PyICe.data_utils.pattern_generators import TWI_Pattern
        >>> hasattr(TWI_Pattern, 'visualize')
        True

        Args:
            file_basename: Base filename without extension.
            offset_SCL: Offset scl to use.
            offset_SDA: Offset sda to use.
            offset_STB: Offset stb to use.
            plot_sizex: Plot sizex to use.
            plot_sizey: Plot sizey to use.
            title: Title string for display or report heading.
        """
        times = [index * self.tstep for index in range(len(self.SCL))]
        G0 = LTC_plot.scope_plot(plot_title="TWI Pattern" if title is None else title,
                                 plot_name=None,
                                 xaxis_label=f"{eng_string(x=times[-1] / 10, fmt=':.3g', si=True, units='s')} / DIV",
                                 xlims=(times[0], times[-1]),
                                 ylims=(0, 8))
        SCL = [value + offset_SCL for value in self.SCL]
        SDA = [value + offset_SDA for value in self.SDA]
        STB = [value + offset_STB for value in self.STB]
        G0.add_trace(data=zip(times, SCL),
                     color=LTC_plot.LT_RED_1,
                     marker=None,
                     markersize=0,
                     legend="SCL")
        G0.add_trace(data=zip(times, SDA),
                     color=LTC_plot.LT_BLUE_1,
                     marker=None,
                     markersize=0,
                     legend="SDA")
        G0.add_trace(data=zip(times, STB),
                     color=LTC_plot.LT_GREEN_1,
                     marker=None,
                     markersize=0,
                     legend="STB")
        G0.add_legend(
            axis=1,
            location=(
                0.98,
                0.98),
            justification='upper right',
            use_axes_scale=False,
            fontsize=10)
        G0.add_note(
            note=f"Pattern Length = {len(self.SCL)}",
            location=[
                0.01,
                0.99],
            use_axes_scale=False,
            fontsize=10,
            axis=1,
            horizontalalignment="left",
            verticalalignment="top")
        Page = LTC_plot.Page(plot_count=1)
        Page.add_plot(G0, plot_sizex=plot_sizex, plot_sizey=plot_sizey)
        Page.create_svg(
            file_basename="TWI Pattern" if file_basename is None else file_basename)
        Page.create_pdf(
            file_basename="TWI Pattern" if file_basename is None else file_basename)


if __name__ == "__main__":
    tbuf = 1300e-9
    thd_sta = 600e-9
    tsu_sto = 600e-9
    thigh = 600e-9
    tlow = 1300e-9
    tsu_dat = 100e-9
    thd_dat = 0

    pattern = TWI_Pattern(tstep=6.65e-9, max_record_size=4096)
    pattern.initialize()
    pattern.add_item(pattern.Leader(pattern, SCL=1, SDA=0, tleader=40e-9))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=tsu_sto, tbuf=tbuf))
    pattern.add_item(pattern.Start(pattern, thd_sta=thd_sta))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=1,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=1,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=0,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=1,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=0,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=0,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=1,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=0,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat))
    pattern.add_item(
        pattern.Bit(
            pattern,
            value=1,
            tlow=tlow,
            thigh=thigh,
            tsu_dat=tsu_dat,
            thd_dat=thd_dat,
            strobe=True))
    pattern.add_item(
        pattern.Leader(
            pattern,
            SCL=0,
            SDA=1,
            tleader=40e-9))  # Release ACK or port hangs
    # Puts the spike between the second and third bits
    pattern.add_item(
        pattern.SCL_Spike(
            pattern,
            value=1,
            tstart=7e-6,
            twidth=20e-9))
    pattern.finalize()
    pattern.visualize(title=r"T$_{LOW}$ Visualizer", file_basename="TLOW")
