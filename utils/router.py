from enum import Enum, auto
import re

class MatchType(Enum):
    '''路由匹配类型枚举
    finder 是一个简单函数
        参数m 是注册为该路由类型的映射集
        参数c 是用户的请求命令行
        逻辑是根据c 如何从m 中找到target函数(第一返回值)
        后续返回值是ctx, 表示在查找过程中提供的额外信息, 可以提供给target函数使用
    '''
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
        '''找到target函数则第一返回值为true, 否则为false
        第二返回值即是调用target函数的返回值
        '''
        try:
            f, *ctx = self.finder(mapper, cmd)
            return (True, f(cmd, ctx, *args, **kwargs)) if f else (False, None)
        except StopIteration:
            return (False, None)


_router = {e:{} for e in MatchType}

def route(cmd, match_type=MatchType.FULL_MATCH):
    '''路由注册的装饰器
    '''
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
    '''根据命令行进行路由到target 函数进行处理
    '''
    for mt in MatchType:
        b, res = mt.process(_router[mt], cmd, *args, **kwargs)
        if b:
            return res
    raise NotImplementedError(f'{cmd} is not registered')


