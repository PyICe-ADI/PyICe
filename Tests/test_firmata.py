from PyICe import lab_core, lab_instruments

m = lab_core.master()

firmata = lab_instruments.firmata('com4')

firmata.add_channel_digital_output('pin2_out', 2)
firmata.add_channel_digital_output('pin3_out', 3)
firmata.add_channel_digital_input('pin4_in', 4)
firmata.add_channel_pwm_output('pin5_pwm', 5)
firmata.add_channel_digital_input('pin6_in_pu', 6, enable_pullup=True)
firmata.add_channel_digital_latch('latch6', firmata['pin6_in_pu'], threshold_high=False)
firmata.add_channel_digital_output('pinA3_dig_out', 14+3)
firmata.add_channel_digital_input('pinA4_dig_in', 14+4)
firmata.add_channel_analog_input('pinA1_in', 1)
firmata.add_channel_analog_latch('latchA1', firmata['pinA1_in'], 3)

m.add(firmata)

# m.gui()

from PyICe import spi_interface, spi_instrument

sr = spi_interface.shift_register()
sr.add_bit_field('bit_field_1',4)
sr.add_bit_field('bit_field_2',8)
sr.add_bit_field('bit_field_3',5)
print(sr)

spi_if = spi_interface.spi_bitbang(SCK_channel=firmata.add_channel_digital_output('SCK',8),
                     MOSI_channel=firmata.add_channel_digital_output('MOSI',9),
                     MISO_channel=None,
                     SS_channel=firmata.add_channel_digital_output('_SS',10), 
                     CPOL=0,
                     CPHA=0,
                     SS_POL=0,
                     low_level=0,
                     high_level=1)

spi_inst = spi_instrument.spiInstrument(name='spi_test_instrument', spiInterface=spi_if, write_shift_register=sr)

m.add(spi_inst)

m['bit_field_1'].write(1)
m['bit_field_2'].write(2)
m['bit_field_3'].write(3)

m.gui()
