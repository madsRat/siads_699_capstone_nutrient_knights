import time
from functools import wraps

def timeit(func):
    @wraps(func)
    def time_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Time: {total_time:.3f} s, Function: {func.__name__}')
        return result
    return time_wrapper