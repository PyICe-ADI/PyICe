import importlib, socket, os

def get_bench_instruments(project_folder_name, benchsetup = None):
    if benchsetup is None:
        thismachine = socket.gethostname().replace("-","_")
        thisuser = thisbench = os.getlogin().lower() # Duplicate benches because of case sensitivity!
        thisbench = f'{thisuser}_{thismachine}'
    else:
        thisbench = benchsetup
    try:
        module = importlib.import_module(name=f"{project_folder_name}.{project_folder_name}_base.benches.{thisbench}", package=None)
    except ImportError as e:
        print(e)
        raise Exception(f"Can't find bench file {thisbench}. Note that dashes must be replaced with underscores.")
    return module.bench_instruments
