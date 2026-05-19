import time
import csv
import urllib.request


class ticker(object):
    """Ticker (object subclass)."""
    def __init__(self, stock_list=None):
        if stock_list is None:
            self.stock_list = ['LLTC', 'ADI', 'TXN', 'AAPL', 'GOOG']
        else:
            self.stock_list = stock_list

    def get_quote(self, symbol):
        """Return the quote.

        Args:
            symbol: Symbol.

        Returns:
            Result value.
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
        """Return build tape result.

        Returns:
            Result value.
        """
        self.str = ''
        for stock in self.stock_list:
            data = self.get_quote(stock)
            self.str += '{}: {}   '.format(data['ticker'], data['price'])
        return self.str

    def rotate(self):
        """Return rotate result.

        Returns:
            Result value.
        """
        self.str = self.str[1:] + self.str[0]
        return self.str

    def tick(self, display_function=None,
             character_time=0.15, refresh_time=45):
        """Return tick result.

        Args:
            character_time: Character time.
            display_function: Display function.
            refresh_time: Refresh time.
        """
        if display_function is None:
            def display_function(msg):
                """Return display function result.

                Args:
                    msg: Msg.

                Returns:
                    Result value.
                """
                return self.disp(msg)
        refresh_cycles = max(int(refresh_time / character_time), 1)
        while True:
            self.build_tape()
            for i in range(refresh_cycles):
                display_function(self.rotate())
                time.sleep(character_time)

    def disp(self, msg):
        """Perform disp operation.

        Args:
            msg: Msg.
        """
        print('{}\r'.format(msg), end=' ')
