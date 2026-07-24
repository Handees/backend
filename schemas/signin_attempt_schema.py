from models.sigin_attempt import SignInAttempt
from .base import BaseSQLAlchemyAutoSchema

class SignInAttemptSchema(BaseSQLAlchemyAutoSchema):
    class Meta:
        model = SignInAttempt
        include_fk = True
        include_relationships = True
        load_instance = True