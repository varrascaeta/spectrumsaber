# Standard imports
import inspect
import pickle
import functools


def serialize(output=True, inputs=True):
    def _wrapper(func):
        parse_inputs = inputs
        if inputs is True:
            parse_inputs = list(inspect.signature(func).parameters)
        elif inputs is False:
            parse_inputs = []

        @functools.wraps(func)
        def _dec(**kwargs):
            final_kwargs = {}
            for k, v in kwargs.items():
                if k in parse_inputs:
                    v = pickle.loads(v)
                final_kwargs[k] = v
            result = func(**final_kwargs)
            result = pickle.dumps(result) if output else result
            return result
        return _dec
    return _wrapper


def serialize_model(serializer):
    def _wrapper(func):
        @functools.wraps(func)
        def _dec(**kwargs):
            result = func(**kwargs)
            if result:
                serialized = serializer(result).data
                return serialized
            return result
        return _dec
    return _wrapper
