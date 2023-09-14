import collections
import os
import re
import subprocess
import sys

class results_dict(collections.OrderedDict):
    '''Ordered dictionary with pretty print addition.'''
    def __str__(self):
        s = ''
        max_key_name_length = 0
        for k,v in self.items():
            max_key_name_length = max(max_key_name_length, len(k))
            s += '{}:\t{}\n'.format(k,v)
        s = s.expandtabs(max_key_name_length+2)
        return s

client_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
def get_client_info():
    p4proc = subprocess.run(["p4", "-ztag", "client", "-o"], capture_output=True)
    client_fields = results_dict({'Client':      None,
                                  'Owner':       None,
                                  'Description': None,
                                  'Root':        None,
                                  'Options':     None,
                                })
    if p4proc.returncode:
        print(f"Perforce client returned: {p4proc.returncode}!")
    else:
        for match in client_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
            if match.group('f_name') in client_fields:
                client_fields[match.group('f_name')] = match.group('f_val')
    return client_fields

fstat_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
def get_fstat(local_file):
    # TODO: Consider switching to Helix Python API? https://www.perforce.com/downloads/helix-core-api-python
    p4proc = subprocess.run(["p4", "fstat", local_file], capture_output=True)
    fstat_fields = {'depotFile': None,
                    'clientFile': None,
                    'headAction': None,
                    'headChange': None,
                    'headRev': None,
                    'haveRev': None,
                    'action': None,
                    'diff': None,
                    'swarmLink': None,
                    }
    if p4proc.returncode:
        print(f"Perforce fstat returned: {p4proc.returncode}!")
    elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - no such file(s).':
        pass #not versioned!
    elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - file(s) not in client view.':
        pass #not versioned!
    elif p4proc.stderr != b'':
        print(f"Perforce fstat sent: {p4proc.stderr.decode(sys.stdout.encoding)} to stderr!")
        #Match stowe_eval.html - no such file(s)?
    else:
        for match in fstat_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
            if match.group('f_name') in fstat_fields:
                fstat_fields[match.group('f_name')] = match.group('f_val')
        if fstat_fields['action'] == 'edit':
            diffproc = subprocess.run(['p4', 'diff', local_file], capture_output=True, check=True)
            fstat_fields['diff'] = diffproc.stdout.decode(sys.stdout.encoding)
        if fstat_fields['depotFile'] is not None:
            swarm_prefix = 'https://swarm.adsdesign.analog.com/files/'
            swarm_fpath = fstat_fields['depotFile'][2:] #remove '//'
            swarm_revision = f"?v={fstat_fields['haveRev']}" if fstat_fields['haveRev'] is not None else ''
            fstat_fields['swarmLink'] = f'{swarm_prefix}{swarm_fpath}{swarm_revision}'
    return fstat_fields

describe_zpat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
def get_describe(change_number):
    # TODO: Consider switching to Helix Python API? https://www.perforce.com/downloads/helix-core-api-python
    p4proc = subprocess.run(["p4", "-ztag", "describe", f"{change_number}"], capture_output=True)
    describe_fields = {'change':     None,
                    'user':       None,
                    'client':     None,
                    'time':       None,
                    'desc':       None,
                    'status':     None,
                    'changeType': None,
                    'path':       None,
                    'depotFile0': None,
                    'action0':    None,
                    'type0':      None,
                    'rev0':       None,
                    'fileSize0':  None,
                    'digest0':    None,
                   }
# ... change 1656161
# ... user dsimmons
# ... client stowe_eval--dsimmons--DSIMMONS-L01
# ... time 1613009815
# ... desc mistake with TST_TEMP datatype. According to official spec, this should be a character string. COnverted back to number layer by Python/SQLite.

# ... status submitted
# ... changeType public
# ... path //adi/stowe/evaluation/TRUNK/modules/*
# ... depotFile0 //adi/stowe/evaluation/TRUNK/modules/stdf_utils.py
# ... action0 edit
# ... type0 text
# ... rev0 14
# ... fileSize0 33359
# ... digest0 15AD23C1FD1BF6F4FE5669838FD94449

    if p4proc.returncode:
        print(f"Perforce describe returned: {p4proc.returncode}!")
    # elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - no such file(s).':
        # pass #not versioned!
    # elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - file(s) not in client view.':
        # pass #not versioned!
    elif p4proc.stderr != b'':
        print(f"Perforce describe sent: {p4proc.stderr.decode(sys.stdout.encoding)} to stderr!")
        #Match stowe_eval.html - no such file(s)?
    else:
        for match in fstat_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
            if match.group('f_name') in describe_fields:
                describe_fields[match.group('f_name')] = match.group('f_val')
    return describe_fields

def check_file_writable(fnm):
    if os.path.exists(fnm):
        # path exists
        if os.path.isfile(fnm): # is it a file or a dir?
            # also works when file is a link and the target is writable
            return os.access(fnm, os.W_OK)
        else:
            return False # path is a dir, so cannot write as a file
    return False
    # # target does not exist, check perms on parent dir
    # pdir = os.path.dirname(fnm)
    # if not pdir: pdir = '.'
    # # target is creatable if parent dir is writable
    # return os.access(pdir, os.W_OK)

def sync_workspace(template_workspace):
    p4proc = subprocess.run(["p4", "workspace", "-t", template_workspace], capture_output=True)
    if p4proc.returncode:
        print(f"Perforce fstat returned: {p4proc.returncode}!")
    if p4proc.stdout != b'':
        print(f'stdout: {p4proc.stdout}')
    if p4proc.stderr != b'':
        print(f'stderr: {p4proc.stderr}')

edit_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
def p4_edit(filename):
    p4proc = subprocess.run(["p4", "-ztag", "edit", filename], capture_output=True)
    edit_fields = results_dict({'depotFile':  None,
                                'clientFile': None,
                                'workRev':    None,
                                'action':     None,
                                'type':       None,
                                })
    if p4proc.returncode:
        print(f"Perforce client returned: {p4proc.returncode}!")
    else:
        for match in client_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
            if match.group('f_name') in edit_fields:
                edit_fields[match.group('f_name')] = match.group('f_val')
    if edit_fields['action'] == 'edit':
        return True
    else:
        print(f'Checkout of {filename} failed.')
        print(edit_fields)
        return False



# stdout: b'Client stowe_eval--dsimmons--CHLM-PELAB-D01 not changed.\r\n'