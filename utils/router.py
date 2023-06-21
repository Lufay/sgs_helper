from enum import Enum, auto
from collections.abc import Iterable
from collections import defaultdict

_router = {}

class MatchType:
    FULL_MATCH = 'full_match'
    KEYWORD = 'keyword'
    PREFIX = 'prefix'
    TEST = 'test'


def route(cmd, match_type=MatchType.FULL_MATCH):
    def outer(func):
        global _router
        if isinstance(cmd, (list, tuple)):
            for c in cmd:
                _router.setdefault(match_type, {}).setdefault(c, func)
        else:
            _router.setdefault(match_type, {}).setdefault(cmd, func)
        return func
    return outer


def route_todo(cmd:str, *args, **kwargs):
    for match_type, mapper in _router.items():
        match match_type:
            case MatchType.FULL_MATCH:
                if f := mapper.get(cmd):
                    return f(*args, **kwargs)
            case MatchType.KEYWORD:
                for k, f in mapper.items():
                    if k in cmd:
                        return f(cmd, *args, **kwargs)
            case MatchType.PREFIX:
                for k, f in mapper.items():
                    if cmd.startswith(k):
                        return f(cmd.removeprefix(k), *args, **kwargs)
            case MatchType.TEST:
                for tester, f in mapper.items():
                    t, *ctx = tester(cmd, *args, **kwargs)
                    if t:
                        f(cmd, ctx=ctx, *args, **kwargs)
    raise NotImplementedError(f'{cmd} is not registered')


