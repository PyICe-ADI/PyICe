from PyICe.lab_utils.banners import print_banner
from PyICe.lab_core import channel
import datetime

class traceability_items():
    def __init__(self, test, warn_only=True):
        self.item_list=[]
        self.trace_data={}
        self.warn_only=warn_only
        self.test = test
    def add(self, channel_name, func):
        self.item_list.append({'channel_name':channel_name, 'func':func})
    def populate_traceability_data(self):
        for item in self.item_list:
            self.trace_data[item['channel_name']] = item['func'](self.test)
    def get_traceability_data(self):
        return self.trace_data
    def add_data_to_metalogger(self, logger):
        for channel_name in self.trace_data:
            new_channel=channel(name=channel_name)
            logger.add_channel(new_channel)
            try:
                logger.write(channel_name, self.trace_data[channel_name])
            except:
                string = f"\n\nPYICE TRACEABILITY ITEMS ERROR: Attempt to populate {channel_name} unsuccessful.\n\n"
                if warn_only:
                    print_banner(string)
                else:
                    raise(string)