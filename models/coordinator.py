from models.model import db

class Coordinator(db.Model):

	__tablename__ = 'Coordinator'

	userId = db.Column(db.String(10), db.ForeignKey('User.pecfestId'), primary_key=True)
	password = db.Column(db.String(10), nullable=False)
	level = db.Column(db.String(10), nullable=False)

	def __str__(self):
		return "[" + self.userId + "] " + self.level
