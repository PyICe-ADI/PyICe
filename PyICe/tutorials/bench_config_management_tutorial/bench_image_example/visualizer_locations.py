import pathlib

class component_locations:
    def __init__(self):
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
        "HAMEG"                             : {"position" : {"xpos":-700, "ypos":-500} , "image" : f"{path}Hameg4040.PNG", "use_label" : False},
        "Rampinator"                        : {"position" : {"xpos":-800, "ypos":-800}  , "image" : f"{path}Rampinator.PNG", "use_label" : False},
        "OSCILLOSCOPE"                      : {"position" : {"xpos":1350, "ypos":925}   , "image" : f"{path}Agilent3034a.PNG", "use_label" : False},
        "AGILENT_3497x"                     : {"position" : {"xpos":-800, "ypos":500}  , "image" : f"{path}Agilent34970.PNG", "use_label" : False},
        "AGILENT_34908A"                    : {"position" : {"xpos":-100, "ypos":575}  , "image" : f"{path}Agilent34908a.PNG", "use_label" : False},
        "AGILENT_34901A_2"                  : {"position" : {"xpos":-100, "ypos":500}  , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
        "AGILENT_34901A_3"                  : {"position" : {"xpos":-100, "ypos":425}   , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
        "PSA_RFMUX"                         : {"position" : {"xpos":1500, "ypos":-500}  , "image" : f"{path}HTX9016.PNG", "use_label" : False},
        "PSA"                               : {"position" : {"xpos":1850, "ypos":-1350} , "image" : f"{path}PSA.png", "use_label" : False},
        }