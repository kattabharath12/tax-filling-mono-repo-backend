class W2ParseError(Exception):
    """Raised when a W-2 cannot be parsed"""
    pass

class UnsupportedFileTypeError(Exception):
    """Raised when an unsupported file type is uploaded"""
    pass
