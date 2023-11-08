class plugin_data_repo():
    def __init__(self):
        pass
        # self.repo['json_addon'] = {}
        # self.repo['json_addon']['traceability'] = {}

    def add_to_repo(self, attr_name, attr_value):
        if hasattr(self, attr_name):
            print(f'The repo already has an attribute named {attr_name}, and it has a value of {getattr(self, attr_name)}.')
        setattr(self, attr_name, attr_value)

## Hokay. So every traceability plugin will add their info to this repo when they add it to the database a during normal run.
## Additionally, every traceability plugin will ATTEMPT TO draw from the database to the repo in the event of a "plot_from_table."
## No traceability will have to be established. Order is going to be a nightmare.