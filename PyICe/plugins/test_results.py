from PyICe.lab_utils.sqlite_data import sqlite_data
import collections
import datetime
import functools
import json
import numbers
from numpy import bool_, ndarray

# https://stackoverflow.com/questions/5884066/hashing-a-dictionary/22003440#22003440
def freeze(o):
  if isinstance(o,dict):
    return frozenset({ k:freeze(v) for k,v in o.items()}.items()) #sorted??
  if isinstance(o,set):
    return frozenset(o)
  if isinstance(o,list):
    return tuple(freeze(v) for v in o)
  if isinstance(o,tuple):
    # Tuples are immutable, but their members might not be.
    return tuple(freeze(v) for v in o)
  try:
    hash(o)
  except TypeError as e:
    raise TypeError("Something slipped through the freeze function. Contact support.") from e
  else:
    return o

def make_hash(o):
    """
    makes a hash out of anything that contains only list,dict and hashable types including string and numeric types
    """
    return hash(freeze(o))

def none_min(a, b):
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return min(a,b)
def none_max(a, b):
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return max(a,b)
def none_abs(a):
    if a is None:
        return None
    return abs(a)


class generic_results():
    '''Parent of Test_Results and correlation_results and keeper of any commonalities.'''
    def __init__(self):
        raise Exception("This class isn't supposed to be instantiated directly.")
        # TODO https://docs.python.org/3/library/abc.html ?
    def _init(self, name, module):
        self._name = name
        self._traceability_info = collections.OrderedDict()
        self._module = module
    def get_name(self):
        return self._name
    def get_traceability_info(self):
        return self._traceability_info
    def _set_traceability_info(self, **kwargs):
        for k,v in kwargs.items():
            self._traceability_info[k] = v
    
    def _json_report(self, declarations, results, ate_results=[]):
        class CustomJSONizer(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bool_):
                    return bool(obj)
                elif isinstance(obj, datetime.datetime):
                    return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                elif isinstance(obj, ndarray):
                    return obj.tolist()
                else:
                    try:
                        return super().default(obj)
                    except TypeError as e:
                        print(f'JSON Serialization error with object of type {type(obj)}:')
                        print(obj)
                        breakpoint()
                        raise e
        res_dict = {}

        res_dict['schema_version'] = 1.0
        res_dict['test_module'] = self.get_name()
        res_dict['report_date'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        if self._module.get_name()+'_metadata' in self._module.get_database().get_table_names():
            trace_database = self._module.get_database()
            trace_data = trace_database.query(f'SELECT * FROM {self._module.get_name()}_metadata WHERE rowid is 1').fetchone()
            res_dict['collection_date'] = trace_data[trace_data.keys().index('datetime')]
            res_dict['traceability']= {}
            for channel_name in trace_data.keys():
                if channel_name == 'datetime' or channel_name =='rowid':
                    continue
                res_dict['traceability'][channel_name] = trace_data[trace_data.keys().index(channel_name)]

        res_dict['tests'] = {}
        for t_d in declarations:
            res_dict['tests'][t_d] = {}
            res_dict['tests'][t_d]['declaration'] = {k:v for k,v in self.test_limits[t_d].items() if k not in ['test_name']}
            try:
                results[t_d]
            except KeyError as e:
                res_dict['tests'][t_d]['passes'] = False
            else:
                res_dict['tests'][t_d]['results'] = {}
                if isinstance(self, Test_Results):
                    res_dict['tests'][t_d]['results']['cases'] = []
                    res_dict['tests'][t_d]['results']['summary'] = {}
                    for condition_hash, condition_orig in results[t_d].get_conditions().items():
                        filter_results = results[t_d].filter(condition_hash)
                        cond_dict =  {'conditions': condition_orig,
                                      'case_results': [{k:v for k,v in t_r._asdict().items() if k not in ['test_name', 'conditions', 'plot']} for t_r in filter_results], 
                                      'summary': {'min_data': filter_results._min(),
                                                  'max_data': filter_results._max(),
                                                  'passes':   bool(filter_results),
                                                 },
                                     }
                        res_dict['tests'][t_d]['results']['cases'].append(cond_dict)
                    res_dict['tests'][t_d]['results']['summary'] = {'min_data': results[t_d]._min(),
                                                                    'max_data': results[t_d]._max(),
                                                                    'passes':   bool(results[t_d]),
                                                                    }
                elif isinstance(self, correlation_results):
                    res_dict['tests'][t_d]['results']['temperatures'] = []
                    for temperature in results[t_d].get_temperatures():
                        temperature_dict = {'temperature': temperature,
                                            'cases': [],
                                           }
                        res_dict['tests'][t_d]['results']['temperatures'].append(temperature_dict)
                        temp_group = results[t_d].filter_temperature(temperature)
                        for condition_hash, condition_orig in temp_group.get_conditions().items():
                            cond_group = temp_group.filter_conditions(condition_hash)
                            cond_dict =  {'conditions': condition_orig,
                                          'case_results': [{k:v for k,v in cond._asdict().items() if k not in ['temperature', 'conditions']} for cond in cond_group],
                                          'summary': {'min_error': cond_group._min_error(),
                                                      'max_error': cond_group._max_error(),
                                                      'passes':    bool(cond_group),
                                                     },
                                         }
                            temperature_dict['cases'].append(cond_dict)
                        temperature_dict['summary'] = {'min_error': temp_group._min_error(),
                                                      'max_error': temp_group._max_error(),
                                                      'passes':    bool(temp_group),
                                                      }
                    res_dict['tests'][t_d]['results']['summary'] = {'min_error': results[t_d]._min_error(),
                                                                    'max_error': results[t_d]._max_error(),
                                                                    'passes':    bool(results[t_d]),
                                                                   }
                else:
                    raise Exception("I'm lost.")
        res_dict['summary'] = {'passes': bool(self)}
        return json.dumps(res_dict, indent=2, ensure_ascii=False, cls=CustomJSONizer)

class Test_Results(generic_results):
    class _test_result(collections.namedtuple('test_result', ['test_name', 'conditions', 'min_data', 'max_data', 'passes', 'failure_reason', 'collected_data', 'plot', 'query'])):
        '''add some helper moethods for easy summary'''
        def __new__(cls, **kwargs):
            '''fix (allowed) missing fields. FOr instance, original JSON didn't retain SQL query string.'''
            if 'query' not in kwargs:
                kwargs['query'] = None
            return super().__new__(cls, **kwargs)
        def __bool__(self):
            return bool(self.passes)
        def _min(self):
            if not len(self.collected_data):
                return None
            return min(self.collected_data)
        def _max(self):
            if not len(self.collected_data):
                return None
            return max(self.collected_data)
        def __str__(self):
            summary_str = ''
            summary_str += f'{self.conditions}\tTRIALS:{len(self)}\tVERDICT:{"PASS" if self else "FAIL"}\n'.expandtabs()
            min = self._min()
            if self.failure_reason != '':
                summary_str += f'\tFORCED_FAIL: {self.failure_reason}\n'
            elif len(self) > 1:
                summary_str += f'\tMIN:{f"{min:g}" if type(min) is int else f"{min}" if min is not None else "None"}\n' if not self else ''
                max = self._max()
                summary_str += f'\tMAX:{f"{max:g}" if type(max) is int else f"{max}" if max is not None else "None"}\n' if not self else ''
            else:
                summary_str += f'\tDATA:{f"{min:g}" if type(min) is int else f"{min}" if min is not None else "None"}\n' if not self else ''
            return summary_str
        def __len__(self):
            return len(self.collected_data)
        def __add__(self, other):
            assert isinstance(other, type(self))
            assert self.test_name == other.test_name
            assert self.conditions == other.conditions
            assert self.query == other.query, f"ERROR {self.test_name} grouping mismatch. Grouped results have unexpectedly disparate SQL queries. Consider adding conditions by selecting addtional columns or by keyword argument. If you think you've received this message in error, contact support." 
            return type(self)(test_name=self.test_name,
                              conditions=self.conditions,
                              min_data=none_min(self.min_data, other.min_data), #None creeps in from register_test_failure()
                              max_data=none_max(self.max_data, other.max_data), #None creeps in from register_test_failure()
                              passes=self.passes and other.passes,
                              failure_reason=f'{self.failure_reason}{other.failure_reason}', #TODO cleanup format
                              collected_data=self.collected_data + other.collected_data,
                              plot=self.plot + other.plot,
                              query=self.query
                             )
    class _test_results_list(list):
        '''add some helper methods for easy filtering and summary'''
        def __init__(self, name, upper_limit, lower_limit):
            self.name = name
            self.upper_limit = upper_limit
            self.lower_limit = lower_limit
            super().__init__()
        def __bool__(self):
            if not len(self):
                return False
            return bool(functools.reduce(lambda a,b: a and b, [item.passes for item in self]))
        def __str__(self):
            resp = ''
            resp += f'{self.name}\n'
            resp += f'\tLIMITS:'
            if self.upper_limit == self.lower_limit:
                #Exact test
                try:
                    resp += f'\t SL:{self.upper_limit:g}'
                except (TypeError, ValueError) as e:
                    resp += f'\t SL:{self.upper_limit}'
            else:
                if self.lower_limit is not None:
                    resp += f'\tLSL:{self.lower_limit:g}'
                if self.upper_limit is not None:
                    resp += f'\tUSL:{self.upper_limit:g}'
            resp += '\n'
            resp += '\tRESULTS:\n'
            for cond_res in self.factored():
                for line in str(cond_res).splitlines():
                    resp += f'\t\t{line}\n'
            resp += f'{self.name} summary {"PASS" if self else "FAIL"}.\n'
            return resp
        def _min(self):
            if not len(self):
                return None
            return functools.reduce(none_min, (r._min() for r in self))
        def _max(self):
            if not len(self):
                return None
            return functools.reduce(none_max, (r._max() for r in self))
        def get_conditions(self):
            return {make_hash(data_group.conditions): data_group.conditions for data_group in self}
        def filter(self, condition_hash):
            ret = type(self)(self.name, self.upper_limit, self.lower_limit)
            for data_group in self:
                if make_hash(data_group.conditions) == condition_hash:
                    ret.append(data_group)
            return ret
        def factored(self):
            '''returns new object; doesn't modifiy existing one in place
            merges all resutls from like conditions'''
            ret = type(self)(self.name, self.upper_limit, self.lower_limit)
            for cond_hash in self.get_conditions():
                data_group = functools.reduce(lambda a,b: a+b, [data_group for data_group in self if make_hash(data_group.conditions)==cond_hash])
                ret.append(data_group)
            return ret
    def __init__(self, name, module):
        '''TODO'''

        self._test_results = collections.OrderedDict()
        self._ate_results = collections.OrderedDict()
        self._init(name, module)
        self._test_declarations = collections.OrderedDict()
        self.test_limits = {}
    def json_report(self):
        return self._json_report(declarations=self._test_declarations, results=self._test_results, ate_results=self._ate_results)
    def get_test_declarations(self):
        return list(self._test_declarations.keys())
    def get_test_declaration(self, key):
        return self._test_declarations[key]
    def __str__(self):
        '''printable regression results'''
        #TODO more concise summary when passing, grouped results, etc.
        resp = ''
        passes = bool(len(self._test_declarations))
        for test in self._test_declarations:
            for line in str(self[test]).splitlines():
                resp += f'\t{line}\n'
            passes &= bool(self[test])
        return resp.expandtabs(3)
    def __bool__(self):
        if not len(self):
            #No tests declared
            return True
        return bool(functools.reduce(lambda a,b: a and b, [bool(self[k]) for k in self]))
    def __iter__(self):
        '''test declaration names'''
        return iter(self._test_declarations)
    def __len__(self):
        return len(self.get_test_declarations())
    def __getitem__(self, key):
        return self._test_results[key]
    def _register_test(self, name, **kwargs):
        _test_declaration = collections.namedtuple('test_declaration', ['test_name']+list(kwargs.keys()))
        if name in self._test_declarations:
            raise Exception(f'Duplicated test name {name} within module {self.get_name()}!')
        self._test_declarations[name] = _test_declaration(  test_name=name,
                                                            **kwargs
                                                               )
        self._test_results[name] = self._test_results_list(name = name, upper_limit=self._test_declarations[name].upper_limit, lower_limit=self._test_declarations[name].lower_limit)
        self._ate_results[name] = []
        return self._test_declarations[name]
    def _register_test_failure(self, name, reason, conditions, query=None):
        if name not in self._test_declarations:
            raise Exception(f'Undeclared test results: {name}')
        failure_result = self._test_result(test_name=name,
                                           conditions=conditions,
                                           min_data=None,
                                           max_data=None,
                                           passes=False,
                                           failure_reason=reason,
                                           collected_data=[], #Give a chance to re-compute summary statistics if more data comes in later.
                                           plot=[], #Mutable; add later
                                           query=query,
                                          )
        self._test_results[name].append(failure_result)
        return failure_result
    def _evaluate_database(self, name, database):
        query = (database.sql_query, database.params)
        if database.get_column_names() is None:
            print(f'\nWARNING! The sql query returned nothing. Please double check the query parameters.')
            return self._register_test_failure(name=name, reason="No submitted data.", conditions=None, query=query)
        conditions_columns = database.get_column_names()[1:]
        nt_type = collections.namedtuple('distincts',conditions_columns)
        database = database.to_list()
        distincts = {nt_type._make(freeze(row[1:])) for row in database}
        try:
          distincts = sorted(distincts)
        except TypeError:
          pass
        rowcount = len(database)
        match_count = 0
        for condition in distincts:
            data = [row[0] for row in database if freeze(row[1:]) == condition]
            self._evaluate_list(name=name, iter_data=data, conditions=condition._asdict() if len(conditions_columns) else None, query=query) #todo, consider reimplementing __str__ instead of dict conversion.
            match_count += len(data)
        assert match_count == rowcount
    def _evaluate_list(self, name, iter_data, conditions, query=None):
        if name not in self._test_declarations:
            self._register_test(name=name, **self.test_limits[name])
            self._test_results[name] = self._test_results_list(name=name, upper_limit=self.test_limits[name]['upper_limit'], lower_limit=self.test_limits[name]['lower_limit'])
        #############################################################
        # TODO deal with functional test pass/fail non-numeric data #
        #############################################################
        if isinstance(iter_data, numbers.Number):
            iter_data = [iter_data]
        elif isinstance(iter_data, (list, tuple)):
            # An ordered list is passed in for sequence order. Needs to be double-listed to avoid iterating the sequence itself!
            pass
        if iter_data is None:
            return self._register_test_failure(name=name, reason="None encountered in submitted data.", conditions=conditions, query=query)
        if None in iter_data:
            t_f = self._register_test_failure(name=name, reason="None encountered in submitted data.", conditions=conditions, query=query)
            iter_data = [item for item in iter_data if item is not None]
            if not len(iter_data): 
                return t_f

        self.test_limits[name]['upper_limit'] = self.test_limits[name]['upper_limit'] if self.test_limits[name]['upper_limit']==self.test_limits[name]['upper_limit'] else None
        self.test_limits[name]['lower_limit'] = self.test_limits[name]['lower_limit'] if self.test_limits[name]['lower_limit']==self.test_limits[name]['lower_limit'] else None
        assert (self.test_limits[name]['upper_limit'] is not None or self.test_limits[name]['lower_limit'] is not None), f'Something is wrong with test limits for {name}. Contact support.'
        if self.test_limits[name]['upper_limit'] != self.test_limits[name]['lower_limit']:
            passes = functools.reduce(lambda x,y: x and y, [data_pt is not None \
                                                            and (self.test_limits[name]['upper_limit'] is None or data_pt <= self.test_limits[name]['upper_limit']) \
                                                            and (self.test_limits[name]['lower_limit'] is None or data_pt >= self.test_limits[name]['lower_limit']) \
                                                            for data_pt in iter_data
                                                            ]
                                      )
        else:
            passes = functools.reduce(lambda x,y: x and y, [data_pt is not None \
                                                            and (data_pt == self.test_limits[name]['upper_limit']) #upper==lower \
                                                            for data_pt in iter_data
                                                            ]
                                      )
        min_data = min(iter_data)
        max_data = max(iter_data)
        new_result_record = self._test_result(test_name=name,
                                              conditions=conditions,
                                              min_data=min_data,
                                              max_data=max_data,
                                              passes=passes,
                                              failure_reason='',
                                              collected_data=iter_data, #Give a chance to re-compute summary statistics if more data comes in later.
                                              plot=[], #Mutable; add later
                                              query=query,
                                              )
        self._test_results[name].append(new_result_record)
        return new_result_record

class ResultsSchemaMismatchException(Exception):
    '''Mismatch between writer and reader formats'''

class Test_Results_Reload(Test_Results):
    '''Rereads a json file and converts it back to a Test_Results compatible schema.'''
    def __init__(self, results_json='test_results.json'):
        self._schema_version = 1.0
        self._test_declarations = collections.OrderedDict()
        self._test_results = collections.OrderedDict()
        with open(results_json, mode='r', encoding='utf-8') as f:
            self.__results = json.load(f)
            f.close()
        if self.__results['schema_version'] != self._schema_version:
            raise ResultsSchemaMismatchException(f'Results file {results_json} written with schema version {self.__results["schema_version"]}, but reader expecting {self._schema_version}.')
        self._init(name=self.__results['test_module'], module=None)
        self._set_traceability_info(datetime=self.__results["collection_date"], **self.__results["traceability"])
        for test in self.__results['tests']:
            self._register_test(name=test, **self.__results['tests'][test]['declaration'])
            for case in self.__results['tests'][test]['results']['cases']:
                for trial in case['case_results']:
                    self._test_results[test].append(self._test_result(test_name=test,
                                                                      conditions=case['conditions'],
                                                                      plot=[],
                                                                      **trial
                                                                      )
                                                   )
    def json_report(self, filename='test_results_rewrite.json'):
        with open(filename, 'wb') as f:
            f.write(super().json_report().encode('utf-8'))
            f.close()

class correlation_results(generic_results):
    _correlation_declaration = collections.namedtuple('correlation_declaration', ['refid_name', 'ATE_test', 'ATE_subtest', 'owner', 'assignee', 'lower_limit', 'upper_limit', 'unit', 'description', 'notes', 'limits_units_percentage'])
    class _correlation_result(collections.namedtuple('correlation_result', ['refid_name', 'temperature', 'conditions', 'bench_data', 'ate_data', 'error', 'failure_reason', 'passes', 'query'])):
        '''add some helper moethods for easy summary'''
        def __new__(cls, **kwargs):
            '''fix (allowed) missing fields. FOr instance, original JSON didn't retain SQL query string.'''
            if 'query' not in kwargs:
                kwargs['query'] = None
            return super().__new__(cls, **kwargs)
        def __bool__(self):
            return bool(self.passes) #numpy _bool infiltration
        def __str__(self):
            
            # summary_str = ''
            # summary_str += f'{self.conditions}\tTRIALS:{len(self)}\tVERDICT:{"PASS" if self else "FAIL"}\n'.expandtabs()
            # summary_str += f'\tMIN:{self._min():g}\n' if not self else ''
            # summary_str += f'\tMAX:{self._max():g}\n' if not self else ''
            
            summary_str = ''
            summary_str += f'\tERROR: {self.error:g}' if self.error is not None else ''
            summary_str += f'\t{self.failure_reason}' if self.failure_reason != '' else ''
            #TODO bench/ate ?
            summary_str += f'\tVERDICT:{"PASS" if self else "FAIL"}\n'
            return summary_str
        # def __add__(self, other):
            # assert isinstance(other, type(self))
            # assert self.refid_name == other.refid_name
            # assert self.temperature == other.temperature
            # assert self.conditions == other.conditions
            # return type(self)(refid_name=self.refid_name,
                              # temperature=self.temperature,
                              # conditions=self.conditions,
                              # bench_data=???,
                              # ate_data=???,
                              # error=???,
                              # passes=self.passes and other.passes,
                              # failure_reason=f'{self.failure_reason}{other.failure_reason}', #TODO cleanup format
                             # )
    class _correlation_results_list(list):
        '''helper methods'''
        def __init__(self, declaration):
            self._declaration = declaration
        def __bool__(self):
            if not len(self):
                return False
            return bool(functools.reduce(lambda a,b: a and b, [item.passes for item in self]))
        def __str__(self):
            resp = f'{self._declaration.refid_name}\n'
            resp += f'\tLIMITS:\t'
            resp += f'LSL: {self._declaration.lower_limit:g}\t' if self._declaration.lower_limit is not None else ''
            resp += f'USL: {self._declaration.upper_limit:g}\t' if self._declaration.upper_limit is not None else ''
            resp += '\n'
            resp += '\tRESULTS:\n'
            for temperature in self.get_temperatures():
                resp += f'\t\tTemperature {temperature}\n'
                temp_group = self.filter_temperature(temperature) #sorted??
                if {result.failure_reason for result in temp_group} == {'ATE data missing.'} and not functools.reduce(lambda a,b: a or b, [res.passes for res in temp_group]): #Magic number alert!!!!!
                    #Each and every one failed, and because temp data was missing.
                    resp += '\t\t\tATE data missing.\n'
                    resp += f'\t\tTemperature {temperature} summary {"PASS" if temp_group else "FAIL"} ({len(temp_group)} case{"s" if len(temp_group) != 1 else ""}).\n'
                    continue
                for cond_hash, cond_orig in temp_group.get_conditions().items():
                    resp_cond = f'{cond_orig}'
                    cond_group = temp_group.filter_conditions(cond_hash)
                    if len(cond_group) > 1:
                        resp += f'\t\t\t{resp_cond}\n'
                        for result in cond_group:
                            res_line = str(result).lstrip('\t').expandtabs()
                            resp += f'\t\t\t\t{res_line}'
                    else:
                        for result in cond_group:
                            resp_cond = f'{resp_cond}{result}'.expandtabs()
                            resp += f'\t\t\t{resp_cond}'
                resp += f'\t\tTemperature {temperature} summary {"PASS" if temp_group else "FAIL"} ({len(temp_group)} case{"s" if len(temp_group) != 1 else ""}).\n'
            resp += f'{self._declaration.refid_name} Summary {"PASS" if self else "FAIL"}.\n'
            return resp
        def _min_error(self):
            if not len(self):
                return None
            return functools.reduce(none_min, [res.error for res in self])
        def _max_error(self):
            if not len(self):
                return None
            return functools.reduce(none_max, [res.error for res in self])
        def get_conditions(self):
            #TODO fix hash collisions???
            return {make_hash(data_group.conditions): data_group.conditions for data_group in self}
        def get_temperatures(self):
            return sorted({data_group.temperature for data_group in self})
        def filter_conditions(self, condition_hash):
            ret = type(self)(declaration=self._declaration)
            for data_group in self:
                if make_hash(data_group.conditions) == condition_hash:
                    ret.append(data_group)
            return ret
        def filter_temperature(self, temperature):
            '''single temp or list'''
            try:
                iter(temperature)
            except TypeError as e:
                temperatures = (temperature,)
            else:
                temperatures = temperature
            ret = type(self)(declaration=self._declaration)
            for data_group in self:
                if data_group.temperature in temperatures:
                    ret.append(data_group)
            return ret
        # Doesn't make sense yet, since results aren't stored as a list; no way to aggregate without data model change.
        # def factored(self):
            # '''returns new object; doesn't modifiy existing one in place
            # merges all resutls from like temperature and conditions'''
            # ret = type(self)(declaration=self._declaration)
            # for temperature in self.get_temperatures():
                # for cond_hash in self.get_conditions():
                    # data_group = functools.reduce(lambda a,b: a+b, [data_group for data_group in self if make_hash(data_group.conditions)==cond_hash and data_group.temperature==temperature])
                    # ret.append(data_group)
            # return ret

    def __init__(self, name, module):
        '''TODO'''
        self._correlation_declarations = collections.OrderedDict()
        self._correlation_results = collections.OrderedDict()
        self._init(name, module)
    def __str__(self):
        resp = ''
        for test in self._correlation_declarations:
            for line in str(self[test]).splitlines():
                resp += f'\t{line}\n'
        return resp.expandtabs(3)
        return resp
    def __getitem__(self, key):
        return self._correlation_results[key]
    def __iter__(self):
        return iter(self._correlation_declarations.keys())
    def json_report(self):
        return self._json_report(declarations=self._correlation_declarations, results=self._correlation_results)
    def get_correlation_declarations(self):
        return list(self._correlation_declarations.keys())
    def get_correlation_declaration(self, key):
        return self._correlation_declarations[key]
    def _is_in_spec(self, name, error):
        declaration = self._correlation_declarations[name]
        if error is None:
            return False
        if declaration.upper_limit is not None and error > declaration.upper_limit:
            return False
        if declaration.lower_limit is not None and error < declaration.lower_limit:
            return False
        return True
    def _error(self, refid_name,temperature,bench_data):
        # Won't work when module doesn't exist, ex json reload.
        declaration = self._correlation_declarations[refid_name]
        # Massage hot and cold a bit to force alignment with ATE data
        # Per concern raised by Ashish and decided with Sauparna 2022/01/13
        if temperature is None:
          t_ish = None # Ambient
        elif isinstance(temperature, str) and temperature.upper() == 'NULL':
          t_ish = None # Ambient with sqlite replacement in test script
        elif -55 <= temperature <= -40:
          t_ish = -40
        elif 120 <= temperature <= 160:
          t_ish = 150
        elif 15 <= temperature <= 35:
          t_ish = 25
        else:
          t_ish = temperature
        self.ate_result = self._module.get_correlation_data_scalar(REFID=refid_name, temperature=t_ish)
        if declaration.limits_units_percentage:
            return (self.ate_result - bench_data) / bench_data
        else:
            return self.ate_result - bench_data

    def __len__(self):
        return len(self._correlation_declarations.keys())
    def __bool__(self):
        if not len(self):
            #No declarations
            return True
        return bool(functools.reduce(lambda a,b: a and b, (self[k] for k in self)))
    
    def _register_correlation_test(self, refid_name, ATE_test, ATE_subtest, owner, assignee, lower_limit, upper_limit, unit, description, notes, limits_units_percentage):
        if refid_name in self._correlation_declarations:
            raise Exception(f'Duplicated correlation refid name {refid_name} within module {self.get_name()}!')
        self._correlation_declarations[refid_name] = self._correlation_declaration(refid_name=              refid_name, 
                                                                             ATE_test=                ATE_test,
                                                                             ATE_subtest=             ATE_subtest,
                                                                             owner=                   owner,
                                                                             assignee=                assignee,
                                                                             lower_limit=             lower_limit,
                                                                             upper_limit=             upper_limit,
                                                                             unit=                    unit,
                                                                             description=             description,
                                                                             notes=                   notes,
                                                                             limits_units_percentage= limits_units_percentage,
                                                          )
        self._correlation_results[refid_name] = self._correlation_results_list(declaration=self._correlation_declarations[refid_name])
        return self._correlation_declarations[refid_name]
    def _register_correlation_result(self, refid_name, iter_data, conditions, query=None): # TODO conditions
        if refid_name not in self._correlation_declarations:
            raise Exception(f'Undeclared correlation results: {refid_name}')
        if type(iter_data) == sqlite_data:
            query = (iter_data.sql_query, iter_data.params)
        if type(iter_data) == sqlite_data and len(iter_data.get_column_names()) > 2:
            conditions_columns = iter_data.get_column_names()[2:]
            nt_type = collections.namedtuple('distincts',conditions_columns)
            #distincts = iter_data.get_distinct(conditions_columns, force_tuple=True)
            iter_data = iter_data.to_list()
            distincts = {nt_type._make(freeze(row[2:])) for row in iter_data}
            try:
                distincts = sorted(distincts)
            except TypeError:
                pass
            rowcount = len(iter_data)
            match_count = 0
            assert conditions is None, "TODO: This isn't a permanent error, but it hasn't been impllemented yet. What to do about explicit conditions???? Append???"
            for condition in distincts:
                data = [(row[0], row[1]) for row in iter_data if freeze(row[2:]) == condition]
                self._register_correlation_result(refid_name=refid_name, iter_data=data, conditions=condition._asdict(), query=query) #todo, consider reimplementing __str__ instead of dict conversion.
                match_count += len(data)
            assert match_count == rowcount
            return
        for (result, temperature) in iter_data:
            #todo dimensional error handling?
            if result is None:
                # There's no bench data. Something has gone pretty wrong already, and this correlation is doomed to failure.
                # Just to be extra-nice, we'll make a Hail Mary attempt to fetch ATE data, for the permanent record. It might be useful for debugging.
                # If there were bench data, this work would be done inside self._error.
                if temperature is None:
                  t_ish = None # Ambient
                elif isinstance(temperature, str) and temperature.upper() == 'NULL':
                  t_ish = None # Ambient with sqlite replacement in test script
                elif -55 <= temperature <= -40:
                  t_ish = -40
                elif 120 <= temperature <= 160:
                  t_ish = 150
                else:
                  # Let it through. 25 will match. Others won't
                  t_ish = temperature
                try:
                  ate_result = self._module.get_correlation_data_scalar(REFID=refid_name, temperature=t_ish)
                except ATEDataException as e:
                  ate_result = None
                self._register_correlation_failure(name=refid_name, reason='Bench data missing.', temperature=temperature, conditions=conditions, ate_data=ate_result, query=query)
                continue
            try:
                # breakpoint()
                if temperature == 'NULL':
                    temperature = 25
                err=self._error(refid_name,temperature,result)
            except test_module.ATETBDException:
                # self._register_correlation_failure(name=refid_name, reason='Cannot fetch ATE data because the test number is listed "TBD".', temperature=None, conditions='')
                # break
                # Let all the bench data in, for posterity and ease of debug, even when no ATE data is available and no error calculation is possible.
                self._register_correlation_failure(name=refid_name, reason='Cannot fetch ATE data because the test number is listed "TBD".', temperature=temperature, conditions=conditions, bench_data=result, query=query)
                continue
            except test_module.ATENAException:
                # self._register_correlation_failure(name=refid_name, reason='Cannot fetch ATE data because the test number is listed "NA".', temperature=None, conditions='')
                # break
                self._register_correlation_failure(name=refid_name, reason='Cannot fetch ATE data because the test number is listed "NA".', temperature=temperature, conditions=conditions, bench_data=result, query=query)
                continue
            except TypeError:
                # Magic number alert. Matches ATE temp massaging in _error()
                if temperature is None:
                  # FTT, QAR
                  expected_missing = False
                  failure_reason = 'QAR/FTT ATE data missing.'
                elif -55 <= temperature <= -40:
                  # QAC
                  expected_missing = False
                  failure_reason = 'QAC ATE data missing.'
                # elif temperature == 25:
                elif 15 <= temperature <= 35:
                  # FTT, QAR
                  expected_missing = False
                  failure_reason = 'QAR/FTT ATE data missing.'
                elif 120 <= temperature <= 160:
                  # QAH
                  expected_missing = False
                  failure_reason = 'QAH ATE data missing.'
                else:
                  expected_missing = True
                  failure_reason = f'{temperature}C is not a QAC, QAR, QAH, CORR temperature.'
                self._correlation_results[refid_name].append(self._correlation_result(refid_name=refid_name, 
                                                                                      temperature=temperature,
                                                                                      conditions=conditions,
                                                                                      bench_data=result,
                                                                                      ate_data=None,
                                                                                      error=None,
                                                                                      failure_reason=failure_reason,
                                                                                      passes=expected_missing,
                                                                                      query=query,
                                                                                      )
                                                            )
                
                continue
            else:
                passes  = self._is_in_spec(refid_name, err)
                self._correlation_results[refid_name].append(self._correlation_result(refid_name  = refid_name, 
                                                                                      temperature = temperature,
                                                                                      conditions=conditions,
                                                                                      bench_data  = result,
                                                                                      ate_data=self.ate_result,
                                                                                      error=err,
                                                                                      failure_reason='', #TODO None (new schema?)
                                                                                      passes=passes,
                                                                                      query=query,
                                                                                     ))
    def _register_correlation_failure(self, name, reason, temperature, conditions, bench_data=None, ate_data=None, query=None):
        if name not in self._correlation_declarations:
            raise Exception(f'Undeclared correlation results: {name}')
        self._correlation_results[name].append(self._correlation_result(refid_name=name,
                                                                        temperature=temperature,
                                                                        conditions=conditions,
                                                                        bench_data=bench_data,
                                                                        error=None,
                                                                        ate_data=ate_data,
                                                                        failure_reason=reason,
                                                                        passes=False,
                                                                        query=query,
                                                                        ))

class correlation_results_reload(correlation_results):
    def __init__(self, results_json='correlation_results.json'):
        self._schema_version = 1.1
        self._correlation_declarations = collections.OrderedDict()
        self._correlation_results = collections.OrderedDict()
        with open(results_json, mode='r', encoding='utf-8') as f:
            self.__results = json.load(f)
            f.close()
        # if self.__results['schema_version'] != self._schema_version:
        if self.__results['schema_version'] not in (0.2, 1.0, 1.1):
            raise ResultsSchemaMismatchException(f'Results file {results_json} written with schema version {self.__results["schema_version"]}, but reader expecting {self._schema_version}.')
        self._init(name=self.__results['test_module'], module=None)
        # print(f'INFO Loading correlation {self.get_name()} record produced on {self.__results["report_date"]} from data collected on {self.__results["collection_date"]}.\n\t({results_json})') #TODO too loud for logs?
        self._set_traceability_info(datetime=self.__results["collection_date"], **self.__results["traceability"])
        # TODO flag json re-output as derivative????
        for test in self.__results['tests']:
            self._register_correlation_test(refid_name=test, **self.__results['tests'][test]['declaration'])
            for temperature_group in self.__results['tests'][test]['results']['temperatures']:
                temperature = temperature_group['temperature']
                for condition_group in temperature_group['cases']:
                    for result in condition_group['case_results']:
                        self._correlation_results[test].append(self._correlation_result(refid_name  = test, 
                                                                                        temperature = temperature,
                                                                                        conditions=condition_group['conditions'],
                                                                                        **result,
                                                                                       )
                                                              )
    def json_report(self, filename='correlation_results_rewrite.json'):
        with open(filename, 'wb') as f:
            f.write(super().json_report().encode('utf-8'))
            f.close()