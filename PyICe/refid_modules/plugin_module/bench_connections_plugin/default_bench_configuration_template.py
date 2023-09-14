from PyICe.bench_configuration_management   import bench_configuration_management, lab_components
import abc

class default_bench_configuration_template(abc.ABC):

    @abc.abstractmethod
    def component_collection():
        ''' Maintain a list of components that will be used on your bench for your various setups. Many can be found in lab_components, but you may need to make a few of your own a la target boards.

        from {project_folder_name}.{project_folder_name}_base.modules     import {project_folder_name}_bench_configuration_components       # If you are adding in project specific boards or the like

        components = bench_configuration_management.component_collection()
        
        components.add_component(lab_components.whatuwant('BABY_I_GOT_IT'))
        components.add_component(lab_components.whatuneed('BABY_YAKNOW_I_GOT_IT'))
        return components


        '''
    @abc.abstractmethod
    def default_connections(components, name):
        ''' Here you can have a default bench setup that all others will be compared to. When displaying what connections are made, only the ones that differ from these will be presented.

        project_default_connections = bench_configuration_management.connection_collection(name)
        
        project_default_connections.add_connection(components["BABY_I_GOT_IT"][a terminal],                       components["BABY_YAKNOW_I_GOT_IT"][another terminal])
        project_default_connections.add_connection(components["BABY_I_GOT_IT"][a different terminal],             components["BABY_YAKNOW_I_GOT_IT"][a fourth terminal])
        
        return stowe_default_connections
        '''
