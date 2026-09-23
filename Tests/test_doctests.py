"""Collect and run doctests from pure utility modules and lab_core."""
import doctest
import pytest

from PyICe.lab_utils import eng_string
from PyICe.lab_utils import str2num as str2num_mod
from PyICe.lab_utils import ordinalize as ordinalize_mod
from PyICe.lab_utils import swap_endian as swap_endian_mod
from PyICe.lab_utils import signedToTwosComplement as s2tc_mod
from PyICe.lab_utils import twosComplementToSigned as tc2s_mod
from PyICe.lab_utils import signExtend as sign_extend_mod
from PyICe.lab_utils import safe_divide as safe_divide_mod
from PyICe.lab_utils import bounded as bounded_mod
from PyICe.lab_utils import isclose as isclose_mod
from PyICe.lab_utils import parse_list as parse_list_mod
from PyICe.lab_utils import clean_unicode as clean_unicode_mod
from PyICe.lab_utils import clean_ascii_code as clean_ascii_mod
from PyICe.lab_utils import clean_sql as clean_sql_mod
from PyICe.lab_utils import ranges as ranges_mod
from PyICe.lab_utils import float_next as float_next_mod
from PyICe.lab_utils import float_prior as float_prior_mod
from PyICe.lab_utils import expand_tabs as expand_tabs_mod
from PyICe import lab_core as lab_core_mod
from PyICe.models import comparator as comparator_mod
from PyICe import twi_interface as twi_mod
from PyICe import ipxact_parser as ipxact_mod
from PyICe import virtual_instruments as vi_mod
from PyICe.lab_utils import interpolator as interpolator_mod
from PyICe.data_utils import units_conversions as units_mod

MODULES_WITH_DOCTESTS = [
    eng_string,
    str2num_mod,
    ordinalize_mod,
    swap_endian_mod,
    s2tc_mod,
    tc2s_mod,
    sign_extend_mod,
    safe_divide_mod,
    bounded_mod,
    isclose_mod,
    parse_list_mod,
    clean_unicode_mod,
    clean_ascii_mod,
    clean_sql_mod,
    ranges_mod,
    float_next_mod,
    float_prior_mod,
    expand_tabs_mod,
    lab_core_mod,
    comparator_mod,
    twi_mod,
    vi_mod,
    interpolator_mod,
    units_mod,
    ipxact_mod,
]


@pytest.mark.parametrize("module", MODULES_WITH_DOCTESTS,
                         ids=lambda m: m.__name__)
def test_doctest(module):
    """Perform test doctest operation.

    Args:
        module: Module.
    """
    results = doctest.testmod(
        module, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
    assert results.failed == 0, f"{results.failed} doctest(s) failed in {module.__name__}"
