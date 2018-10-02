from models.model import db

class OTPs(db.Model):

	__tablename__ = 'OTPs'

	mobile = db.Column(db.String(10), primary_key=True)
	otp = db.Column(db.String(6), nullable=False)

	def __repr__(self):
		return 'ID: <' + self.mobile + ':' + self.otp + '>'

	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__tablename__.columns}


