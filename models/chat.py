from core import db

from .base import TimestampMixin, BaseModelPR


class Chat(TimestampMixin, db.Model):
    id = db.Column(db.String, primary_key=True, unique=True)
    booking_id = db.Column(db.String, db.ForeignKey('booking.booking_id'))
    closed_at = db.Column(db.DateTime)
    chats = db.relationship('ChatMessage', backref='chat')


class ChatMessage(BaseModelPR, TimestampMixin, db.Model):
    message_id = db.Column(db.String)
    content = db.Column(db.Text, nullable=False)
    chat_id = db.Column(db.String, db.ForeignKey('chat.id'), index=True)
    sent_by = db.Column(db.String, db.ForeignKey('user.user_id'), index=True)
    is_flagged = db.Column(db.Boolean)
