# This is based on the app note:
# https://fscdn.rohm.com/en/products/databook/applinote/ic/power/switching_regulator/buck_converter_efficiency_app-e.pdf

class buck_power_loss(object):
    def __init__(self, **kwargs):
        self.params = kwargs
        self.params["tref"]         = 25    # Reference temperature for temperature dependent things
        self.params["ron_h_tol"]    = 1     # Model to increase the switch resistance by corner
        self.params["ron_l_tol"]    = 1     # Model to increase the switch resistance by corner
        self.params["dcr_tol"]      = 1     # Model to increase the DCR resistance by corner
        self.params["tamb_abstol"]  = 0.1   # Temperature settling iteration tolerance in °C
        self.params["vbg"]          = 1.25  # Bandgap voltage to compute body diode voltage vs temperature
    def _compute(self):
        self.params["tamb_die"] = self.params["tdegc"]
        self.params["tamb_ind"] = self.params["tdegc"]
        temperature_is_stable = False
        while not temperature_is_stable:
            ##########################################################################################
            # Adjust temperature and tolerance based parameters
            ##########################################################################################
            self.params["ron_h"] = self.params["ron_h_nom"] * self.params["ron_h_tol"] * (1 + self.params["ron_h_tc"] * (self.params["tamb_die"] - self.params["tref"]))
            self.params["ron_l"] = self.params["ron_l_nom"] * self.params["ron_l_tol"] * (1 + self.params["ron_l_tc"] * (self.params["tamb_die"] - self.params["tref"]))
            self.params["dcr"] = self.params["dcr_nom"] * self.params["dcr_tol"] * (1 + self.params["dcr_tc"] * (self.params["tamb_ind"] - self.params["tref"]))
            self.params["vd"] = (self.params["vbg"] - self.params["vdtref"]) / (0 - (self.params["tref"] + 273.15)) * (self.params["tamb_die"] + 273.15) + self.params["vbg"]
            ##########################################################################################
            # switch_conduction_loss
            ##########################################################################################
            self.params["duty_cycle"] = (self.params["vout"] + self.params["iout"] * (self.params["ron_l"] + self.params["dcr"])) / \
                                        (self.params["vin"]  - self.params["iout"] * (self.params["ron_l"] - self.params["ron_h"]))
            self.params["iripple"] = (self.params["vin"] - self.params["vout"]) / self.params["fsw"] / self.params["l"] * self.params["duty_cycle"]
            self.params["ipeak"] = self.params["iout"] + self.params["iripple"] / 2
            self.params["ivalley"] = self.params["iout"] - self.params["iripple"] / 2
            self.params["pon_h"] = (self.params["iout"]**2 + (self.params["ipeak"] - self.params["ivalley"])**2 / 12) * self.params["ron_h"] * self.params["duty_cycle"]
            self.params["pon_l"] = (self.params["iout"]**2 + (self.params["ipeak"] - self.params["ivalley"])**2 / 12) * self.params["ron_l"] * (1 - self.params["duty_cycle"])
            ##########################################################################################
            # switch_transition_loss
            ##########################################################################################
            self.params["psw_h"] = 1 / 2 * (self.params["vin"] + self.params["vd"]) * (self.params["tr_h"] * self.params["ivalley"] + self.params["tf_h"] * self.params["ipeak"]) * self.params["fsw"]
            self.params["psw_l"] = 0 # 1 / 2 * self.params["vd"] * self.params["iout"] * (self.params["tr_l"] + self.params["tf_l"]) * self.params["fsw"] # Sauparna to re-assess later?
            ##########################################################################################
            # reverse_recovery_loss
            ##########################################################################################
            self.params["pdiode"] = 1 / 2 * self.params["vin"] * self.params["irr"] * self.params["trr"] * self.params["fsw"]
            ##########################################################################################
            # deadtime transition loss
            ##########################################################################################
            self.params["pd"] = self.params["vd"] * self.params["iout"] * (self.params["tdr"] + self.params["tdf"]) * self.params["fsw"]
            ##########################################################################################
            # coss loss
            ##########################################################################################
            self.params["pcoss"] =  (self.params["qoss_l"] + self.params["qoss_h"]) * self.params["vin"] * self.params["fsw"]
            ##########################################################################################
            # gate chargeloss
            ##########################################################################################
            self.params["pg"] = self.params["qg_h"] * self.params["vgs_h"] * self.params["fsw"] + \
                                self.params["qg_l"] * self.params["vgs_l"] * self.params["fsw"]
            ##########################################################################################
            # qcurrent loss
            ##########################################################################################
            self.params["pic"] = self.params["vin"] * self.params["icc"]
            ##########################################################################################
            # inductor_conduction_loss
            ##########################################################################################
            self.params["il_rms_squared"] = (self.params["ipeak"] - self.params["ivalley"])**2 / 12 + self.params["iout"]**2
            self.params["pdcrl"] = self.params["il_rms_squared"] * self.params["dcr"]
            ##########################################################################################
            # inductor_core_loss
            ##########################################################################################
            if self.params["corelossmodel"] == "MARTIN": # The Martin Conjecture
                self.params["plcore"] = self.params["il_rms_squared"] * self.params["fsw"] * self.params["coreloss_k"] * (1 + self.params["coreloss_tc"] * (self.params["tamb_die"] - self.params["tref"])) 
            elif self.params["corelossmodel"] == "DAS":
                self.params["plcore"] = (   self.params["acrl"] * (self.params["ipeak"] - self.params["ivalley"])**2 / 12 + \
                                            self.params["iout"]**2 * self.params["fsw"] * self.params["coreloss_k"]) * (1 + self.params["coreloss_tc"] * (self.params["tamb_die"] - self.params["tref"]))
            else:
                print(f"PyICe Buck power Loss Model: Don't know how to use Core Loss Model: '{self.params['''corelossmodel''']}'.")
                exit()
            ##########################################################################################
            # Cin and Cout loss
            ##########################################################################################
            self.params["icinrms"] = self.params["iout"] * ((self.params["vin"] - self.params["vout"] ) * self.params["vout"])**0.5 / self.params["vin"]
            self.params["pcin"] = self.params["icinrms"]**2 * self.params["esrcin"]
            self.params["dil"] = (self.params["vin"] - self.params["vout"]) / self.params["fsw"] / self.params["l"] * self.params["vout"] / self.params["vin"]
            self.params["icoutrms"] = self.params["dil"] / 2 / 3**0.5
            self.params["pcout"] = self.params["icoutrms"]**2 * self.params["esrcout"]
            ##########################################################################################
            # body diode loss
            ##########################################################################################
            self.params["pdiode"] = 1 / 2 * self.params["vin"] * self.params["irr"] * self.params["trr"] * self.params["fsw"]
            ##########################################################################################
            # Check temperature settling
            ##########################################################################################
            self.params["pdiss_chip"] = self.params["pon_h"] + self.params["pon_l"] + self.params["psw_h"] + self.params["psw_l"] + self.params["pdiode"] + self.params["pcoss"] + self.params["pd"] + self.params["pg"] + self.params["pic"]
            self.params["pdiss_inductor"] = self.params["pdcrl"] + self.params["plcore"]
            self.params["tamb_die_new"] = self.params["tdegc"] + self.params["pdiss_chip"] * self.params["thjc_die"]
            self.params["tamb_ind_new"] = self.params["tdegc"] + self.params["pdiss_inductor"] * self.params["thjc_ind"]
            temperature_is_stable = abs(self.params["tamb_die_new"] - self.params["tamb_die"]) < self.params["tamb_abstol"] and abs(self.params["tamb_ind_new"] - self.params["tamb_ind"]) < self.params["tamb_abstol"]
            self.params["tamb_die"] = self.params["tamb_die_new"]
            self.params["tamb_ind"] = self.params["tamb_ind_new"]
            
    def write(self, parameter, value):
        self.params[parameter] = value

    def read(self, parameter):
        return self.params[parameter]

    def get_power_loss(self):
        self._compute()
        return   self.params["pdiss_chip"]                      \
               + self.params["pdiss_inductor"]                  \
               + self.params["pcin"] + self.params["pcout"]
               
    def get_ploss_chip(self):
        self._compute()
        return self.params["pdiss_chip"]
        
    def get_ploss_inductor(self):
        self._compute()
        return self.params["pdiss_inductor"]
                  
    def get_efficiency(self):
        power_out = self.params["vout"] * self.params["iout"]
        return power_out / (power_out + self.get_power_loss())
        
    def get_temperatures(self):
        self._compute()
        return {"TDIE": self.params["tamb_die"], "TINDUCTOR": self.params["tamb_ind"]}

class copper_resistor(object):
    # No self heating solver
    def __init__(self, **kwargs):
        self.params = kwargs
        self.params["tref"] = 25
        self.params["tc"] = 3950e-6
        
    def write(self, parameter, value):
        self.params[parameter] = value
        
    def get_resistance(self):
        return self.params["r_nom"] * (1 + self.params["tc"] * (self.params["tdegc"]-self.params["tref"]))
        
    def get_power_loss(self):
        return self.get_resistance() * self.params["current"]**2
        