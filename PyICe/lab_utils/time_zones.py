"""Time zones utility."""
import datetime


class US_Time_Zone(datetime.tzinfo):
    """Implement ``datetime.tzinfo`` with US daylight-saving-time rules.

    Handles the DST transition on the second Sunday of March (spring forward)
    and the first Sunday of November (fall back). Subclasses must set the
    following attributes in their ``__init__``:

    - ``tz_name`` – standard-time abbreviation (e.g. ``'EST'``)
    - ``tz_name_dst`` – daylight-time abbreviation (e.g. ``'EDT'``)
    - ``gmt_offset`` – hours offset from UTC in standard time (e.g. ``-5``)
    - ``dst_offset`` – additional hours added during DST (typically ``+1``)

    >>> import datetime
    >>> tz = US_Eastern_Time()
    >>> tz.tzname(datetime.datetime(2024, 1, 15))
    'EST'
    >>> tz.tzname(datetime.datetime(2024, 7, 15))
    'EDT'
    """

    def first_sunday_on_or_after(self, dt):
        """Return the first Sunday on or after *dt*.

        Used internally to locate DST transition dates.

        >>> import datetime
        >>> tz = US_Time_Zone.__new__(US_Time_Zone)
        >>> tz.first_sunday_on_or_after(datetime.datetime(2024, 3, 10))  # already Sunday
        datetime.datetime(2024, 3, 10, 0, 0)
        >>> tz.first_sunday_on_or_after(datetime.datetime(2024, 3, 4)).weekday()  # 0=Mon
        6

        Args:
            dt: A ``datetime.datetime`` (or ``datetime.date``) to start from.

        Returns:
            A ``datetime.datetime`` for the first Sunday ≥ *dt*.
        """
        days_to_go = 6 - dt.weekday()
        # if days_to_go:
        dt += datetime.timedelta(days_to_go)
        return dt

    def utcoffset(self, dt):
        """Return the total UTC offset (standard + DST) for the given datetime.

        >>> import datetime
        >>> US_Eastern_Time().utcoffset(datetime.datetime(2024, 1, 15))
        datetime.timedelta(days=-1, seconds=68400)
        >>> US_Eastern_Time().utcoffset(datetime.datetime(2024, 7, 15))
        datetime.timedelta(days=-1, seconds=72000)

        Args:
            dt: A ``datetime.datetime`` whose date determines whether DST
                is in effect.

        Returns:
            A ``datetime.timedelta`` representing the offset from UTC.
        """
        return datetime.timedelta(hours=self.gmt_offset) + self.dst(dt)  # pylint: disable=no-member; gmt_offset is defined in subclass __init__ (e.g. US_Eastern_Time, US_Pacific_Time)

    def dst(self, dt):
        """Return the DST adjustment for *dt* (one hour or zero).

        >>> import datetime
        >>> US_Eastern_Time().dst(datetime.datetime(2024, 1, 15))
        datetime.timedelta(0)
        >>> US_Eastern_Time().dst(datetime.datetime(2024, 7, 15))
        datetime.timedelta(seconds=3600)

        Args:
            dt: A ``datetime.datetime`` whose date determines whether DST
                is active.

        Returns:
            ``datetime.timedelta(hours=dst_offset)`` during DST, otherwise
            ``datetime.timedelta(0)``.
        """
        # DST starts second Sunday in March
        # ends first Sunday in November
        self.dston = self.first_sunday_on_or_after(
            datetime.datetime(dt.year, 4, 8))
        self.dstoff = self.first_sunday_on_or_after(
            datetime.datetime(dt.year, 11, 1))
        if self.dston <= dt.replace(tzinfo=None) < self.dstoff:
            return datetime.timedelta(hours=self.dst_offset)  # pylint: disable=no-member; dst_offset is defined in subclass __init__ (e.g. US_Eastern_Time, US_Pacific_Time)
        else:
            return datetime.timedelta(0)

    def tzname(self, dt):
        """Return the timezone abbreviation, switching for DST.

        >>> import datetime
        >>> US_Pacific_Time().tzname(datetime.datetime(2024, 12, 1))
        'PST'
        >>> US_Pacific_Time().tzname(datetime.datetime(2024, 6, 1))
        'PDT'

        Args:
            dt: A ``datetime.datetime`` whose date determines whether DST
                is active.

        Returns:
            The standard or daylight-saving timezone abbreviation string
            (e.g. ``'EST'`` or ``'EDT'``).
        """
        if self.dst(dt):
            return self.tz_name_dst  # pylint: disable=no-member; tz_name_dst is defined in subclass __init__ (e.g. US_Eastern_Time, US_Pacific_Time)
        return self.tz_name  # pylint: disable=no-member; tz_name is defined in subclass __init__ (e.g. US_Eastern_Time, US_Pacific_Time)


class UTC(US_Time_Zone):
    """UTC / GMT / Zulu time zone (no DST adjustment).

    >>> import datetime
    >>> UTC().utcoffset(datetime.datetime(2024, 7, 15))
    datetime.timedelta(0)
    """

    def __init__(self):
        """Set UTC parameters (zero offset, no DST)."""
        self.tz_name = "UTC"
        self.tz_name_dst = "UTC"
        self.gmt_offset = +0
        self.dst_offset = +0


class US_Eastern_Time(US_Time_Zone):
    """US Eastern time zone (EST/EDT, UTC−5 / UTC−4).

    >>> import datetime
    >>> US_Eastern_Time().tzname(datetime.datetime(2024, 1, 15))
    'EST'
    """

    def __init__(self):
        """Set Eastern-timezone parameters (GMT−5, +1 h DST)."""
        self.tz_name = "EST"
        self.tz_name_dst = "EDT"
        self.gmt_offset = -5
        self.dst_offset = +1


class US_Pacific_Time(US_Time_Zone):
    """US Pacific time zone (PST/PDT, UTC−8 / UTC−7).

    >>> import datetime
    >>> US_Pacific_Time().tzname(datetime.datetime(2024, 1, 15))
    'PST'
    """

    def __init__(self):
        """Set Pacific-timezone parameters (GMT−8, +1 h DST)."""
        self.tz_name = "PST"
        self.tz_name_dst = "PDT"
        self.gmt_offset = -8
        self.dst_offset = +1
