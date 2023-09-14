import time, os

def delete_file(filename, max_tries=20, retry_delay=5):
    """Tries to delete a file, retrying if the file is locked (e.g. because it is open
    in Notepad++, SQLite Manager, or another program), failing gracefully if the file
    doesn't (yet) exist. Gives up after a number of retries and raises RuntimeError.
    Good for removing stale SQLite DBs and log files from old runs."""
    try:
        f_stat = os.stat(filename)  # See if file already exists.
        # If not, an exception is thrown and we GOTO the "except OSError:" below.
        # All code from here to the "except OSError:"
        # is only executed if the file actually exists.
        tries = max_tries
        while tries > 0:
            try:
                os.remove(filename)
                print("Removed prior run file {}".format(filename))
                break
            except OSError:
                print("Unable to remove stale file {} --- RETRYING in {} secs".format(filename, retry_delay))
                tries = tries - 1
                time.sleep(retry_delay)
        else:
            print("Giving up!")
            raise RuntimeError
    except OSError:
        print("No prior", filename, "to remove.")