import datetime

def logger_time_str(datetime):
    '''return time string in same format as used by lab_core.logger.
    Requires timezone-aware datetime object argument to correctly convert to UTC times used by logger.
    if datetime object is naieve of timezone, add it with datetime.replace(tzinfo=lab_utils.US_Eastern_Time()) or datetime.replace(tzinfo=lab_utils.UTC())
    '''
    return datetime.astimezone(UTC()).strftime('%Y-%m-%dT%H:%M:%S.%fZ')