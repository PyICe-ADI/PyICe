from PyICe.refid_modules.plugin_module.plugin import plugin
import importlib

class template_checker(plugin):
    def __init__(self, test_mod,template_check):
        super().__init__(test_mod)
        self.template_check=template_check

    def __str__(self):
        return "Compares a board's checked in blueprint to that of a given template, reporting discrepancies."

    def get_atts(self):
        att_dict = {
                    }
        return att_dict

    def _set_atts_(self):
        pass

    def get_hooks(self):
        plugin_dict={
                    'tm_set':[self._temche_set_variables],
                    }
        return plugin_dict

    def set_interplugs(self):
        try:
            self.tm.interplugs['die_traceability_begin_collect'].extend([self.tem_check_itself])
        except KeyError:
            print('\nTemplate_check_plugin requires die_traceability_plugin to be able to function.\n')

    def execute_interplugs(self, hook_key, *args, **kwargs):
        for (k,v) in self.tm.interplugs.items():
            if k is hook_key:
                for f in v:
                    f(*args, **kwargs)

    def _temche_set_variables(self, *args, **kwargs):
        self.tm.tt._need_to_temche = True

    def tem_check_itself(self):
        if self.tm.tt._need_to_temche:
            prob_msg = self.template_check.template_check(self.tm.tb_data, self.tm.variant)
            if len(prob_msg[0]):
                print(f'\nBOM discrepancies between target board and variant template')
                [print(f'  {msg.expandtabs(prob_msg[1]+5)}') for msg in prob_msg[0]]
                if input('Continue? [y/n] ').upper() not in ['Y', 'YES']: 
                    raise Exception('Too many BOM discrepancies')
            self.tm.tt._need_to_temche = False