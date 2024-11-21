from PyICe.lab_core import channel
import collections

class Traceability_items():
    def __init__(self, test):
        self.item_list = []
        self.test = test
        self.trace_data = collections.OrderedDict()
    def add(self, channel_name, func):
        self.item_list.append({'channel_name':channel_name, 'func':func})
    def populate_traceability_data(self, traceables):
        for channel_name in traceables:
            self.trace_data[channel_name] = traceables[channel_name](self.test)
    def get_traceability_data(self):
        return self.trace_data
    def add_data_to_metalogger(self, logger):
        for channel_name in self.trace_data:
            new_channel=channel(name=channel_name)
            logger.add_channel(new_channel)
            logger.write(channel_name, self.trace_data[channel_name])