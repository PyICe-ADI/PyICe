"""Ticker utility.

>>> from PyICe.lab_utils.ticker import ticker

"""
import time
import csv
import urllib.request


class ticker(object):
    """Fetch live stock quotes from Yahoo Finance and scroll them as a ticker tape.

    >>> from PyICe.lab_utils.ticker import ticker
    >>> ticker is not None
    True

    """
    def __init__(self, stock_list=None):
        """Create a ticker for a list of stock symbols.
        Stores configuration in ``stock_list`` for use by other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> ticker is not None
        True

        Args:
            stock_list: Iterable of ticker symbols to track (e.g.
                ``['AAPL', 'GOOG']``).  Defaults to a built-in list if
                not provided.
        """
        if stock_list is None:
            self.stock_list = ['LLTC', 'ADI', 'TXN', 'AAPL', 'GOOG']
        else:
            self.stock_list = stock_list

    def get_quote(self, symbol):
        """Fetch a single stock quote from Yahoo Finance.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> hasattr(ticker, 'get_quote')
        True

        Args:
            symbol: Ticker symbol string (e.g. ``'AAPL'``).

        Returns:
            Dict with keys ``'ticker'``, ``'desc'``, and ``'price'``, each
            a string.  All values are ``None`` if the request fails.
        """
        url = 'http://finance.yahoo.com/d/quotes.csv?s=+{}&f=snl1'.format(
            symbol)
        try:
            ticker, desc, price = next(csv.reader(
                [urllib.request.urlopen(url).read()]))
            return {'ticker': ticker.strip().replace('"', ''), 'desc': desc.strip(
            ).replace('"', ''), 'price': price.strip().replace('"', '')}
        except Exception as e:
            print(e)
            return {'ticker': None, 'desc': None, 'price': None}

    def build_tape(self):
        """Fetch quotes for all symbols and concatenate them into a single tape string.

        Retrieves data from the remote endpoint.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> hasattr(ticker, 'build_tape')
        True

        Returns:
            A string like ``'AAPL: 150.00   GOOG: 2800.00   '`` ready for
            scrolling display.
        """
        self.str = ''
        for stock in self.stock_list:
            data = self.get_quote(stock)
            self.str += '{}: {}   '.format(data['ticker'], data['price'])
        return self.str

    def rotate(self):
        """Rotate the tape string one character to the left, wrapping around.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> hasattr(ticker, 'rotate')
        True

        Returns:
            The rotated tape string, giving the visual effect of scrolling text.
        """
        self.str = self.str[1:] + self.str[0]
        return self.str

    def tick(self, display_function=None,
             character_time=0.15, refresh_time=45):
        """Run an infinite scrolling ticker-tape loop.

        Fetches fresh quotes every *refresh_time* seconds while scrolling the
        tape one character at a time.  Blocks forever; intended for demo or
        idle-screen use.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> hasattr(ticker, 'tick')
        True

        Args:
            display_function: Callable that accepts a string to render one
                frame of the ticker.  Defaults to :meth:`disp` (console
                carriage-return overwrite).
            character_time: Seconds to wait between each one-character scroll
                step (controls scroll speed).
            refresh_time: Seconds between full quote re-fetches from Yahoo.
        """
        if display_function is None:
            def display_function(msg):
                """Print *msg* via :meth:`disp` (default display callback).

                Hooks into the event system so that custom logic runs at the appropriate time.


                >>> from PyICe.lab_utils.ticker import ticker
                >>> hasattr(ticker, 'display_function')
                True

                Args:
                    msg: Ticker string to display.
                """
                return self.disp(msg)
        refresh_cycles = max(int(refresh_time / character_time), 1)
        while True:
            self.build_tape()
            for i in range(refresh_cycles):
                display_function(self.rotate())
                time.sleep(character_time)

    def disp(self, msg):
        """Print *msg* to the console with a carriage return, overwriting the current line.


        >>> from PyICe.lab_utils.ticker import ticker
        >>> hasattr(ticker, 'disp')
        True

        Args:
            msg: The ticker-tape string to display.
        """
        print('{}\r'.format(msg), end=' ')
