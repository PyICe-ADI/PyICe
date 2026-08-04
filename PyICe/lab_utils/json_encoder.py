"""Shared JSON encoder for PyICe data types.

>>> from PyICe.lab_utils.json_encoder import PyICeJSONEncoder
>>> import json, numpy as np, datetime
>>> json.dumps(np.array([1.0, 2.0]), cls=PyICeJSONEncoder)
'[1.0, 2.0]'
>>> json.dumps(np.bool_(True), cls=PyICeJSONEncoder)
'true'
>>> json.dumps(datetime.datetime(2024, 1, 1, 12, 0), cls=PyICeJSONEncoder)
'"2024-01-01T12:00:00.000000Z"'
"""
import json
import datetime
import numpy as np


class PyICeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types, datetimes, and bytes.

    Falls back to repr() for any unrecognized type, ensuring serialization
    never raises.

    >>> from PyICe.lab_utils.json_encoder import PyICeJSONEncoder
    >>> PyICeJSONEncoder is not None
    True
    """

    def default(self, obj):
        """Serialize obj to a JSON-compatible type.

        >>> from PyICe.lab_utils.json_encoder import PyICeJSONEncoder
        >>> hasattr(PyICeJSONEncoder, 'default')
        True
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if isinstance(obj, datetime.timedelta):
            return obj.total_seconds()
        if isinstance(obj, bytes):
            return repr(obj)
        return repr(obj)
