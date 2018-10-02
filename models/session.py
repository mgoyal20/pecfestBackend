from models.model import db

class Session(db.Model):

	__tablename__ = 'Session'

	sessionKey = db.Column(db.String(10), primary_key=True)
	userId = db.Column(db.String(10), nullable=False)
