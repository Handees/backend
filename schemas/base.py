from core import ma
from core.exc import DataValidationError
from marshmallow import pre_load


def _parse_error(error, data, **kwargs):
    msg = ""
    for k, v in error.messages.items():
        err = v[0]
        if "Missing data" in err:
            msg = f"{k}: Missing data for required field"
        else:
            msg = f"{k}: {error}"
        break
    return msg


class BaseSQLAlchemyAutoSchema(ma.SQLAlchemyAutoSchema):
    def handle_error(self, error, data, **kwargs):
        """Log and raise error when de-serialization fails. """
        message = _parse_error(error, data, **kwargs)
        self.error_messages = message
        raise DataValidationError(msg=message, errors=error.messages, data=data)

    @pre_load
    def remove_skip_values(self, data, many, partial):
        """Treat nulls & empty strings as undefined
        As per these guidelines: https://google.github.io/styleguide/jsoncstyleguide.xml#Empty/Null_Property_Values
        """
        if not data:
            return data

        VALUES_TO_SKIP = ["", None]
        return {k: v for k, v in data.items() if v not in VALUES_TO_SKIP}
