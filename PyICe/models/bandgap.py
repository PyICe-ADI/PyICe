import random, numpy

class bandgap():
    def __init__(self):
        self.vbe27      = random.gauss(mu=0.66, sigma=250e-6)
        self.Nemit      = random.gauss(mu=12, sigma=0.1)
        self.dvbe_gain   = random.gauss(mu=23/3., sigma=23/3.*0.0025)
        self.VTO        = random.gauss(mu=1.235, sigma=0.001)
        self.trim_lsb   = 0.0014
        self.K          = 1.380649e-23
        self.q          = 1.602176634e-19
    def set_trimval(self, trimcode):
        if not isinstance(trimcode, int):
            print(f"\n\nSorry, my bandgap bits don't take the value: {trimcode}\n\n")
            exit()
        self.trimcode = trimcode
        if self.trimcode < 0:
            print(f"\n\nSorry, my bandgap trim settings don't go negative: {trimcode}\n\n")
            exit()
        if self.trimcode > 127:
            print(f"\n\nSorry, my bandgap trim settings don't go above 127: {trimcode}\n\n")
            exit()
    def set_tdegc(self, tdegc):
        self.tdegc = float(tdegc)
        if self.tdegc < -50:
            print(f"\n\nDie too cold at {self.tdegc}, cracked and broken!\n\n")
            exit()
        if self.tdegc > 165:
            print(f"\n\nDie too hot at (self.tdegc), Latched up!!\n\n")
            exit()
    def Tk(self):
        return 273.15 + self.tdegc
    def Vbe(self):
        m = (self.vbe27 - self.VTO) / (273.15 + 27)
        b = self.VTO
        parabola_offset = 211.0
        parabola_height = 0.003
        parbola = ((1 - (self.Tk() - parabola_offset)**2) / parabola_offset + parabola_offset) / parabola_offset * parabola_height
        return m * self.Tk() + b + parbola
    def Vt(self):
        return self.K * (self.tdegc + 273.15) / self.q
    def get_vbg(self):
        return self.Vbe() + self.dvbe_gain * self.Vt() * numpy.log(self.Nemit) + self.trimcode * self.trim_lsb * (self.Vt() / 0.026)














