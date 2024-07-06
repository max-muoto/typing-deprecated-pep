from typing_extensions import deprecated


class MyClass:
    @deprecated("This method is deprecated. Use another method instead.")
    def deprecated_method(self):
        pass


class MyClass2(MyClass):
    @deprecated("This method is deprecated. Use another method instead.")
    def deprecated_method(self):
        pass
