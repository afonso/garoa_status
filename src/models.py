from google.appengine.ext import db


class Log(db.Model):
	open_in = db.DateTimeProperty(auto_now_add=True)
	closed_in = db.DateTimeProperty()
	closed = db.BooleanProperty(default=False)

class Event(db.Model):
	name = db.StringProperty(required=True)
	type = db.StringProperty(required=True, choices=["check-in", "check-out", "door"], default="check-in")
	t = db.DateTimeProperty(auto_now_add=True)
	extra = db.StringProperty()
