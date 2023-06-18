class DataValidationError(Exception):
    def __init__(self, msg, errors=None, data=None):
        super().__init__(msg, data)
        self.msg = msg
        self.errors = errors
        self.data = data

    def __reduce__(self):
        return (DataValidationError, (self.msg, self.errors, self.data))


class BookingHasContract(Exception):
    pass


class ClientNotConnected(Exception):
    pass


class InvalidBookingTransaction(Exception):
    pass
