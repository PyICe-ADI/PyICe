import datetime

class US_Time_Zone(datetime.tzinfo):
    '''Generic Timezone parent class.
    Implements methods required by datetime.tzinfo with US DST rules (second Sunday of March and first Sunday of November).
    Requires subclass to define local timezone parameters:
        self.tz_name
        self.tz_name_dst
        self.gmt_offset
        self.dst_offset
    '''
    def first_sunday_on_or_after(self,dt):
        '''return date of first Sunday on or after dt.'''
        days_to_go = 6 - dt.weekday()
        #if days_to_go:
        dt += datetime.timedelta(days_to_go)
        return dt
    def utcoffset(self, dt):
        '''return DST aware offset from GMT/UTC based on calendar date.'''
        return datetime.timedelta(hours=self.gmt_offset) + self.dst(dt)
    def dst(self, dt):
        '''return DST offset from standard local time based on calendar date.'''
        # DST starts second Sunday in March
        # ends first Sunday in November
        self.dston = self.first_sunday_on_or_after(datetime.datetime(dt.year, 4, 8))
        self.dstoff = self.first_sunday_on_or_after(datetime.datetime(dt.year, 11, 1))
        if self.dston <= dt.replace(tzinfo=None) < self.dstoff:
            return datetime.timedelta(hours=self.dst_offset)
        else:
            return datetime.timedelta(0)
    def tzname(self,dt):
        '''return DST aware local time zone name based on calendar date.'''
        if self.dst(dt):
            return self.tz_name_dst
        return self.tz_name
class UTC(US_Time_Zone):
    '''UTC / GMT / Zulu time zone.'''
    def __init__(self):
        self.tz_name = "UTC"
        self.tz_name_dst = "UTC"
        self.gmt_offset = +0
        self.dst_offset = +0
class US_Eastern_Time(US_Time_Zone):
    '''US Eastern time zone. (NYC/BOS)'''
    def __init__(self):
        self.tz_name = "EST"
        self.tz_name_dst = "EDT"
        self.gmt_offset = -5
        self.dst_offset = +1
class US_Pacific_Time(US_Time_Zone):
    '''US Pacific time zone. (LAX/SMF)'''
    def __init__(self):
        self.tz_name = "PST"
        self.tz_name_dst = "PDT"
        self.gmt_offset = -8
        self.dst_offset = +1