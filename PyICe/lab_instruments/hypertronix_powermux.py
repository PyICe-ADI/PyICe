from ..lab_core import scpi_instrument

class powermux(scpi_instrument):
    '''Boston Design Center 8x8 crosspoint relay mux + 4 aux channels, this needs an example of how to use AUX channels'''
    def __init__(self,interface_visa):
        self._base_name = 'powermux'
        scpi_instrument.__init__(self,f"powermux @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.columns = {}
        self.columns["aux"] = 0 ## aux relays are treated as x=0
        self.rows = {}
        self.board = 0
    def add_channel_relay_names(self,channel_name,column_name,row_name):
        relay_channel = channel(channel_name,write_function=lambda closed: self.set_relay(column_name, row_name, closed) )
        return self._add_channel(relay_channel)
    def add_channel_relay(self,channel_name,column_number,row_number):
        relay_channel = channel(channel_name,write_function=lambda closed: self._set_relay(column_number, row_number, closed) )
        return self._add_channel(relay_channel)
    def add_column(self,column_name,num):
        '''register named column. num is physical column number.  valid range is [1-8] and [0] for auxiliary channels
            column "aux" is predefined '''
        self.columns[column_name] = num
    def add_row(self,row_name,num):
        '''register named row. num is physical row number.  valid range is [1-8] and [1-4] for auxiliary channels
            column "aux" is predefined '''
        self.rows[row_name] = num
    def set_relay(self,column_name,row_name,closed):
        '''open and close a relay by row/column names'''
        if closed:
            self.close_relay(column_name,row_name)
        else:
            self.open_relay(column_name,row_name)
    def _set_relay(self,column_number,row_number,closed):
        cmd = f"{self.board}{column_number}{row_number}"
        if closed:
            self.get_interface().write((f"CLOSe (@{cmd})"))
        else:
            self.get_interface().write((f"OPEN (@{cmd})"))
    def close_relay(self,column_name,row_name):
        '''close relay at named (column, row)'''
        self._set_relay(self.columns[column_name], self.rows[row_name], closed=True)
    def open_relay(self,column_name,row_name):
        '''open relay at named (column, row)'''
        self._set_relay(self.columns[column_name], self.rows[row_name], closed=False)
    def _set_relay_wdelay(self,delay,relay_list,closed):
        '''close or open list of relays at named (column, row) with delay between each'''
        if closed:
            command_string = "CLOSe"
        else:
            command_string = "OPEN"
        command_string += f":DELay (@{delay}"
        for relay in relay_list:
            column_number = relay[0]
            row_number = relay[1]
            command_string += f",{self.board}{column_number}{row_number}"
        command_string += ")"
        self.get_interface().write((command_string))
    def close_relay_wdelay(self,delay,relay_list):
        '''close list of relays at named (column, row) with delay between each'''
        self._set_relay_wdelay(delay,relay_list,closed=True)
    def open_relay_wdelay(self,delay,relay_list):
        '''open list of relays at named (column, row) with delay between each'''
        self._set_relay_wdelay(delay,relay_list,closed=False)
    def open_all(self,sync_channels=False):
        '''open all relays, set sync_channels to true to keep the channels synced (no need to do this if shutting down)'''
        if sync_channels:
            for relay_channel in self.get_all_channels_list():
                relay_channel.write(False)
        else:
            self.get_interface().write(("OPEN ALL"))
    def test(self):
        '''run the built in test routine'''
        self.get_interface().write(("*TST?"))
