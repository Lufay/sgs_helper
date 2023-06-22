from enum import Enum, auto
import re

class MatchType(Enum):
    # ctx: []
    FULL_MATCH = (auto(), lambda m, c: (m.get(c),))
    # ctx: [cmd_without_prefix]
    PREFIX = (auto(), lambda m, c: ((kf := next((k, m[k]) for k in m if c.startswith(k)))[1],
                                     c.removeprefix(kf[0])))
    # ctx: []
    KEYWORD = (auto(), lambda m, c: (next(m[k] for k in m if k in c),))
    # ctx: [match_obj]
    REGEX = (auto(), lambda m, c: (next(m[k] for k in m if (ma := re.search(k, c))), ma))
    # ctx: tester_ret[1:]
    TEST = (auto(), lambda m, c: (next(m[t] for t in m if (bc := t(c))[0]), *bc[1:]))

    def __init__(self, value, finder, cont_conv=None):
        self._value_ = value
        self.finder = finder

    def process(self, mapper, cmd, *args, **kwargs):
        try:
            f, *ctx = self.finder(mapper, cmd)
            return (True, f(cmd, ctx, *args, **kwargs)) if f else (False, None)
        except StopIteration:
            return (False, None)


_router = {e:{} for e in MatchType}

def route(cmd, match_type=MatchType.FULL_MATCH):
    def outer(func):
        global _router
        if isinstance(cmd, (list, tuple)):
            for c in cmd:
                _router[match_type].setdefault(c, func)
        else:
            _router[match_type].setdefault(cmd, func)
        return func
    return outer


def route_todo(cmd:str, *args, **kwargs):
    for mt in MatchType:
        b, res = mt.process(_router[mt], cmd, *args, **kwargs)
        if b:
            return res
    raise NotImplementedError(f'{cmd} is not registered')


