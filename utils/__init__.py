class classproperty:
    def __init__(self, method_or_cached):
        if callable(method_or_cached):
            self.method = method_or_cached
            self.cached = False
        else:
            self.cached = bool(method_or_cached)
    
    def __call__(self, method):
        self.method = method
        return self
    
    def __set_name__(self, owner, name):
        self.__name__ = name
    
    def __get__(self, ins, owner):
        if not self.cached:
            return self.method(owner)
        if not hasattr(self, '_cache'):
            self._cache = self.method(owner)
        return self._cache
    
    from collections import namedtuple
    property_val = namedtuple('property_val', 'value cached')
    def __set__(self, ins, value):
        if isinstance(value, self.property_val):
            self.cached = bool(value.cached)
            value = value.value
        if callable(value):
            self.method = value
        elif self.cached:
            self._cache = value
        else:
            self.method = lambda c: value

    def __delete__(self, ins):
        if self.cached:
            del self._cache