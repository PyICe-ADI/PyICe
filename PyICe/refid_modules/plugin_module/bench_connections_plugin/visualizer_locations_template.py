import pathlib

class component_locations:
    def __init__(self):
        '''
        path =  pathlib.Path(__file__).parent.resolve().as_posix() + "/visualizer_images/"
        self.locations = {
        #####################################################
        #                                                   #
        # Test Equipment                                    #
        #                                                   #
        #####################################################
        "CONFIGURATORXT"                    : {"position" : {"xpos":0, "ypos":0}        , "image" : f"{path}ConfigXT.PNG", "use_label" : False},
        "SIGLENT"                           : {"position" : {"xpos":500, "ypos":1000}   , "image" : f"{path}Siglent.PNG", "use_label" : False},
        "SPAT"                              : {"position" : {"xpos":-800, "ypos":-200}  , "image" : f"{path}SPAT.PNG", "use_label" : False},
        "AGILENT_U2300_DAQ"                 : {"position" : {"xpos":-800, "ypos":500}   , "image" : f"{path}U2331A.PNG", "use_label" : False},
        "U2300_TO_CAT5"                     : {"position" : {"xpos":-800, "ypos":250}   , "image" : f"{path}U2331A_Adapter.PNG", "use_label" : False},
        "HAMEG"                             : {"position" : {"xpos":-700, "ypos":-1400} , "image" : f"{path}Hameg4040.PNG", "use_label" : False},
        "Rampinator"                        : {"position" : {"xpos":-800, "ypos":-800}  , "image" : f"{path}Rampinator.PNG", "use_label" : False},
        "OSCILLOSCOPE"                      : {"position" : {"xpos":1350, "ypos":925}   , "image" : f"{path}Agilent3034a.PNG", "use_label" : False},
        "AGILENT_3497x"                     : {"position" : {"xpos":-800, "ypos":1000}  , "image" : f"{path}Agilent34970.PNG", "use_label" : False},
        "AGILENT_34908A"                    : {"position" : {"xpos":-100, "ypos":1075}  , "image" : f"{path}Agilent34908a.PNG", "use_label" : False},
        "AGILENT_34901A_2"                  : {"position" : {"xpos":-100, "ypos":1000}  , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
        "AGILENT_34901A_3"                  : {"position" : {"xpos":-100, "ypos":925}   , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
        "PSA_RFMUX"                         : {"position" : {"xpos":1500, "ypos":-500}  , "image" : f"{path}HTX9016.PNG", "use_label" : False},
        "PSA"                               : {"position" : {"xpos":1850, "ypos":-1350} , "image" : f"{path}PSA.png", "use_label" : False},
        #####################################################
        #                                                   #
        # Terminators and Probes                            #
        #                                                   #
        #####################################################
        "SCOPEPROBE1"                       : {"position" : {"xpos":800, "ypos":600}    , "image" : f"{path}ScopeProbe.PNG", "use_label" : False},
        "SCOPEPROBE2"                       : {"position" : {"xpos":1100, "ypos":600}   , "image" : f"{path}ScopeProbe.PNG", "use_label" : False},
        "SCOPEPROBE3"                       : {"position" : {"xpos":1400, "ypos":600}   , "image" : f"{path}ScopeProbe.PNG", "use_label" : False},
        "SCOPEPROBE4"                       : {"position" : {"xpos":1700, "ypos":600}   , "image" : f"{path}ScopeProbe.PNG", "use_label" : False},
        "VOUT0_TERMINATOR"                  : {"position" : {"xpos":950, "ypos":400}    , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        "VOUT1_TERMINATOR"                  : {"position" : {"xpos":1100, "ypos":400}   , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        "VOUT2_TERMINATOR"                  : {"position" : {"xpos":1250, "ypos":400}   , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        
        
        "PSA_DC_BLOCKER"                    : {"position" : {"xpos":2300, "ypos":-800}   , "image" : f"{path}HTX9015_DC_BLOCKER.png", "use_label" : False},
        
        
        "AVIN_TERMINATOR"                   : {"position" : {"xpos":1400, "ypos":400}   , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        "RST_TERMINATOR"                    : {"position" : {"xpos":1550, "ypos":400}   , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        "WDD_TERMINATOR"                    : {"position" : {"xpos":1700, "ypos":400}   , "image" : f"{path}Tekronix50Ohm.PNG", "use_label" : False},
        "CURRENTPROBE_A"                    : {"position" : {"xpos":2000, "ypos":400}   , "image" : f"{path}CurrentProbe.PNG", "use_label" : False},
        "CURRENTPROBE_B"                    : {"position" : {"xpos":2000, "ypos":700}   , "image" : f"{path}CurrentProbe.PNG", "use_label" : False},
        #####################################################
        #                                                   #
        # Power Breakouts and Y's                           #
        #                                                   #
        #####################################################
        "Y_CONNECTOR_POWER1"                : {"position" : {"xpos":-500, "ypos":-500}  , "image" : f"{path}YPower.PNG", "use_label" : False},
        "Y_CONNECTOR_POWER5"                : {"position" : {"xpos":-400, "ypos":-500}  , "image" : f"{path}YPower.PNG", "use_label" : False},
        "Y_CONNECTOR_POWER6"                : {"position" : {"xpos":-300, "ypos":-500}  , "image" : f"{path}YPower.PNG", "use_label" : False},
        "Y_CONNECTOR_POWER2"                : {"position" : {"xpos":-200, "ypos":-500}  , "image" : f"{path}YPower.PNG", "use_label" : False},
        "Y_CONNECTOR_POWER7"                : {"position" : {"xpos":-100, "ypos":-500}  , "image" : f"{path}YPower.PNG", "use_label" : False},
        "Y_CONNECTOR_POWER3"                : {"position" : {"xpos":0, "ypos":-500}     , "image" : f"{path}YPower.PNG", "use_label" : False},
        "POWER3_BREAKOUT"                   : {"position" : {"xpos":450, "ypos":500}    , "image" : f"{path}PowerBreakout.PNG", "use_label" : False},
        "POWER4_BREAKOUT"                   : {"position" : {"xpos":450, "ypos":700}    , "image" : f"{path}PowerBreakout.PNG", "use_label" : False},
        #####################################################
        #                                                   #
        # Target Boards                                     #
        #                                                   #
        #####################################################
        "LT3390_BOARD"                      : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_1_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_2_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_3_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_4_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_5_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_6_BOARD"                    : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "LT3390_BOARD_OPEN_LOOP"            : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        "TARGET_BOARD"                      : {"position" : {"xpos":2000,   "ypos":200}, "image" : f"{path}TargetBoard.PNG", "use_label" : True},
        #####################################################
        #                                                   #
        # Auxilliary Boards                                 #
        #                                                   #
        #####################################################
        "BASE_BOARD"                        : {"position" : {"xpos":950, "ypos":0}  , "image" : f"{path}Baseboard.PNG", "use_label" : False},
        "LT8609_BOARD"                      : {"position" : {"xpos":1750, "ypos":0} , "image" : f"{path}LT8609Adapter.PNG", "use_label" : False},
        "LT8609_BOARD_VMAINA_PASSTHRU"      : {"position" : {"xpos":1750, "ypos":0} , "image" : f"{path}LT8609Adapter.PNG", "use_label" : False},
        "LT3390_1_ADAPTER"                  : {"position" : {"xpos":1750, "ypos":0} , "image" : f"{path}LT3390-1_Adapter.PNG", "use_label" : False},
        "LT3390_3_ADAPTER"                  : {"position" : {"xpos":1750, "ypos":0} , "image" : f"{path}LT3390-1_Adapter.PNG", "use_label" : False},
        "LT3390_5_ADAPTER"                  : {"position" : {"xpos":1750, "ypos":0} , "image" : f"{path}LT3390-1_Adapter.PNG", "use_label" : False},
        "CAP_MASTER_BLASTER_0K_MB"          : {"position" : {"xpos":1500, "ypos":0} , "image" : f"{path}CapBoard.PNG", "use_label" : False},
        "CAP_MASTER_BLASTER_2K_MB"          : {"position" : {"xpos":1500, "ypos":0} , "image" : f"{path}CapBoard.PNG", "use_label" : False},
        "MEASURE_BUS_ISO_2K"                : {"position" : {"xpos":1500, "ypos":0} , "image" : f"{path}CapBoard.PNG", "use_label" : False},
        #####################################################
        #                                                   #
        # Specific Loads BK8500                             #
        #                                                   #
        #####################################################
        "BK8500_ILOAD0"                     : {"position" : {"xpos":-100, "ypos":-900}  , "image" : f"{path}BK8500.PNG", "use_label" : False},
        "BK8500_ILOAD1"                     : {"position" : {"xpos":-100, "ypos":-1200} , "image" : f"{path}BK8500.PNG", "use_label" : False},
        "BK8500_ILOAD2"                     : {"position" : {"xpos":-100, "ypos":-1500} , "image" : f"{path}BK8500.PNG", "use_label" : False},
        #####################################################
        #                                                   #
        # Generic Loads                                     #
        #                                                   #
        #####################################################
        "GENERIC_ILOAD0"                    : {"position" : {"xpos":400, "ypos":-500}   , "image" : f"{path}Missing.PNG", "use_label" : False},
        "GENERIC_ILOAD1"                    : {"position" : {"xpos":400, "ypos":-700}   , "image" : f"{path}Missing.PNG", "use_label" : False},
        "GENERIC_ILOAD2"                    : {"position" : {"xpos":400, "ypos":-900}   , "image" : f"{path}Missing.PNG", "use_label" : False},
        "GENERIC_ILOAD3"                    : {"position" : {"xpos":400, "ypos":-1100}  , "image" : f"{path}Missing.PNG", "use_label" : False},
        "GENERIC_ILOAD4"                    : {"position" : {"xpos":400, "ypos":-1300}  , "image" : f"{path}Missing.PNG", "use_label" : False},
        "single_channel_electronic_load"    : {"position" : {"xpos":400, "ypos":-1500}  , "image" : f"{path}Missing.PNG", "use_label" : False},
        #####################################################
        #                                                   #
        # Specific Loads HTX9000                            #
        #                                                   #
        #####################################################
        "HTX9000_ILOAD0"                    : {"position" : {"xpos":900, "ypos":-500}   , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        "HTX9000_ILOAD1"                    : {"position" : {"xpos":900, "ypos":-700}   , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        "HTX9000_ILOAD2"                    : {"position" : {"xpos":900, "ypos":-900}   , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        "HTX9000_ILOAD3"                    : {"position" : {"xpos":900, "ypos":-1100}  , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        "HTX9000_ILOAD4"                    : {"position" : {"xpos":900, "ypos":-1300}  , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        "HTX9000_POWER1"                    : {"position" : {"xpos":900, "ypos":-1500}  , "image" : f"{path}HTX9000.PNG", "use_label" : False},
        }
    '''
    pass