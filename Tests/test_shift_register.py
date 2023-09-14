#!/usr/bin/env python

from PyICe import spi_interface, spi_instrument

def setup_inst():
    #All SPI stuff starts with a shift register.
    sr = spi_interface.shift_register(name='test SPI shift register')
    sr.add_bit_field(bit_field_name='test_mode', bit_field_bit_count=4, description='test register')
    sr.add_bit_field(bit_field_name='second', bit_field_bit_count=8, description='second register')
    sr.add_bit_field(bit_field_name='third', bit_field_bit_count=5, description='third register')
    print(sr)

    #Naked shift register without instrument wrapper
    data = {}
    data['test_mode'] = 0b1111
    data['second'] = 3
    data['third'] = 15

    pack = sr.pack(data)
    print(bin(pack[0]))
    print(pack[1])
    unpack = sr.unpack(pack[0])
    print(unpack)

    #Shift registers can be concatenated
    sr2 = spi_interface.shift_register(name='another shift register')
    sr2.add_bit_field('fourth', 13)

    sr_concat = sr + sr2

    #Instrument wrapper using above shift register.
    spi_if = spi_interface.spi_dummy(delay=1,word_size=5)
    spi_if.set_strict_alignment(False) #test automatic data padding
    spi_inst = spi_instrument.spiInstrument(name=sr_concat.get_name(), spiInterface=spi_if, write_shift_register=sr_concat, read_shift_register=sr_concat)
    print(spi_inst.read_all_channels())
    spi_inst['test_mode'].write(0b1111)
    spi_inst['second'].write(3)
    spi_inst['third'].write(15)
    print(spi_inst.read_all_channels())

    spi_inst['fourth'].write(1)
    print(spi_inst.read_all_channels())

    spi_inst['test_mode_readback'].add_preset('test_mode_1', 1)
    spi_inst['test_mode_readback'].add_preset('test_mode_2', 2)
    spi_inst['test_mode_readback'].add_preset('test_mode_3', 3)
    spi_inst['test_mode_readback'].add_preset('test_mode_4', 4)
    spi_inst['test_mode_readback'].add_preset('test_mode_5', 5)
    spi_inst.add_channel_transceive_enable('enable_spi')

    return spi_inst




if __name__ == '__main__':
    from PyICe import lab_core
    m = lab_core.master()
    m.add(setup_inst())
    m['second_readback'].add_change_callback()
    m.write_html('spi.html', sort_categories=True)
    m.gui()