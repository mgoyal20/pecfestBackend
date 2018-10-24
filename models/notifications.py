from models.model import db


class Notifications(db.Model):
    __tablename__ = 'Notifications'

    token = db.Column(db.String(50), primary_key=True)
