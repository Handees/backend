from models.signin_attempt import SignInAttempts
from .base import BaseSQLAlchemyAutoSchema

class SignInAttemptSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = SignInAttempts
        include_fk = True
        include_relationships = True
        load_instance = True