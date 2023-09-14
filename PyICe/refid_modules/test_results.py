from PyICe import lab_utils, LTC_plot
from PyICe.refid_modules import test_module
import collections
import datetime
import functools
import json
import numbers
import pprint
from numpy import bool_, ndarray

pp = pprint.PrettyPrinter(indent=4)
# pp.pformat(obj)
# pp.pprint(obj)
# print = pp.pprint

# 2021/12/14 Dave Simmons
# Notes collected below w.r.t deficiencies identified in the output format, and tests results module more generally
# Gathered through discussions with Sauparna and Steve.
# Intend to fix them incrementally and remove comment line here as-addressed.

# eeprom contents logging
# change stowe logger to directly capture collect() method?
# add compile() to report? Logging not necessary because it's re-run at report gen time.
# https://json-schema.org/understanding-json-schema/structuring.html#structuring
# test results schema checker
# 
# https://jama.analog.com/perspective.req#/items/4382084?projectId=597
# plot hyperlink
# data hyperlink
# conditions
# scope of measurement
# test method
# jira link

# https://docs.python.org/3/library/dataclasses.html


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
    raise TypeError("Something slipped through the freeze function. Contact pyice-developers@analog.com. Or file a bug report at jira.analog.com/pyice") from e
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
    '''Parent of test_results and correlation_results and keeper of any commonalities.'''
    def __init__(self):
        raise Exception("This class isn't supposed to be instantiated directly.")
        # TODO https://docs.python.org/3/library/abc.html ?
    def _init(self, name, module):
        self._name = name
        self._traceability_info = collections.OrderedDict()
                                  #{'TRACEABILITY_HASH': None,
                                  # 'REVID': None,
                                  # 'BENCH_CONFIGURATION': None,
                                  # 'EQUIPMENT_INFO': None,
                                  # 'OPERATOR': None,
                                  # 'AUTHOR': None,
                                  # 'OWNER': None,
                                  # 'VARIANT': None,
                                  # 'VARIANT_REVISION': None,
                                  # 'STDF_FILE': None,
                                  # # SWARM LINKS?
                                  #}
                                  # datetime
        self._module = module
        self.table_name=None
        self.db_filepath=None
    def get_name(self):
        return self._name
    def get_traceability_info(self):
        return self._traceability_info
    def set_table_name(self,table_name):
        self.table_name=table_name
    def set_db_filepath(self,db_filepath):
        self.db_filepath=db_filepath
    def _set_traceability_info(self, **kwargs):
        for k,v in kwargs.items():
            if True: #k in self._traceability_info.keys():
                self._traceability_info[k] = v
            else:
                raise Exception(f'Received unexpected traceability field {k} with value {v}. Contact pyice-developers@analog.com. Or file a bug report at jira.analog.com/pyice.')
        for k in ["datetime",
                  "TRACEABILITY_HASH",
                  "bench_operator",
                  "bench_instruments",
                  "comment",
                  "test_swarmlink",
                  "test_cumulative_time",
                  "bench_configuration",
                  "revid",
                  "f_die_fab_2_0_",
                  "f_die_fab_4_3_",
                  "f_die_parent_child_9_8_",
                  "f_die_loc_y",
                  "f_die_loc_x",
                  "f_die_running_7_0_",
                  "f_die_parent_child_7_0_",
                  "f_die_fab_6_5_",
                  "f_die_wafer_number",
                  "f_die_running_9_8_",
                  "f_die_week",
                  "f_die_year",
                  "START_T",
                  "STDF_file",
                  "config_file",
                  "config_change",
                  "config_date",
                  "variant_datasheet",
                  "variant_shell",
                  ]:
            try:
                assert k in self._traceability_info, f'ERROR: {k} key missing from {self.get_name()} traceability information.'
            except AssertionError as e:
                if input (f'{e} Continue anyway? ').lower() not in ("y", "yes"):
                    raise e
                else:
                    self._traceability_info[k] = None
        try:
            self._traceability_info['ATE_date'] = datetime.datetime.utcfromtimestamp(self._traceability_info['START_T']).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except TypeError as e:
            self._traceability_info['ATE_date'] = None            # "app_configuration" expected with EEPROM hardware (Schema 1.0), but not required (Schema 0.2)
            #         "cap_mb_isolator_serialnum",
            #         "cap_mb_isolatorboard_component_purpose",
            #         "cap_mb_isolatorboard_data",
            #         "targetboard_serialnum",
            #         "targetboard_component_purpose",
            #         "targetboard_data",
            # "skew" expected Schema 1.1 onward.
        


    def _json_report(self, declarations, results, ate_results=[]):
    # def _json_report(self, declarations, results, ate_results=[], *args):
        # if not len(declarations.keys()):
        if not len(self):
            # No tests (or no correlations) in this module
            # Omit whole report, since there's nothing to report.
            return None
        class CustomJSONizer(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bool_):
                    return bool(obj)
                elif isinstance(obj, datetime.datetime):
                    return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                elif isinstance(obj, ndarray):
                    return obj.tolist()
                # elif isinstance(obj, np.integer):
                    # return int(obj)
                # elif isinstance(obj, np.floating):
                    # return float(obj)
                else:
                    try:
                        return super().default(obj)
                    except TypeError as e:
                        print(f'JSON Serialization error with object of type {type(obj)}:')
                        print(obj)
                        breakpoint()
                        raise e
        res_dict = {}
        # res_dict['schema_version'] = 0.2 # Increment after release
        # res_dict['schema_version'] = 1.0 # Traceable eval hardware via eeprom
        # res_dict['schema_version'] = 1.1 # Add skew map (will provide workaround for legacy format) and 5% (of window) autocorrelation hint (output only - remade from raw data).
        # res_dict['schema_version'] = 1.2 # Add a human readable version of the ATE test datetime to traceability.
        res_dict['schema_version'] = 1.3 # Add table_name and dirpath for easy eval_report generation.
        res_dict['test_module'] = self.get_name()
        res_dict['report_date'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        trace_data = self.get_traceability_info()
        res_dict['collection_date'] = trace_data['datetime']
        res_dict['table_name'] = self.table_name
        res_dict['filepath'] = self.db_filepath
        res_dict['traceability'] = {k:v for k,v in trace_data.items() if k not in ['datetime']}
        # for f in *args:
            # f(res_dict)
        res_dict['tests'] = {}
        for t_d in declarations:
            res_dict['tests'][t_d] = {}
            res_dict['tests'][t_d]['declaration'] = {k:v for k,v in declarations[t_d]._asdict().items() if k not in ['test_name', 'refid_name']}
            try:
                results[t_d]
            except KeyError as e:
                res_dict['tests'][t_d]['passes'] = False
            else:
                res_dict['tests'][t_d]['results'] = {}
               
                if isinstance(self, test_results):
                    res_dict['tests'][t_d]['results']['cases'] = []
                    res_dict['tests'][t_d]['results']['summary'] = {}
                    for condition_hash, condition_orig in results[t_d].get_conditions().items():
                        filter_results = results[t_d].filter(condition_hash)
                        cond_dict =  {'conditions': condition_orig, #TODO put back to dictionary!
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
                    res_dict['tests'][t_d]['ate_results'] = []
                    for ate_r in ate_results[t_d]:
                        res_dict['tests'][t_d]['ate_results'].append({k:v for k,v in ate_r._asdict().items() if k not in ['test_name']})
                        #TODO tdegc alignment!
                        try:
                            min_error = ate_r.result - results[t_d]._min()
                        except TypeError as e:
                            min_error = None
                        try:
                            max_error = ate_r.result - results[t_d]._max()
                        except TypeError as e:
                            max_error = None
                        res_dict['tests'][t_d]['ate_results'][-1]['min_error'] = min_error
                        res_dict['tests'][t_d]['ate_results'][-1]['max_error'] = max_error
                        max_abs_error = none_max(none_abs(min_error), none_abs(max_error))
                        if max_abs_error is not None and res_dict['tests'][t_d]['declaration']['correlation_autolimit'] is not None:
                            passes = max_abs_error <= res_dict['tests'][t_d]['declaration']['correlation_autolimit']
                        else:
                            # can't compare something
                            passes = True
                        res_dict['tests'][t_d]['ate_results'][-1]['passes'] = passes
                elif isinstance(self, correlation_results):
                    res_dict['tests'][t_d]['results']['temperatures'] = []
                    for temperature in results[t_d].get_temperatures():
                        temperature_dict = {'temperature': temperature,
                                            'cases': [],
                                            # 'summary': {},
                                           }
                        res_dict['tests'][t_d]['results']['temperatures'].append(temperature_dict)
                        temp_group = results[t_d].filter_temperature(temperature)
                        for condition_hash, condition_orig in temp_group.get_conditions().items():
                            cond_group = temp_group.filter_conditions(condition_hash)
                            cond_dict =  {'conditions': condition_orig,
                                          'case_results': [{k:v for k,v in cond._asdict().items() if k not in ['refid_name', 'temperature', 'conditions']} for cond in cond_group],
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
        # TODO Signature/CRC?
        return json.dumps(res_dict, indent=2, ensure_ascii=False, cls=CustomJSONizer)

class test_results(generic_results):
    _ate_result = collections.namedtuple('ate_result', ['test_name', 'result', 'temperature']) # 'lower_limit', 'upper_limit', FROM DLOG?? Prob discarded....
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
            assert self.query == other.query, f"ERROR {self.test_name} grouping mismatch. Grouped results have unexpectedly disparate SQL queries. Consider adding conditions by selecting addtional columns or by keyword argument. If you think you've received this message in error, see Dave." 
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
        def __init__(self, declaration):
            self._declaration = declaration
            super().__init__()
        def __bool__(self):
            if not len(self):
                return False
            return bool(functools.reduce(lambda a,b: a and b, [item.passes for item in self]))
        def __str__(self):
            resp = ''
            resp += f'{self._declaration.test_name}\n'
            resp += f'\tLIMITS:'
            if self._declaration.upper_limit == self._declaration.lower_limit: #DOES THIS WORK? WRONG CLASS?????
                #Exact test
                try:
                    resp += f'\t SL:{self._declaration.upper_limit:g}'
                except TypeError as e:
                    resp += f'\t SL:{self._declaration.upper_limit}'
            else:
                if self._declaration.lower_limit is not None:
                    resp += f'\tLSL:{self._declaration.lower_limit:g}'
                if self._declaration.upper_limit is not None:
                    resp += f'\tUSL:{self._declaration.upper_limit:g}'
            resp += '\n'
            resp += '\tRESULTS:\n'
            for cond_res in self.factored():
                for line in str(cond_res).splitlines():
                    resp += f'\t\t{line}\n'
            resp += f'{self._declaration.test_name} summary {"PASS" if self else "FAIL"}.\n'
            return resp
        def _min(self):
            if not len(self):
                return None
            return functools.reduce(none_min, (r._min() for r in self)) #None creeps in from failures
        def _max(self):
            if not len(self):
                return None
            return functools.reduce(none_max, (r._max() for r in self)) #None creeps in from failures
        def get_conditions(self):
            #TODO fix hash collisions???
            return {make_hash(data_group.conditions): data_group.conditions for data_group in self}
        def filter(self, condition_hash):
            ret = type(self)(declaration=self._declaration.test_name)
            for data_group in self:
                if make_hash(data_group.conditions) == condition_hash:
                    ret.append(data_group)
            return ret
        def factored(self):
            '''returns new object; doesn't modifiy existing one in place
            merges all resutls from like conditions'''
            ret = type(self)(declaration=self._declaration.test_name)
            for cond_hash in self.get_conditions():
                our_list = [data_group for data_group in self if make_hash(data_group.conditions)==cond_hash]
                if cond_hash == make_hash(None) and not sum([len(x) for x in our_list]):
                    ## We got here because no rows were returned and conditions were lost. Red Flag.
                    [ret.append(x) for x in our_list]
                elif cond_hash == make_hash(None) and not min([len(x) for x in our_list]):
                    raise Exception("There is a mix in the group of no conditions of no results and some results. For want of an example or test case, how to handle that is presently unclear. Please contact support.")
                else:
                    data_group = functools.reduce(lambda a,b: a+b, our_list)
                    ret.append(data_group)
            return ret
    def __init__(self, name, module):
        '''TODO'''
        self._test_declarations = collections.OrderedDict()
        self._test_results = collections.OrderedDict()
        self._ate_results = collections.OrderedDict()
        self._init(name, module)
    def json_report(self):
        return self._json_report(declarations=self._test_declarations, results=self._test_results, ate_results=self._ate_results)
        # return self._json_report(declarations=self._test_declarations, results=self._test_results, *args)
    def _set_additional_registration_arguments(self, *args):
        self._test_declaration = collections.namedtuple('test_declaration', ['test_name', 'lower_limit', 'upper_limit', 'correlation_autolimit', *args])
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
        return iter(self._test_declarations.keys())
    def __len__(self):
        return len(self.get_test_declarations())
    def __getitem__(self, key):
        return self._test_results[key]
    def _plot(self, key=None):
        '''how should this work? one at a time or all together?'''
        # TODO keep or remove plotting?
        unit_axis_conversion = {
                                'µA':"CURRENT (µA)",
                                'mA':"CURRENT (mA)",
                                'A':"CURRENT (A)",
                                'mV':"VOLTAGE (mV)",
                                'V':"VOLTAGE (V)",
                                '%':"PERCENT (%)",
                                'µs':"TIME (µs)",
                                'ns':"TIME (ns)",
                                's':"TIME (s)",
                                'P|F':"Pass/Fail",
                                'W':"Power (W)",
                                'MHz':"FREQUENCY (MHz)",
                                'Ω':"RESISTANCE (Ω)",
                                'kΩ':"RESISTANCE (kΩ)",
                                'pF':"CAPACITANCE (pF)",
                               }
        if key is not None:
            tsts = [key]
        else:
            tsts = [k for k in self]
        for tst in tsts:
            tst_decl = self._test_declarations[tst]
            tst_rslts = self._test_results[tst]
            passes = functools.reduce(lambda a,b: a and b, [data_group.passes for data_group in tst_rslts]) if len(tst_rslts) else False # No data submitted.
            plt = LTC_plot.plot(plot_title=f'{tst_decl.test_name}\n{"PASS" if passes else "FAIL"}',
                                plot_name=tst_decl.test_name,
                                # xaxis_label=unit_axis_conversion[tst_decl.unit] if tst_decl.unit in unit_axis_conversion else "don't know units anymore",
                                # yaxis_label='COUNT',
                                xaxis_label="TRIAL",
                                yaxis_label='VALUE',
                                # xlims=(tst_rslts.min_data, tst_rslts.max_data),
                                # xlims=(foo, bar),
                                xlims=None,
                                ylims=None,
                                xminor=None,
                                xdivs=4,
                                yminor=None,
                                ydivs=10,
                                logx=False,
                                logy=False
                               )
            scatter_data = []
            xdata=0
            for data_group in tst_rslts:
                for ydata in data_group.collected_data:
                    scatter_data.append((xdata,ydata))
                    xdata+=1
            plt.add_scatter(axis=1,
                            data=scatter_data,
                            color=LTC_plot.LT_RED_2,
                            marker='*',
                            legend=str(data_group.conditions), #TODO Notes field?
                            )
            # This autoranging stuff has problems when empty/Null/None data gets in this far. It crashes matplotlib limit scaling functions. Noted here, but hopefully that type of test result is alwasy bogus and shold be caught and dealt with before we get this far along.
            if tst_decl.lower_limit is not None:
                plt.add_horizontal_line(value=tst_decl.lower_limit, xrange=None, note=None, color=[1,0,0])
            if tst_decl.upper_limit is not None:
                plt.add_horizontal_line(value=tst_decl.upper_limit, xrange=None, note=None, color=[1,0,0])
            try:
                tst_rslts[0].plot.append(plt.create_svg(file_basename=None)) #Todo - where should the plot really go???
            except IndexError as e:
                # No data submitted!
                pass
            except ValueError as e:
                print(e) #TODO debug later. Crashing when list is submitted for population data (sequence up order). No idea what relaly happening. DJS 2021/04/05

    def _register_test(self, name, lower_limit, upper_limit, **kwargs):
        self._set_additional_registration_arguments(*list(kwargs.keys()))
        # TODO bring jira link through from REFID where possible?
        if name in self._test_declarations:
            raise Exception(f'Duplicated test name {name} within module {self.get_name()}!')
        try:
            correlation_autotolerance = 0.05 #Magic number alert. Maxim standard correlation to 5% of spec window size.
            correlation_autolimit = correlation_autotolerance*(upper_limit-lower_limit)
            if correlation_autolimit < 0:
                correlation_autolimit = None
        except TypeError as e:
            correlation_autolimit = None

        self._test_declarations[name] = self._test_declaration(test_name=name,
                                                               lower_limit=lower_limit,
                                                               upper_limit=upper_limit,
                                                               correlation_autolimit=correlation_autolimit,
                                                               **kwargs
                                                               )
        self._test_results[name] = self._test_results_list(self._test_declarations[name])
        self._ate_results[name] = []
        return self._test_declarations[name]
    def _register_ate_result(self, name, result, temperature):
        self._ate_results[name].append(self._ate_result(test_name=name,
                                                        result=result,
                                                        temperature=temperature,
                                                        )
                                      )
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
    def _register_test_result(self, name, iter_data, conditions, query=None):
        if name not in self._test_declarations:
            raise Exception(f'Undeclared test results: {name}')
        #############################################################
        # TODO deal with functional test pass/fail non-numeric data #
        #############################################################
        if type(iter_data) == lab_utils.sqlite_data:
            assert query is None
            query = (iter_data.sql_query, iter_data.params)
            if iter_data.get_column_names() is None:
                print(f'\nWARNING FROM {__name__}!\n The sql query {query} for {name} returned nothing. Please double check the query parameters.\n')
                return self._register_test_failure(name=name, reason="No submitted data.", conditions=conditions, query=query)
            if len(iter_data.get_column_names()) > 1:
                conditions_columns = iter_data.get_column_names()[1:]
                nt_type = collections.namedtuple('distincts',conditions_columns)
                # distincts = iter_data.get_distinct(conditions_columns, force_tuple=True)
                iter_data = iter_data.to_list()
                distincts = {nt_type._make(freeze(row[1:])) for row in iter_data}
                try:
                  distincts = sorted(distincts)
                except TypeError:
                  pass
                rowcount = len(iter_data)
                match_count = 0
                assert conditions is None, "TODO: This isn't a permanent error, but it hasn't been impllemented yet. What to do about explicit conditions???? Append???"
                for condition in distincts:
                    data = [row[0] for row in iter_data if freeze(row[1:]) == condition]
                    self._register_test_result(name=name, iter_data=data, conditions=condition._asdict(), query=query) #todo, consider reimplementing __str__ instead of dict conversion.
                    match_count += len(data)
                assert match_count == rowcount
                return
            else:
                iter_data = [row[0] for row in iter_data]
        elif isinstance(iter_data, numbers.Number):
            iter_data = [iter_data]
        elif isinstance(iter_data, (list, tuple)):
            # Steve passing in an ordered list for sequence order. Needs to be double-listed to avoid iterating the sequence itself!
            pass
        if iter_data is None:
            return self._register_test_failure(name=name, reason="None encountered in submitted data.", conditions=conditions, query=query)
        if None in iter_data:
            t_f = self._register_test_failure(name=name, reason="None encountered in submitted data.", conditions=conditions, query=query)
            iter_data = [item for item in iter_data if item is not None]
            if not len(iter_data): 
                return t_f
        assert (self._test_declarations[name].upper_limit is not None or self._test_declarations[name].lower_limit is not None), f'Something is wrong with test limits for {name}. See Dave.'
        if self._test_declarations[name].upper_limit != self._test_declarations[name].lower_limit:
            passes = functools.reduce(lambda x,y: x and y, [data_pt is not None \
                                                            and (self._test_declarations[name].upper_limit is None or data_pt <= self._test_declarations[name].upper_limit) \
                                                            and (self._test_declarations[name].lower_limit is None or data_pt >= self._test_declarations[name].lower_limit) \
                                                            for data_pt in iter_data
                                                            ]
                                      )
        else:
            # I think this is an exact test. Avoid arithmetic and ordering comparisons in case data isn't scalar.
            passes = functools.reduce(lambda x,y: x and y, [data_pt is not None \
                                                            and (data_pt == self._test_declarations[name].upper_limit) #upper==lower \
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
                                              # TODO Notes??
                                              )
        self._test_results[name].append(new_result_record)
        return new_result_record
        
class ResultsSchemaMismatchException(Exception):
    '''Mismatch between writer and reader formats'''

class test_results_reload(test_results):
    def __init__(self, results_json='test_results.json'):
        self._schema_version = 1.3
        self._test_declarations = collections.OrderedDict()
        self._test_results = collections.OrderedDict()
        self._ate_results = collections.OrderedDict()
        with open(results_json, mode='r', encoding='utf-8') as f:
            self.__results = json.load(f)
            f.close()
        # if self.__results['schema_version'] != self._schema_version:
        if self.__results['schema_version'] not in (0.2, 1.0, 1.1, 1.2, 1.3):
            raise ResultsSchemaMismatchException(f'Results file {results_json} written with schema version {self.__results["schema_version"]}, but reader expecting {self._schema_version}.')
        self._init(name=self.__results['test_module'], module=None)
        # print(f'INFO Loading test {self.get_name()} record produced on {self.__results["report_date"]} from data collected on {self.__results["collection_date"]}.\n\t({results_json})')  #TODO too loud for logs?
        self._set_traceability_info(datetime=self.__results["collection_date"], **self.__results["traceability"])
        # TODO flag json re-output as derivative????
        for test in self.__results['tests']:
            try:
                # Not used on read-in. Recreated from limts each time.
                del self.__results['tests'][test]['declaration']['correlation_autolimit']
            except KeyError:
                # Not present before schema 1.1
                pass
            self._register_test(name=test, **self.__results['tests'][test]['declaration'])
            for case in self.__results['tests'][test]['results']['cases']:
                for trial in case['case_results']:
                    self._test_results[test].append(self._test_result(test_name=test,
                                                                      conditions=case['conditions'],
                                                                      plot=[],
                                                                      **trial
                                                                      )
                                                   )
            for ate_data in self.__results['tests'][test]['ate_results']:
                try:
                    # Not used on read-in. Recreated from limts and raw data each time.
                    del ate_data['min_error']
                    del ate_data['max_error']
                    del ate_data['passes']
                except KeyError:
                    # Not present before schema 1.1
                    pass
                self._register_ate_result(name=test, **ate_data)
    def json_report(self, filename='test_results_rewrite.json'):
        with open(filename, 'wb') as f:
            try:
                f.write(super().json_report().encode('utf-8'))
            except:
                f.write(super().json_report().encode('utf-8'))
            f.close()
        
        
class correlation_results(generic_results):
    _correlation_declaration = collections.namedtuple('correlation_declaration', ['refid_name', 'ATE_test', 'ATE_subtest', 'owner', 'assignee', 'lower_limit', 'upper_limit', 'unit', 'description', 'notes', 'limits_units_percentage', 'requirement_reference', 'safety_critical', 'correlation_spec'])
    # _correlation_declaration = collections.namedtuple('correlation_declaration', ['refid_name', 'lower_limit', 'upper_limit', 'auxiliary'])
    class _correlation_result(collections.namedtuple('correlation_result', ['refid_name', 'temperature', 'conditions', 'bench_data', 'ate_data', 'error', 'failure_reason', 'passes', 'query'])):
    # class _correlation_result(collections.namedtuple('correlation_result', ['refid_name', 'error', 'passes', 'auxiliary'])):
        '''add some helper moethods for easy summary'''
        def __new__(cls, **kwargs):
            '''fix (allowed) missing fields. FOr instance, original JSON didn't retain SQL query string.'''
            if 'query' not in kwargs:
                kwargs['query'] = None
            return super().__new__(cls, **kwargs)
        def __bool__(self):
            return bool(self.passes) #numpy _bool infiltration
        def __str__(self):
            summary_str = ''
            summary_str += f'\tERROR: {self.error:g}' if self.error is not None else ''
            summary_str += f'\t{self.failure_reason}' if self.failure_reason is not '' else ''
            summary_str += f'\tVERDICT:{"PASS" if self else "FAIL"}\n'
            return summary_str

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
                if all('ATE data missing.' in result.failure_reason for result in temp_group) and not functools.reduce(lambda a,b: a or b, [res.passes for res in temp_group]):
                    #Each and every one failed, and because temp data was missing on ATE's side.
                    resp += '\t\t\tATE data missing.\n'
                    resp += f'\t\tTemperature {temperature} summary FAIL ({len(temp_group)} case{"s" if len(temp_group) != 1 else ""}).\n'
                    continue
                elif {result.failure_reason for result in temp_group} == {f'{temperature}C is not a QAC, QAR, QAH, CORR temperature.'}:
                    #Each and every one passed, because temp data isn't correlated.
                    resp += f'\t\t\t{temperature}C is not a QAC, QAR, QAH, CORR temperature.\n'
                    resp += f'\t\tTemperature {temperature} summary PASS ({len(temp_group)} case{"s" if len(temp_group) != 1 else ""}).\n'
                    continue
                for cond_hash, cond_orig in temp_group.get_conditions().items():
                    resp_cond = f'{cond_orig}'
                    cond_group = temp_group.filter_conditions(cond_hash)
                    try:
                        if len(cond_group) > 1:
                            resp += f'\t\t\t{resp_cond}\n'
                            if all([res.passes for res in cond_group]) and all([res.error is not None for res in cond_group]):
                                resp += f'\t\t\t\tMIN ERR: {min([res.error for res in cond_group]):.3e}\t  MAX ERR: {max([res.error for res in cond_group]):.3e}\n'
                            else:
                                for result in cond_group:
                                    res_line = str(result).lstrip('\t').expandtabs()
                                    resp += f'\t\t\t\t{res_line}'
                        else:
                            for result in cond_group:
                                resp_cond = f'{resp_cond}{result}'.expandtabs()
                                resp += f'\t\t\t{resp_cond}'
                    except Exception as e:
                        print(f'Partial resp: {resp}')
                                                                           
                        print(f'resp_cond: {resp_cond}; cond_group: {cond_group}')
                        raise e
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
        #try:
        #    resp = lab_utils.build_banner(f'Module {self.get_name()} Correlation Report Stub {self._traceability_info["TRACEABILITY_HASH"]}')
        #except KeyError:    # This will happen if a test crashes and skips the result compilation.
        #    resp = lab_utils.build_banner(f'Module {self.get_name()} Correlation Report Stub Unknown: Hash Value Error')
        resp = ''
        for test in self._correlation_declarations:
            for line in str(self[test]).splitlines():
                resp += f'\t{line}\n'
        # resp += f'Correlation Summary {"PASS" if self else "FAIL"}.\n\n'
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
    def _set_additional_correlation_attributes(self, *args):
        self._correlation_declaration = collections.namedtuple('correlation_declaration', ['refid_name', 'lower_limit', 'upper_limit', *args])
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
    
    def _register_correlation_test(self, name, lower_limit, upper_limit, **kwargs):
        if name in self._correlation_declarations:
            raise Exception(f'Duplicated correlation refid name {name} within module {self.get_name()}!')
        self._set_additional_correlation_attributes(*list(kwargs.keys()))
        self._correlation_declarations[name] = self._correlation_declaration(refid_name=              name, 
                                                                             lower_limit=             lower_limit,
                                                                             upper_limit=             upper_limit,
                                                                             **kwargs
                                                                            )
        self._correlation_results[name] = self._correlation_results_list(declaration=self._correlation_declarations[name])
        return self._correlation_declarations[name]
    def _register_correlation_result(self, refid_name, iter_data, conditions, query=None): # TODO conditions
        if refid_name not in self._correlation_declarations:
            raise Exception(f'Undeclared correlation results: {refid_name}')
        if type(iter_data) == lab_utils.sqlite_data:
            query = (iter_data.sql_query, iter_data.params)
        if type(iter_data) == lab_utils.sqlite_data and iter_data.get_column_names() is not None and len(iter_data.get_column_names()) > 2:
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
                if temperature is 'NULL':
                    temperature = 25
                err=self._error(refid_name,temperature,result)
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
        self._schema_version = 1.3
        self._correlation_declarations = collections.OrderedDict()
        self._correlation_results = collections.OrderedDict()
        with open(results_json, mode='r', encoding='utf-8') as f:
            self.__results = json.load(f)
            f.close()
        # if self.__results['schema_version'] != self._schema_version:
        if self.__results['schema_version'] not in (0.2, 1.0, 1.1, 1.2, 1.3):
            raise ResultsSchemaMismatchException(f'Results file {results_json} written with schema version {self.__results["schema_version"]}, but reader expecting {self._schema_version}.')
        self._init(name=self.__results['test_module'], module=None)
        # print(f'INFO Loading correlation {self.get_name()} record produced on {self.__results["report_date"]} from data collected on {self.__results["collection_date"]}.\n\t({results_json})') #TODO too loud for logs?
        self._set_traceability_info(datetime=self.__results["collection_date"], **self.__results["traceability"])
        # TODO flag json re-output as derivative????
        for test in self.__results['tests']:
            self._register_correlation_test(name=test, **self.__results['tests'][test]['declaration'])
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


if __name__ == '__main__':
    from stowe_eval.stowe_eval_base.modules import refid_importer
    #TODO command line filter/group args like stowe_die_traceability?
    refids_plan = refid_importer.refid_importer()
    try:
        trr = test_results_reload()
    except FileNotFoundError as e:
        print("test_results.json not found in working directory.")
    else:
      print(trr)
      # Copied from jira refid crosscheck
      for refid in trr:
          try:
              spec_lower_limit = refids_plan[refid]['MIN'] if not refid_importer.isnan(refids_plan[refid]['MIN']) else None
              spec_upper_limit = refids_plan[refid]['MAX'] if not refid_importer.isnan(refids_plan[refid]['MAX']) else None
              spec_units = refids_plan[refid]['UNIT'] #if not refid_importer.isnan(refids_plan[refid]['UNIT']) else None
              spec_ate_test = refids_plan[refid]['ATE TEST #'] if not refid_importer.isnan(refids_plan[refid]['ATE TEST #']) else None
              spec_ate_subtest = refids_plan[refid]['ATE SUBTEST #'] if not refid_importer.isnan(refids_plan[refid]['ATE SUBTEST #']) else None
              #todo collect script and multitest unit revisions check here against json????
          except KeyError as e:
              print(f'ERROR REFID {refid} missing from eval plan.')
              continue
          
          result_lower_limit = trr.get_test_declaration(refid).lower_limit
          result_upper_limit = trr.get_test_declaration(refid).upper_limit
          result_units = trr.get_test_declaration(refid).unit
          result_ate_test = trr.get_test_declaration(refid).ATE_test if not refid_importer.isnan(trr.get_test_declaration(refid).ATE_test) else None
          result_ate_subtest = trr.get_test_declaration(refid).ATE_subtest if not refid_importer.isnan(trr.get_test_declaration(refid).ATE_subtest) else None
          if result_lower_limit != spec_lower_limit:
              print(f'WARNING {refid} lower limit mismatches REFID spec. ({result_lower_limit} vs {spec_lower_limit})')
          elif result_upper_limit != spec_upper_limit:
              print(f'WARNING {refid} upper limit mismatches REFID spec. ({result_upper_limit} vs {spec_upper_limit})')
          elif result_units != spec_units:
              print(f'WARNING {refid} units mismatch REFID spec. ({result_units} vs {spec_units})')
          elif result_ate_test != spec_ate_test:
              print(f'WARNING {refid} ATE test mismatch REFID spec. ({result_ate_test} vs {spec_ate_test})')
          elif result_ate_subtest != spec_ate_subtest:
              print(f'WARNING {refid} ATE subtest mismatch REFID spec. ({result_ate_subtest} vs {spec_ate_subtest})')

    try:
        crr = correlation_results_reload()
    except FileNotFoundError as e:
        print("correlation_results.json not found in working directory.")
    else:
        print(crr)
        # Copied from jira refid crosscheck
        for refid in crr:
            try:
                spec_lower_limit = refids_plan[refid]['MIN'] if not refid_importer.isnan(refids_plan[refid]['MIN']) else None
                spec_upper_limit = refids_plan[refid]['MAX'] if not refid_importer.isnan(refids_plan[refid]['MAX']) else None
                spec_units = refids_plan[refid]['UNIT'] #if not refid_importer.isnan(refids_plan[refid]['UNIT']) else None
                spec_ate_test = refids_plan[refid]['ATE TEST #'] if not refid_importer.isnan(refids_plan[refid]['ATE TEST #']) else None
                spec_ate_subtest = refids_plan[refid]['ATE SUBTEST #'] if not refid_importer.isnan(refids_plan[refid]['ATE SUBTEST #']) else None
            except KeyError as e:
                print(f'ERROR REFID {refid} missing from eval plan.')
                continue
            result_lower_limit = crr.get_correlation_declaration(refid).lower_limit
            result_upper_limit = crr.get_correlation_declaration(refid).upper_limit
            result_units = crr.get_correlation_declaration(refid).unit
            result_ate_test = crr.get_correlation_declaration(refid).ATE_test if not refid_importer.isnan(crr.get_correlation_declaration(refid).ATE_test) else None
            result_ate_subtest = crr.get_correlation_declaration(refid).ATE_subtest if not refid_importer.isnan(crr.get_correlation_declaration(refid).ATE_subtest) else None
            if result_lower_limit != spec_lower_limit:
                print(f'WARNING {refid} lower limit mismatches REFID spec. ({f"{result_lower_limit:g}" if result_lower_limit is not None else None} vs {f"{spec_lower_limit:g}" if spec_lower_limit is not None else None})')
            elif result_upper_limit != spec_upper_limit:
                print(f'WARNING {refid} upper limit mismatches REFID spec. ({f"{result_upper_limit:g}" if result_upper_limit is not None else None} vs {f"{spec_upper_limit:g}" if spec_upper_limit is not None else None})')
            elif result_units != spec_units:
                print(f'WARNING {refid} units mismatch REFID spec. ({result_units} vs {spec_units})')
            elif result_ate_test != spec_ate_test:
                print(f'WARNING {refid} ATE test mismatch REFID spec. ({result_ate_test} vs {spec_ate_test})')
            elif result_ate_subtest != spec_ate_subtest:
                print(f'WARNING {refid} ATE subtest mismatch REFID spec. ({result_ate_subtest} vs {spec_ate_subtest})')

            

