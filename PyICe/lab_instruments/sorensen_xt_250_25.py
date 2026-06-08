"""Sorensen xt 250 25 instrument driver.

>>> from PyICe.lab_instruments.sorensen_xt_250_25 import sorensen_xt_250_25

"""
from ..lab_core import *  # noqa: F403
from .sorensen_generic_supply import *  # noqa: F403


class sorensen_xt_250_25(sorensen_generic_supply):
    """Single channel sorensen_xt_250_25."""

    def __init__(self, interface_visa):
        """Initialize sorensen_xt_250_25.
        Stores configuration in ``_base_name``, ``sorensen_name`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self.sorensen_name = "sorensen_xt_250_25"
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_xt_250_25'
