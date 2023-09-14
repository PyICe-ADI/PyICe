import pytest
from PyICe.twi_instrument import twi_instrument
from PyICe.lab_core import channel_master
from PyICe.lab_interfaces import interface_factory


fact = interface_factory()
@pytest.fixture()
def twi_inter():
    interface = fact.get_twi_dummy_interface()
    return interface

@pytest.fixture()
def twi_inst(twi_inter):
    inst = twi_instrument(twi_inter)
    return inst


class TestTwiInstrument:

    def test_add_register(self, twi_inst):
        print('test)')
        twi_inst.add_register(name='ex_register',
                              addr7='0x70',
                              command_code=12,
                              size=8,
                              offset=16,
                              word_size=16,
                              is_readable=True,
                              is_writable=False)
        chan = twi_inst.get_channel('ex_register')
        assert chan.read() == 0
        with pytest.raises(Exception):
            twi_inst.add_register(name='new_reg',
                                  addr7='0x90',
                                  command_code=12,
                                  size=8,
                                  offset=16,
                                  word_size=16,
                                  is_readable=True,
                                  is_writable=False)
        twi_inst.add_register(name='single_bit',
                              addr7='0x70',
                              command_code=12,
                              size=1,
                              offset=16,
                              word_size=0,
                              is_readable=False,
                              is_writable=True)
        chan = twi_inst.get_channel('single_bit')
        # chan.write('Send') This should have worked? non in "Send"?

    def test_add_channel_ARA(self, twi_inst):
        twi_inst.add_channel_ARA('alert')
        chan = twi_inst.get_channel('alert')
        result = chan.read()
        assert type(result) is int  # bad practice to return random numbers









