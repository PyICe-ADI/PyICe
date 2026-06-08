"""Logger time str utility.

>>> from PyICe.lab_utils.logger_time_str import logger_time_str

"""
from .time_zones import UTC


def logger_time_str(datetime):
    """Format a timezone-aware datetime as the UTC ISO string used by lab_core.logger.

    The logger stores all timestamps in UTC with microsecond precision. This
    function converts from any timezone-aware datetime to that canonical format,
    ensuring consistent time correlation across data collected in different
    time zones.

    >>> from datetime import datetime as dt
    >>> logger_time_str(dt(2024, 3, 15, 12, 30, 45, 123456, tzinfo=UTC()))
    '2024-03-15T12:30:45.123456Z'

    Args:
        datetime: Timezone-aware datetime object. If naive, attach a timezone
            first with ``dt.replace(tzinfo=UTC())``.
    """
    return datetime.astimezone(UTC()).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
