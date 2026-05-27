"""Sorensen lhp 100 10 instrument driver.

>>> from PyICe.lab_instruments.sorensen_lhp_100_10 import sorensen_lhp_100_10

"""
from ..lab_core import *  # noqa: F403
from .sorensen_generic_supply import *  # noqa: F403


class sorensen_lhp_100_10(sorensen_generic_supply):
    """Single channel sorensen_lhp_100_10."""

    def __init__(self, interface_visa):
        """Initialize sorensen_lhp_100_10.
        Stores configuration in ``_base_name``, ``sorensen_name`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self.sorensen_name = "sorensen_lhp_100_10"
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_lhp_100_10'
