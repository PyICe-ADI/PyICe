"""Units parser utilities.

>>> from PyICe.data_utils.units_parser import Units_Parser

"""
class Units_Parser():
    """Units_ parser.

    >>> from PyICe.data_utils.units_parser import Units_Parser
    >>> Units_Parser is not None
    True

    """
    def __init__(self):
        """Initialize units_ parser.

        Stores configuration in ``symbols`` for use by other methods.

        >>> from PyICe.data_utils.units_parser import Units_Parser
        >>> obj = Units_Parser()
        >>> isinstance(obj, Units_Parser)
        True

        """
        self.symbols = {
            # ETS DLOG
            "DUT": {"scale": 1, "isunit": True, "DESCRIPTION": "Device Under Test"},
            # ETS DLOG
            "Bits": {"scale": 1, "isunit": True, "DESCRIPTION": "Digital codes"},
            # ETS DLOG
            "BITS": {"scale": 1, "isunit": True, "DESCRIPTION": "Digital codes"},
            # ETS DLOG
            "LSB": {"scale": 1, "isunit": True, "DESCRIPTION": "Digital codes"},
            "NUM": {"scale": 1, "isunit": True, "DESCRIPTION": "???"},  # ETS DLOG

            "Count": {"scale": 1, "isunit": True, "DESCRIPTION": "Count"},
            "Counts": {"scale": 1, "isunit": True, "DESCRIPTION": "Count"},

            "dBuV": {"scale": 1, "isunit": True, "DESCRIPTION": "Decibel Micro Volt ASCII"},
            "dBµV": {"scale": 1, "isunit": True, "DESCRIPTION": "Decibel Micro Volt UTF8"},

            "P|F": {"scale": 1, "isunit": True, "DESCRIPTION": "Use for Pass/Fail results"},
            # ETS "/" OK???
            "T/F": {"scale": 1, "isunit": True, "DESCRIPTION": "Use for True/False results"},
            # ETS "/" OK???
            "P/F": {"scale": 1, "isunit": True, "DESCRIPTION": "Use for Pass/Fail results"},
            "Bool": {"scale": 1, "isunit": True, "DESCRIPTION": "Use for Pass/Fail results"},
            "dBm": {"scale": 1, "isunit": True, "DESCRIPTION": "Decibel Milli Watt"},
            "dBV": {"scale": 1, "isunit": True, "DESCRIPTION": "Decibel Volt"},
            "ppb": {"scale": 1e-6, "isunit": True, "DESCRIPTION": "Part Per Billion"},
            "ppm": {"scale": 1e-6, "isunit": True, "DESCRIPTION": "Part Per Million"},
            "min": {"scale": 1, "isunit": True, "DESCRIPTION": "Minute"},

            "dB": {"scale": 1, "isunit": True, "DESCRIPTION": "Decibel"},
            "Hz": {"scale": 1, "isunit": True, "DESCRIPTION": "Hertz"},
            "HZ": {"scale": 1, "isunit": True, "DESCRIPTION": "Hertz"},  # ETS
            # ETS
            "HERTZ": {"scale": 1, "isunit": True, "DESCRIPTION": "Hertz"},
            "√Hz": {"scale": 1, "isunit": True, "DESCRIPTION": "Square Root Hertz"},
            # Chosen over milli-milli
            "mm": {"scale": 1e-3, "isunit": True, "DESCRIPTION": "Millimeter"},
            "°C": {"scale": 1, "isunit": True, "DESCRIPTION": "Degree Celcius"},
            "°F": {"scale": 1, "isunit": True, "DESCRIPTION": "Degree Farneheit"},
            "V•m": {"scale": 1, "isunit": True, "DESCRIPTION": "Volt•Meter"},
            "Vrms": {"scale": 1, "isunit": True, "DESCRIPTION": "Root mean square Voltage"},
            "eV": {"scale": 1, "isunit": True, "DESCRIPTION": "Electron Volt"},
            "Ω•m": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm•Meter"},
            "Wb": {"scale": 1, "isunit": True, "DESCRIPTION": "Weber"},
            "°": {"scale": 1, "isunit": True, "DESCRIPTION": "Degree Angle"},

            "Å": {"scale": 1e-10, "isunit": True, "DESCRIPTION": "Angstrom"},
            "A": {"scale": 1, "isunit": True, "DESCRIPTION": "Ampere"},
            # ETS
            "AMPS": {"scale": 1, "isunit": True, "DESCRIPTION": "Ampere"},
            "C": {"scale": 1, "isunit": True, "DESCRIPTION": "Coulomb"},
            "F": {"scale": 1, "isunit": True, "DESCRIPTION": "Farad"},
            "J": {"scale": 1, "isunit": True, "DESCRIPTION": "Joule"},
            "H": {"scale": 1, "isunit": True, "DESCRIPTION": "Henry"},
            "K": {"scale": 1, "isunit": True, "DESCRIPTION": "Kelvin"},
            "N": {"scale": 1, "isunit": True, "DESCRIPTION": "Newton"},
            "S": {"scale": 1, "isunit": True, "DESCRIPTION": "Siemen"},
            "V": {"scale": 1, "isunit": True, "DESCRIPTION": "Volt"},
            "VOLTS": {"scale": 1, "isunit": True, "DESCRIPTION": "Volt"},
            "Vpp": {"scale": 1, "isunit": True, "DESCRIPTION": "Volts Peak to Peak"},
            "W": {"scale": 1, "isunit": True, "DESCRIPTION": "Watt"},

            "Ω": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm"},
            "g": {"scale": 1, "isunit": True, "DESCRIPTION": "Gram"},
            "Ohm": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm"},  # ETS
            "OHM": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm"},  # ETS
            "Ohms": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm"},  # ETS
            "OHMS": {"scale": 1, "isunit": True, "DESCRIPTION": "Ohm"},  # ETS
            # ETS
            "KOhms": {"scale": 1e3, "isunit": True, "DESCRIPTION": "Ohm"},
            # This is Mhos but doesn't display
            "℧": {"scale": 1, "isunit": True, "DESCRIPTION": "Mho"},
            "Mhos": {"scale": 1, "isunit": True, "DESCRIPTION": "Mho"},  # ETS
            "MHO": {"scale": 1, "isunit": True, "DESCRIPTION": "Mho"},  # ETS
            "mhos": {"scale": 1, "isunit": True, "DESCRIPTION": "Mho"},  # ETS
            "mho": {"scale": 1, "isunit": True, "DESCRIPTION": "Mho"},  # ETS
            "s": {"scale": 1, "isunit": True, "DESCRIPTION": "Second"},
            "sec": {"scale": 1, "isunit": True, "DESCRIPTION": "Second"},
            # ETS version!
            "Sec": {"scale": 1, "isunit": True, "DESCRIPTION": "Second"},
            # ETS version!
            "SECONDS": {"scale": 1, "isunit": True, "DESCRIPTION": "Second"},
            "h": {"scale": 1, "isunit": True, "DESCRIPTION": "Hour"},
            "Hr": {"scale": 1, "isunit": True, "DESCRIPTION": "Hour"},  # ETS
            "Year": {"scale": 1, "isunit": True, "DESCRIPTION": "Year"},  # ETS
            # ETS
            "Month": {"scale": 1, "isunit": True, "DESCRIPTION": "Month"},
            # ETS
            "Week": {"scale": 1, "isunit": True, "DESCRIPTION": "Week of year, or perhaps week of month."},
            "Day": {"scale": 1, "isunit": True, "DESCRIPTION": "Day"},  # ETS
            # ETS
            "Wafer": {"scale": 1, "isunit": True, "DESCRIPTION": "Wafer number within lot."},
            # ETS
            "Dnum": {"scale": 1, "isunit": True, "DESCRIPTION": "Device Number"},
            "FAIL": {"scale": 1, "isunit": True, "DESCRIPTION": "???"},  # ETS

            "%": {"scale": 1e-2, "isunit": False, "DESCRIPTION": "Percent"},
            "y": {"scale": 1e-24, "isunit": False, "DESCRIPTION": "Yocto"},
            "z": {"scale": 1e-21, "isunit": False, "DESCRIPTION": "Zepto"},
            "a": {"scale": 1e-18, "isunit": False, "DESCRIPTION": "Atto"},
            "f": {"scale": 1e-15, "isunit": False, "DESCRIPTION": "Femto"},
            "p": {"scale": 1e-12, "isunit": False, "DESCRIPTION": "Pico"},
            "n": {"scale": 1e-9, "isunit": False, "DESCRIPTION": "Nano"},
            "u": {"scale": 1e-6, "isunit": False, "DESCRIPTION": "Micro ASCII"},
            "µ": {"scale": 1e-6, "isunit": False, "DESCRIPTION": "Micro UTF8"},
            "m": {"scale": 1e-3, "isunit": False, "DESCRIPTION": "Milli"},
            "k": {"scale": 1e3, "isunit": False, "DESCRIPTION": "Kilo"},
            "M": {"scale": 1e6, "isunit": False, "DESCRIPTION": "Mega"},
            "G": {"scale": 1e12, "isunit": False, "DESCRIPTION": "Giga"},
            # Chosen over [T]esla
            "T": {"scale": 1e18, "isunit": False, "DESCRIPTION": "Tera"},
            "P": {"scale": 1e15, "isunit": False, "DESCRIPTION": "Peta"},
            "E": {"scale": 1e18, "isunit": False, "DESCRIPTION": "Exa"},
            "Z": {"scale": 1e21, "isunit": False, "DESCRIPTION": "Zetta"},
            "Y": {"scale": 1e24, "isunit": False, "DESCRIPTION": "Yotta"},
        }

    def parse(self, units):
        """Return the parse.

        Interprets raw data and returns structured results.


        >>> from PyICe.data_utils.units_parser import Units_Parser
        >>> hasattr(Units_Parser, 'parse')
        True

        Args:
            units: Unit string.

        Returns:
            The parsed data structure.

        Raises:
            Exception: If an unexpected error occurs.
        """
        def viable_symbol(string):
            """Return viable symbol result.

            Performs the described operation on the object's internal state.


            >>> from PyICe.data_utils.units_parser import Units_Parser
            >>> hasattr(Units_Parser, 'viable_symbol')
            True

            Args:
                string: String data.

            Returns:
                The viable symbol result.
            """
            if string == "":
                return True
            for symbol in self.symbols:
                if symbol in string:
                    return True
            return False

        lengths = list(range(1, max(len(symbol)
                       for symbol in self.symbols.keys()) + 1))
        lengths.reverse()  # Always pick out in order: longest to shortest
        multiplier = 1
        divisor = 1
        mult_strings = []
        div_strings = []
        mults = ""
        divs = ""
        tokens = units.replace("•", "").split("/")
        mults = tokens[0]

        for token in tokens[1:]:
            divs += token

        while len(mults) > 0:
            if not viable_symbol(mults):
                raise Exception(
                    f"\n\nUnits Parser: Couldn't find a viable unit or scaler in the string fragment: '{mults}' Given: '{units}'")
            for length in lengths:
                for symbol in self.symbols:
                    if len(symbol) == length and symbol in mults:
                        multiplier = multiplier * self.symbols[symbol]["scale"]
                        mults = mults.replace(symbol, "", 1)
                        if self.symbols[symbol]["isunit"]:
                            mult_strings.append(symbol)

        while len(divs) > 0:
            if not viable_symbol(divs):
                raise Exception(
                    f"\n\nUnits Parser: Couldn't find a viable unit or scaler in the string fragment: '{divs}' Given: '{units}'")
            for length in lengths:
                for symbol in self.symbols:
                    if len(symbol) == length and symbol in divs:
                        divisor = divisor / self.symbols[symbol]["scale"]
                        divs = divs.replace(symbol, "", 1)
                        if self.symbols[symbol]["isunit"]:
                            div_strings.append(symbol)

        return {"MULT": multiplier * divisor, "UNITS": f"{mult_strings}/{div_strings}",
                "NUMERATOR_UNITS": mult_strings, "DENOMINATOR_UNITS": div_strings}


def parser(units):
    """Backward compatible with the old loose function call.

    Performs the described operation on the object's internal state.


    >>> from PyICe.data_utils.units_parser import parser
    >>> callable(parser)
    True

    Args:
        units: Unit string.

    Returns:
        The result of the operation.
    """
    return Units_Parser().parse(units)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            print(f"{arg}:", f"{parser(arg)}")
    else:
        try:
            from examples import examples
        except ImportError:
            examples = ["1.5V", "100mA", "3.3kΩ", "10µF", "25°C"]
        for example in examples:
            print(f"{example}:", f"{parser(example)}")
