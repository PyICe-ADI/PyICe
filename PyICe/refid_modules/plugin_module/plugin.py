import abc

class plugin(abc.ABC):
    def __init__(self, test_mod, **kwargs):
        self.tm = test_mod
        if not hasattr(self.tm, 'interplugs'):
            self.tm.interplugs={}
        self._set_atts_()

    @abc.abstractmethod
    def get_atts(self):
        '''
        This will add attributes to the test module so it will be able to call certain values without invoking the plugins in the future.

        att_dict = {
                   'attribute_name':self.corresponding_method,
                   'same_deal':self.pattern_recognition,
                   ...
                    }
        return att_dict
        '''

    @abc.abstractmethod
    def __str__(self):
        """Provide a description of the plugin"""

    @abc.abstractmethod
    def get_hooks(self):
        '''Here you assign what methods you want to include in your temptroller or test_module in the style of
        
        plugin_dict={
                          "where these methods go":[method1, method2],
                          "where other methods go": [method3, method4],
                          ...
                         }
         return plugin_dict
        
        the list of possible locations for the temptroller and test_module is as follows:
        'begin_collect'
        'tm_add_attr'
        'tm_logger_setup'
        'tm_set'
        'tm_plot'
        'pre_collect'
        'post_collect'
        'post_repeatability'
        'tm_plot_from_table'
        'begin_archive'
        '''

    @abc.abstractmethod
    def set_interplugs(self):
        '''
        If you have another plug and you know the name of one of their interplug spots, you can add in functions here in the style of
        
        self.tm.interplugs[example_other_plugin_spot] = [self.example, self.functions, self.to, self.add]
        self.tm.interplugs[_its__another_plugin_spot] = [self.even, self.more, self.stuff]
        '''

    def execute_interplugs(self, hook_key, *args, **kwargs):
        ''' And here you go through all the listed interplugs from all plugins and see if anything in there matters to you. In the style of '''
        
        for (k,v) in self.tm.interplugs.items():
            if k is hook_key:
                for f in v:
                    f(*args, **kwargs)

