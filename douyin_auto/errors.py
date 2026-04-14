# Custom exceptions for douyin-auto


class DouyinError(Exception):
    """Base exception for douyin-auto"""
    pass


class WindowNotFoundError(DouyinError):
    """Raised when Douyin window is not found"""
    pass


class ControlNotFoundError(DouyinError):
    """Raised when a UI control cannot be found"""
    pass


class OperationFailedError(DouyinError):
    """Raised when an operation fails"""
    pass


class ElementNotFoundError(DouyinError):
    """Raised when an element cannot be found"""
    pass
