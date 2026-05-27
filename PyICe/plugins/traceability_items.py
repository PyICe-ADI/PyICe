"""Traceability items plugin.

>>> from PyICe.plugins.traceability_items import Traceability_items

"""
from PyICe.lab_core import channel
import collections


class Traceability_items():
    """Traceability_items.

    >>> from PyICe.plugins.traceability_items import Traceability_items
    >>> Traceability_items is not None
    True

    """
    def __init__(self, test):
        """Initialize traceability_items.
        Stores configuration in ``item_list``, ``test``, ``trace_data`` for
        use by other methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.traceability_items import Traceability_items
        >>> Traceability_items is not None
        True

        Args:
            test: Test case object or test function.
        """
        self.item_list = []
        self.test = test
        self.trace_data = collections.OrderedDict()

    def add(self, channel_name, func):
        """Run the add step.

        Supports the ``Traceability_items`` workflow by performing the described operation.


        >>> from PyICe.plugins.traceability_items import Traceability_items
        >>> hasattr(Traceability_items, 'add')
        True

        Args:
            channel_name: Name for the new channel.
            func: Func to use.
        """
        self.item_list.append({'channel_name': channel_name, 'func': func})

    def populate_traceability_data(self, traceables):
        """Perform populate traceability data operation.

        Supports the ``Traceability_items`` workflow by performing the described operation.


        >>> from PyICe.plugins.traceability_items import Traceability_items
        >>> hasattr(Traceability_items, 'populate_traceability_data')
        True

        Args:
            traceables: Traceables to use.
        """
        for channel_name in traceables:
            self.trace_data[channel_name] = traceables[channel_name](self.test)

    def get_traceability_data(self):
        """Return the traceability data.
        Returns the stored traceability data value from the object's internal
        state.
        Returns the stored traceability data from the object's internal state.

        Returns the stored traceability data from the object's internal state.


        >>> from PyICe.plugins.traceability_items import Traceability_items
        >>> hasattr(Traceability_items, 'get_traceability_data')
        True

        Returns:
            The current traceability data.
        """
        return self.trace_data

    def add_data_to_metalogger(self, logger):
        """Add a data to metalogger.

        Appends a new data to metalogger entry to the object's internal collection.


        >>> from PyICe.plugins.traceability_items import Traceability_items
        >>> hasattr(Traceability_items, 'add_data_to_metalogger')
        True

        Args:
            logger: Logger instance for data recording.
        """
        for channel_name in self.trace_data:
            new_channel = channel(name=channel_name)
            logger.add_channel(new_channel)
            logger.write(channel_name, self.trace_data[channel_name])
