from core import db
from .base import TimestampMixin


class SignInAttempts(TimestampMixin, db.Model):
    __tablename__ = "signin_attempts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.String(50),
        db.ForeignKey("user.user_id")
    )

    user = db.relationship(
        "User",
        back_populates="signin_attempts",
        foreign_keys=[user_id]
    )

    ip_address = db.Column(db.String(45))
    device_uuid = db.Column(db.String(128))
    device_model = db.Column(db.String(128))
    device_os = db.Column(db.String(50))
    estimated_location = db.Column(db.JSON)

   