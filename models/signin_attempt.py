from core import db
from .base import TimestampMixin


class SignInAttempts(TimestampMixin, db.Model):

    __tablename__= "signin_attempts"

    id = db.Column(
        db.Integer, 
        primary_key=True
        autoincrement=True
        )
    
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id"), 
        nullable=False
        )
    
    created_at = db.Column(
        db.DateTime, 
        nullable=False, 
        default=db.func.current_timestamp()
        )
    
    device_os = db.Column(
        db.String(50), 
        nullable=True
        )
    
    ip_address = db.Column(
        db.String(45), 
        nullable=True
        )
    
    user = db.relationship(
        "User", 
        back_populates="signin_attempts")
    
    estimated_location = db.Column(
        db.JSON, 
        nullable=True
        )
