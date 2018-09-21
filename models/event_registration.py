from models.model import db

class EventRegistration(db.Model):

	__tablename__ = 'Registration'

	id = db.Column(db.Integer, primary_key=True)
	eventId = db.Column(db.Integer, db.ForeignKey('Event.eventId'), nullable=False)
	memberId = db.Column(db.String(10), db.ForeignKey('User.pecfestId'), nullable=False)
	leaderId = db.Column(db.String(10), db.ForeignKey('User.pecfestId'), nullable=False)

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__tablename__.columns}
