from PyICe import lab_instruments, lab_core
from PyICe.lab_utils.banners import print_banner
import os

def create_my_scopefile():
    if not os.path.isfile('./local/my_instruments.py'):
        os.makedirs("./local/", exist_ok=True)
        with open('./local/my_instruments.py', 'w') as file:
            text = '''from PyICe import lab_core, lab_instruments
master = lab_core.master()
agilent_3034a = master.get_visa_interface(PUT YOUR SCOPE ADDRESS STRING HERE)'''
            file.write(text)
            print("\n")
            print_banner("Created the file './local/my_instruments.py.'", "Edit it for your scope address and rerun this program.")
            print("\n")
            exit()
