from PyICe.refid_modules.plugin_module.traceability_plugins.traceability_plugin              import traceability_plugin
from PyICe.lab_core import instrument, channel
import abc

class board_traceability_plugin(traceability_plugin):
    def __init__(self, test_mod):
        super().__init__(test_mod)

    def get_hooks(self):
        plugin_dict = super().get_hooks()
        plugin_dict['tm_logger_setup'].insert(0,self._set_board_instrument)
        return plugin_dict

    def _set_board_instrument(self, *args, **kwargs):
        '''Makes an instrument to be added to the master later. Default is making a dummy channel for the instrument and asking for an id. Can be replaced in a child class.'''
        self.instrument = instrument(name="board_instrument")
        ch_cat = 'traceability_info'
        for (new_channel,value) in self._add_channels().items():
            self.instrument._add_channel(channel(new_channel))
            self.instrument.write_channel(new_channel, value)
            self.instrument[new_channel].set_category(ch_cat)

    @abc.abstractmethod
    def _add_channels(self):
        '''
        add in channel names and values from the provided location.
        '''
        return {}
