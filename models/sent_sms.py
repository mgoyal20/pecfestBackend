from models.model import db

class SentSMS(db.Model):

	__tablename__ = 'sent_sms'

	id = db.Column(db.Integer, primary_key=True)
	smsId = db.Column(db.String(255), nullable=False)
	mobile = db.Column(db.String(10), nullable=False)
	smsType = db.Column(db.Integer, nullable=False)

	# 1 for pending, 2 for delivered, 3 for rejected
	status = db.Column(db.Integer, nullable=False)