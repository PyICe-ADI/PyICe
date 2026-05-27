"""Delete file utility."""
import time
import os


def delete_file(filename, max_tries=20, retry_delay=5):
    """Delete a file, retrying if it is locked, and silently skipping if it does not exist.

    Designed for removing stale SQLite databases and log files from previous
    test runs.  If the file is held open by another program (e.g. Notepad++,
    SQLite Manager), the function retries up to *max_tries* times with a
    *retry_delay*-second pause between attempts.

    Args:
        filename: Path to the file to delete.
        max_tries: Maximum number of removal attempts before giving up.
        retry_delay: Seconds to wait between retries when the file is locked.

    Raises:
        RuntimeError: If the file still cannot be deleted after all retries.
    """
    try:
        _f_stat = os.stat(filename)  # noqa: F841 - See if file already exists.
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
                print(
                    "Unable to remove stale file {} --- RETRYING in {} secs".format(filename, retry_delay))
                tries = tries - 1
                time.sleep(retry_delay)
        else:
            print("Giving up!")
            raise RuntimeError
    except OSError:
        print("No prior", filename, "to remove.")
