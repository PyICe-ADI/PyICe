import pkgutil
import inspect
import sys
import os

class lab_instrument_locator:
    '''Complicated deep blue Python to elminate the old lab_instruments file from the upper level of PyICe.
    See: https://stackoverflow.com/questions/2447353/getattr-on-a-module
    '''
    def __init__(self):
        basepath = os.path.dirname(__file__)
        PyICe_mod_path = pkgutil.resolve_name('PyICe').__path__[0] # ._path[0] for some users?
        self._members = {}
        for (root, dirs, files) in os.walk(basepath):
            for fname in files:
                if root == basepath and fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                mod_rel_fpath = os.path.relpath(fpath, start=PyICe_mod_path)
                (_mod_rel_path, mod_fname) = os.path.split(mod_rel_fpath)
                mod_path = f'PyICe.{_mod_rel_path.replace(os.sep, ".")}'
                (mod_name,mod_ext) = os.path.splitext(mod_fname)
                if mod_ext == ".py":
                    _this_module = pkgutil.resolve_name(f"{mod_path}.{mod_name}")
                    _mod_members = dir(_this_module)
                    for (name, member) in inspect.getmembers(_this_module):
                        if name.startswith('_'):
                            continue
                        if name not in _mod_members:
                            continue
                        if name in self._members and self._members[name] is not member:
                            raise Exception(f'lab_instruments namespace conflict: {name} from {member.__module__} and {self._members[name].__module__}.')
                        self._members[name] = member
        self.__all__ = list(self._members.keys())
        
    def __getattribute__(self, name):
        if name=="__class__":
            return type(self)
        if name in ["_members", "__all__", "__class__"]:
            return super(lab_instrument_locator, self).__getattribute__("__dict__")[name] 
        if name.startswith("_"):
            return globals()[name]
        return self._members[name]

sys.modules[__name__] = lab_instrument_locator()
