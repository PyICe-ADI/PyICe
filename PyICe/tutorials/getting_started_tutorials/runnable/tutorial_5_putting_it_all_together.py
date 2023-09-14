# ==================================
# TUTORIAL 5 Putting it all Together
# ==================================

from PyICe import lab_interfaces

interface_factory = lab_interfaces.interface_factory()

a34401_interface = interface_factory.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)
supply_interface = interface_factory.get_visa_serial_interface("COM16", baudrate=115200, rtscts=True, timeout=10)

from PyICe import lab_instruments

meter = lab_instruments.agilent_34401a(a34401_interface)
meter.add_channel("vresistor_vsense")
meter.config_dc_voltage()

hameg = lab_instruments.hameg_4040(supply_interface)
hameg.add_channel(channel_name="vsweep", num=3, ilim=1, delay=0.25)
hameg.add_channel_current(channel_name="current_limit", num=3)

from PyICe import lab_core

bench = lab_core.channel_master()
bench.add(meter)
bench.add(hameg)

from PyICe import lab_utils
from PyICe import LTC_plot

logger = lab_core.logger(bench)
logger.new_table(table_name='diode_data_table', replace_table=True)
bench.write('current_limit', 0.5)

for vsweep in lab_utils.floatRangeInc(0, 6, 0.025):
   print(f"Setting voltage to {vsweep}V")
   bench.write('vsweep', vsweep)
   logger.log()
bench.write('vsweep', 0)

database = lab_utils.sqlite_data(table_name="diode_data_table", database_file="data_log.sqlite")            

#########################################################################
#                                                                       #
# Laser Diode Assembly Current vs Voltage
#                                                                       #
#########################################################################
G1 = LTC_plot.plot(plot_title   = "Laser Diode Assembly Current vs\nApplied Voltage",
                  plot_name    = "G1",
                  xaxis_label  = "ASSEMBLY VOLTAGE (V)",
                  yaxis_label  = "ASSEMBLY CURRENT (mA)",
                  xlims        = (0, 6),
                  ylims        = (0, 40),
                  xminor       = 0,
                  xdivs        = 6,
                  yminor       = 2,
                  ydivs        = 4,
                  logx         = False,
                  logy         = False)
database.query('SELECT vsweep_vsense, vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
G1.add_trace(   axis    = 1,
               data    = database.to_list(),
               color   = LTC_plot.LT_RED_1,
               legend  = "")
database.query('SELECT vresistor_vsense, vsweep_isense FROM diode_data_table WHERE vsweep==6')
V_6V, I_6V = database[0]
database.query('SELECT vresistor_vsense, vsweep_isense FROM diode_data_table WHERE vsweep==3')
V_3V, I_3V = database[0]
rmeasured = (V_6V - V_3V) / (I_6V - I_3V)
G1.add_note(note=r"$R_{SERIES}=$" + f"{rmeasured:0.2f}Ω", location=[0.1, 36], use_axes_scale=True, fontsize=9, axis=1, horizontalalignment="left", verticalalignment="bottom")
#########################################################################
#                                                                       #
#########################################################################


#########################################################################
#                                                                       #
# Laser Diode Assembly Current vs Raw Laser Diode Voltage
#                                                                       #
#########################################################################
G2 = LTC_plot.plot(plot_title   = "Laser Diode Current vs\nRaw Diode Voltage",
                  plot_name    = "G2",
                  xaxis_label  = "DIODE VOLTAGE (V)",
                  yaxis_label  = "DIODE CURRENT (mA)",
                  xlims        = (1.6, 2.4),
                  ylims        = (0.3, 40),
                  xminor       = 2,
                  xdivs        = 4,
                  yminor       = 1,
                  ydivs        = 4,
                  logx         = False,
                  logy         = True) # <---- Note Log scale
database.query('SELECT vsweep_vsense - vresistor_vsense, vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense - vresistor_vsense')
G2.add_trace(   axis    = 1,
               data    = database.to_list(),
               color   = LTC_plot.LT_RED_1,
               legend  = "")
#########################################################################
#                                                                       #
#########################################################################


#########################################################################
#                                                                       #
# Laser Diode Assembly Total Power and Diode Power vs Applied Voltage
#                                                                       #
#########################################################################
G3 = LTC_plot.plot( plot_title  = "Power of the Laser Diode Assembly\nand Raw Laser Diode",
                  plot_name    = "G3",
                  xaxis_label  = "VOLTAGE (V)",
                  yaxis_label  = "POWER (mW)",
                  xlims        = (0, 6),
                  ylims        = (0, 240),
                  xminor       = 0,
                  xdivs        = 6,
                  yminor       = 0,
                  ydivs        = 6,
                  logx         = False,
                  logy         = False)
database.query('SELECT vsweep_vsense, vsweep_vsense * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
G3.add_trace(   axis    = 1,
               data    = database.to_list(),
               color   = LTC_plot.LT_RED_1,
               legend  = r"$P_{ASSY}$")
database.query('SELECT vsweep_vsense, (vsweep_vsense - vresistor_vsense) * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
G3.add_trace(   axis    = 1,
               data    = database.to_list(),
               color   = LTC_plot.LT_BLUE_1,
               legend  = r"$P_{DIODE}$")
G3.add_legend(axis=1, location=(1, 0), justification='lower left', use_axes_scale=False, fontsize=7)
#########################################################################
#                                                                       #
#########################################################################


#########################################################################
#                                                                       #
# Raw Laser Diode Power vs Diode Current
#                                                                       #
#########################################################################
G4 = LTC_plot.plot( plot_title  = "Power of the Raw Laser Diode\nvs Diode Current" + r"$^{*}$",
                  plot_name    = "G4",
                  xaxis_label  = "CURRENT (mA)",
                  yaxis_label  = "POWER (mW)",
                  xlims        = (0, 40),
                  ylims        = (0, 100),
                  xminor       = 0,
                  xdivs        = 4,
                  yminor       = 0,
                  ydivs        = 5,
                  logx         = False,
                  logy         = False)
database.query('SELECT vsweep_isense * 1e3, (vsweep_vsense - vresistor_vsense) * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_isense')
G4.add_trace(   axis    = 1,
               data    = database.to_list(),
               color   = LTC_plot.LT_RED_1,
               legend  = r"")
G4.add_note(note= r"$^{*}$" + "Diode current is the same\n as the assembly current", location=[0.05, 0.95], use_axes_scale=False, fontsize=7, axis=1, horizontalalignment="left", verticalalignment="top")
#########################################################################
#                                                                       #
#########################################################################


#########################################################################
#                                                                       #
# Assembling and Generating the Pages
#                                                                       #
#########################################################################

Page1 = LTC_plot.Page(rows_x_cols=(1, 2), page_size=None)
Page1.add_plot(G1, position=1)
Page1.add_plot(G2, position=2)

Page2 = LTC_plot.Page(rows_x_cols=(1, 2), page_size=None)
Page2.add_plot(G3, position=1)
Page2.add_plot(G4, position=2)

Multipage = LTC_plot.Multipage_pdf()
Multipage.add_page(Page1)
Multipage.add_page(Page2)

Multipage.create_pdf("Laser Diode Test")