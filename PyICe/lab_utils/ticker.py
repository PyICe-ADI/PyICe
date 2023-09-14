import time, csv, urllib.request

class ticker(object):
    def __init__(self,stock_list=None):
        if stock_list is None:
            self.stock_list = ['LLTC', 'ADI', 'TXN', 'AAPL', 'GOOG']
        else:
            self.stock_list = stock_list
    def get_quote(self,symbol):
        url = 'http://finance.yahoo.com/d/quotes.csv?s=+{}&f=snl1'.format(symbol)
        try:
            ticker, desc, price = next(csv.reader([urllib.request.urlopen(url).read()]))
            return {'ticker':ticker.strip().replace('"',''), 'desc':desc.strip().replace('"',''), 'price':price.strip().replace('"','')}
        except Exception as e:
            print(e)
            return {'ticker':None, 'desc':None, 'price':None}
    def build_tape(self):
        self.str = ''
        for stock in self.stock_list:
            data = self.get_quote(stock)
            self.str += '{}: {}   '.format(data['ticker'],data['price'])
        return self.str
    def rotate(self):
        self.str = self.str[1:] + self.str[0]
        return self.str
    def tick(self, display_function=None, character_time=0.15, refresh_time=45):
        if display_function is None:
            display_function = lambda msg: self.disp(msg)
        refresh_cycles = max(int(refresh_time / character_time), 1)
        while True:
            self.build_tape()
            for i in range(refresh_cycles):
                display_function(self.rotate())
                time.sleep(character_time)
    def disp(self, msg):
        print('{}\r'.format(msg), end=' ')