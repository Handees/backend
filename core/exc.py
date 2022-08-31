class DataValidationError(Exception):
    def __init__(self, msg, errors, data=None):
        super().__init__(msg, errors, data)
        self.msg = msg
        self.errors = errors
        self.data = data

    def __reduce__(self):
        return (DataValidationError, (self.msg, self.errors, self.data))