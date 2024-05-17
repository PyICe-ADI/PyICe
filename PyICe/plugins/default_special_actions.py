from PyICe.lab_utils.banners import print_banner

class Default_channel_checks():
    def __init__(self, condition):
        self.condition = condition
        self._count = 0

    def alert(self, channel_name, readings, test):
        '''A standard action that will throw up a banner if the reading of the assigned channel fails the condition defined at initiation.'''
        if self._count == 0 and self.condition(readings[channel_name]):
            pass
        elif self._count == 0 and not self.condition(readings[channel_name]):
            print_banner(f'WARNING: {channel_name} has failed to maintain its pass condition.')
            # if 'notify' in FIGURE OUT WHERE:
                # notify(f'WARNING: {channel_name} has failed to maintain its pass condition.')
            self._count+=1
        elif self._count != 0 and self.condition(readings[channel_name]):
            print_banner(f'CONGRATS: {channel_name} has reentered its pass condition after {self._count} logs!')
            self._count = 0
        else:
            self._count+=1

    def abort(self, channel_name, readings, test):
    '''A standard action that will crash the running test if the reading of the assigned channel fails the condition defined at initiation.'''
        if self.condition(readings[channel_name]):
            pass
        else:
            # notify(f'WARNING: {channel_name} has failed to maintain its mandatory state. Data has been compromised. Aborting test.')
            raise Exception(f'WARNING: {channel_name} has failed to maintain its mandatory state. Data has been compromised. Aborting test.')
    