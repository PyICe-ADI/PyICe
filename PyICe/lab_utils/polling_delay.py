import time, datetime

class polling_delay(object):
    '''poll for test condition iteratively before unblocking'''
    def __init__(self, dly_fn=None, time_readback_fn=None, except_on_timeout=True, timeout_str_prefix='*Error* '):
        '''
        '''
        if dly_fn is None:
            self.dly_function = lambda dly: time.sleep(dly)
        else:
            self.dly_function = dly_fn
        if time_readback_fn is None and dly_fn is None:
            self.time_readback_fn = lambda: time.time()
        elif time_readback_fn is None:
            self.time_readback_fn = lambda: self.accumulated_dly
        else:
            self.time_readback_fn = time_readback_fn

        self.except_on_timeout = except_on_timeout
        self.timeout_str_prefix = timeout_str_prefix

        # Fill status variables with something
        self._begin()
        self._end(success=False)
        self._continue_condition = None
    def _begin(self):
        self._accumulated_dly = 0
        self._iterations = 0
        self._initial_time = self.time_readback_fn()
        self._success = None
        self._last_val = None
    def _end(self, success):
        self._success = success
        self._final_time = self.time_readback_fn()
    def _wait_for(self, poll_interval, timeout, test_initial, test_fn):
        self._begin()
        if test_initial:
            test_pass = test_fn()
        else:
            test_pass = False
        while(timeout is None or self.time_readback_fn() < self._initial_time+timeout):
            self._accumulated_dly += poll_interval #wait time, not clk time
            self._iterations += 1
            self.dly_function(poll_interval)
            if test_fn():
                self._end(success=True)
                break
        else:
            #timeout
            err_str = f'{self.timeout_str_prefix} polling delay timeout at time {self.time_readback_fn()} after {timeout} timout.'
            self._end(success=False)
            if self.except_on_timeout:
                raise Exception(err_str) #todo specific exception class?
            else:
                print(err_str)
        return self._success
    def wait_for_exact(self, poll_fn, poll_interval, expect, timeout=None, test_initial=True):
        self._continue_condition = expect
        def _test(expect=expect, poll_fn=poll_fn):
            # closure
            t_val = poll_fn()
            self._last_val = t_val
            if t_val == expect:
                test_pass = True
            else:
                test_pass = False
            return test_pass
        return self._wait_for(poll_interval=poll_interval, timeout=timeout, test_initial=test_initial, test_fn=_test)
    def wait_for_limit(self, poll_fn, poll_interval, min=None, max=None, timeout=None, test_initial=True):
        self._continue_condition = (min, max)
        def _test(min=min, max=max, poll_fn=poll_fn):
            # closure
            t_val = poll_fn()
            self._last_val = t_val
            assert min is not None or max is not None, "Must specify at least one of [min,max] test limits"
            test_pass = True
            if min is not None and t_val < min:
                test_pass = False
            if max is not None and t_val > max:
                test_pass = False
            return test_pass
        return self._wait_for(poll_interval=poll_interval, timeout=timeout, test_initial=test_initial, test_fn=_test)
    def get_previous_outcome(self):
        return {'accumulated_delay': self._accumulated_dly,
                'iterations': self._iterations,
                'initial_time': self._initial_time,
                'final_time': self._final_time,
                'last_value': self._last_val,
                'continue_condition': self._continue_condition,
                'success': self._success,
                }


def test():
    import random
    from PyICe.lab_utils.polling_delay import polling_delay
    
    def thinking_of_a_number():
        resp = random.randrange(100)
        print(f'testing {resp}')
        return resp
    
    class virt_time:
        def __init__(self):
            self._time = 0
        def delay(self, dly_time):
            print(f'waiting {dly_time} at time {self._time}')
            self._time += dly_time
        def get_time(self):
            return self._time
    vt = virt_time()
        
    waiter = polling_delay(timeout_str_prefix='YoYoYo!: ', except_on_timeout=False)
    print(waiter.get_previous_outcome())
    
    waiter.wait_for_exact(poll_fn=thinking_of_a_number, poll_interval=0.1, expect=42, timeout=500, test_initial=True)
    print(waiter.get_previous_outcome())
    waiter.wait_for_limit(poll_fn=thinking_of_a_number, poll_interval=0.2, min=30, max=40, test_initial=False)
    print(waiter.get_previous_outcome())
    waiter.wait_for_limit(poll_fn=thinking_of_a_number, poll_interval=0.2, min=-10, max=-1, test_initial=False, timeout=3)
    print(waiter.get_previous_outcome())
    
    
    virt_waiter = polling_delay(dly_fn=vt.delay, time_readback_fn=vt.get_time)
    
    virt_waiter.wait_for_exact(poll_fn=lambda: random.randrange(10), poll_interval=5e-6, expect=7, timeout=1e-3, test_initial=False)
    print(virt_waiter.get_previous_outcome())
    virt_waiter.wait_for_limit(poll_fn=lambda: random.randrange(30), poll_interval=6e-6, min=2, max=12, test_initial=True)
    print(virt_waiter.get_previous_outcome())
    virt_waiter.wait_for_limit(poll_fn=lambda: random.randrange(30), poll_interval=6e-6, min=31, max=32, timeout=10e-6, test_initial=True) #impossible
    print(virt_waiter.get_previous_outcome()) 
    # virt_waiter.except_on_timeout = True
    # virt_waiter.wait_for_limit(poll_fn=lambda: random.randrange(30), poll_interval=6e-6, min=31, max=32, timeout=10e-6, test_initial=True) #crash
    # print(virt_waiter.get_previous_outcome())
    
