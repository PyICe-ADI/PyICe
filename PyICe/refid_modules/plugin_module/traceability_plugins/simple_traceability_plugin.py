from PyICe.refid_modules.plugin_module.traceability_plugins.traceability_plugin              import traceability_plugin
from PyICe.lab_core import instrument, channel
from jsonc_parser.parser import JsoncParser

class simple_traceability_plugin(traceability_plugin):
    def __init__(self, test_mod, data):
        self.data=data
        self.traceability_channel_names = data.keys()
        super().__init__(test_mod)

    def get_hooks(self):
        plugin_dict = super().get_hooks()
        plugin_dict['pre_collect'] = [self._set_simple_instrument]
        return plugin_dict

    def _set_simple_instrument(self):
        '''Makes an instrument to be added to the master later. Default is making a dummy channel for the instrument and asking for an id. Can be replaced in a child class.'''
        self.instrument = instrument(name="throwaway_traceability_instrument")
        for channel_name, value in self.data.items():
            self.instrument._add_channel(channel(channel_name)).write(value)

    def get_traceability_channels(self):
        return [x for x in self.data]

class JSON_traceability_plugin(simple_traceability_plugin):
    def __init__(self, test_mod, file_location=None):
        parsed_data=JsoncParser.parse_file(file_location)
        super().__init__(test_mod, data=parsed_data)