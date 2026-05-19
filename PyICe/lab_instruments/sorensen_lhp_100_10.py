"""Sorensen lhp 100 10 instrument driver."""
from ..lab_core import *  # noqa: F403
from .sorensen_generic_supply import *  # noqa: F403


class sorensen_lhp_100_10(sorensen_generic_supply):
    """Single channel sorensen_lhp_100_10."""

    def __init__(self, interface_visa):
        self.sorensen_name = "sorensen_lhp_100_10"
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_lhp_100_10'
