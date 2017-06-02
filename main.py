#!/usr/bin/env python
# coding=utf-8

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db

from google.appengine.api import datastore
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

import time
#import simplejson as json
import json
import logging
import random
import config
from datetime import datetime

from google.appengine.api import urlfetch
import cStringIO

import urllib2

class Log(db.Model):
	open_in = db.DateTimeProperty(auto_now_add=True)
	closed_in = db.DateTimeProperty()
	closed = db.BooleanProperty(default=False)

class Event(db.Model):
	name = db.StringProperty(required=True)
	type = db.StringProperty(required=True, choices=["check-in", "check-out", "door"], default="check-in")
	t = db.DateTimeProperty(auto_now_add=True)
	extra = db.StringProperty()
	
	#name (string, mandatory) – name or nickname of person or object associated with this event;
	#type (string, mandatory) – ‘check-in’ or ‘check-out’ (other values may be specified, but receivers of the object are not obligated to be able to understand these)
	#t (long int, mandatory) – time since the epoch for this event
	#extra (string, optional) – additional information
	
#class Macs(db.Model):
    #known = db.IntegerProperty(required=True, default=0)
    #unknown = db.IntegerProperty(required=True, default=0)
	#names = db.StringListProperty(required=False)
    #lastchange = db.DateTimeProperty(auto_now_add=True)

"""

	/					> raiz
	/rest/status/open	> muda status para aberto
	/rest/status/close	> muda status para fechado 
	/rest/event/		> POST: gera novo evento (fora checkin/open/close)
	
	/foursquare/checkin	> push do foursquare da venue (inclui registro em events)
	


	usar memcache com ID do lastStatus, principalmente se ele estiver aberto
	se o status estiver fechado e receber outro closed, nao faz nada
	se o status estiver aberto e receber closed, fecha e atualiza
	
	se o status estiver aberto e receber outro open, nao faz nada
	se o status estiver fechado e receber open, criar novo registro e atualizar
	

"""


# toda vez que gerar evento limpar cache

def get_data():
	# verificar memcache
	# listar ultimos eventos
	
	status = memcache.get("status")
	if status is None:
		status = config.JSON_STATUS
		status["lastchange"] = int(time.mktime(datetime.now().timetuple()))
		
		last_log = memcache.get("log")
		if last_log is None:
			last_log = Log.all().order("-open_in").get()
		
		if not last_log is None:
			status["open"] = not last_log.closed
		
		events = []
		for event in Event.all().order("-t").fetch(config.TOTAL_EVENTS):
			events.append({
				"name": event.name,
				"type": event.type,
				"t": int(time.mktime(event.t.timetuple())),
				"extra": event.extra
			})
		
		events.reverse()
		status["events"] = events
		memcache.add("status", status)
		
	return status

def get_macs():
	# verificar memcache	
	macs_json = memcache.get("macs")
	if macs_json is None: #this is the first update
		macs_json = config.JSON_MACS
		macs_json["lastchange"] = int(time.mktime(datetime.now().timetuple()))
		
	elif (int(time.mktime(datetime.now().timetuple())) - macs_json["lastchange"] > (15*60)): #last update is older than 15min
		macs_json["known"]={}
		macs_json["unknown"] = 0
	else:
		names=macs_json["known"]
		clear_old_macs(names)
		macs_json["known"] = names

	memcache.delete("macs")
	memcache.add("macs", macs_json)
		
	return macs_json

def clear_old_macs(names):
	logging.info("Clear Old Macs")
	
	clone_dict = names.copy()
	for nome, timestamp in clone_dict.iteritems():
		if(int(time.mktime(datetime.now().timetuple())) - timestamp > (30*60)): #MAC update older than 30min
			del names[nome]


class RestHandler(webapp.RequestHandler):
	def get(self, objeto, acao=None, token=None):
		if token != config.ARDUINO_TOKEN:
			self.response.out.write("<e9>")
			return
		
		if objeto == "status":
			last_log = memcache.get("log")
			if last_log is None:
				last_log = Log.all().order("-open_in").get()
			
			if acao == "open":
				if last_log is None or last_log.closed:
					logging.info("NEW OPEN")
					last_log = Log()
					last_log.put()
					#memcache.delete("log")
					#memcache.add("log", last_log)
					#memcache.delete("status")
					#self.response.out.write("<o1>")
				else:
					logging.info("REFRESH OPEN")
				self.response.out.write("<o1>")
				
			elif acao == "close":
				if not last_log is None and not last_log.closed:
					logging.info("NEW CLOSE")
					last_log.closed = True
					last_log.closed_in = datetime.now()
					last_log.put()
					#memcache.delete("log")
					#memcache.add("log", last_log)
					#memcache.delete("status")
					#self.response.out.write("<o1>")
				else:
					logging.info("REFRESH OPEN")
				self.response.out.write("<o1>")
			


			logging.info("publishing firebase...")
			#XXX config.FIREBASE_SECRET


			opener = urllib2.build_opener(urllib2.HTTPHandler)
			request = urllib2.Request(config.FIREBASE_URL % ("", config.FIREBASE_SECRET), data=config.FIREBASE_JSON % (acao))
			request.add_header('Content-Type', 'your/contenttype')
			request.get_method = lambda: 'PUT'
			url = opener.open(request)			

			# logging.info("publishing pubnub...")
			# info = pubnub.publish({
			# 	'channel' : 'garoa_status_api',
			# 	'message' : {
			# 		'open': not last_log.closed,
			# 		'event': 'status'
			# 	}
			# })
			# logging.info(info)
				
			memcache.delete("log")
			memcache.add("log", last_log)
			memcache.delete("status")
				
		elif objeto == "event":
			#TODO: implementar registro de outros eventos
			self.response.out.write("<e0>")
			
		else:
			self.response.out.write("<x0>")

#http://localhost:8080/rest/macs/1234_4321_1111/1234
#TODO: Change to POST
class UpdateMacsHandler(webapp.RequestHandler):
	#def post(self):
		#self.request.get("macs")
		
	def get(self, objeto, macs_str=None, token=None):
		
		if token != config.ARDUINO_TOKEN:
			self.response.out.write("<e9>")
			return

		if objeto == "macs":
			logging.info("UPDATE MACS")

			macs_list=macs_str.split('_')
			macs_json = get_macs()
			
			#Get List from google Drive
			logging.info("Getting Spreadsheet information")
			MAC_SPREADSHEET_STR = config.MAC_SPREADSHEET_STR
			result = urlfetch.fetch(MAC_SPREADSHEET_STR)
			if result.status_code == 200:
				buf = result.content
			else:
				raise Exception('Error getting Spreadsheet information')
			
			#Transform CSV to dict
			lines = buf.split("\n")
			lines.pop(0)
			CADASTRO_MACS = {}

			for line in lines:
			    item = line.split(",")
			    CADASTRO_MACS[item[0].upper()] = item[1]
			
			unknown=0;
			names=macs_json["known"]

			for atual in macs_list:
				if atual.upper() in CADASTRO_MACS:
					names[CADASTRO_MACS[atual.upper()]]= int(time.mktime(datetime.now().timetuple()))
				else:
					unknown+=1

			self.response.out.write("<o1>")
			
			#Remove IGNORE
			try:
				del names["IGNORE"]
			except:
				logging.info("No ignore to remove")
			
			macs_json["unknown"] = unknown
			macs_json["known"] = names
			macs_json["lastchange"] = int(time.mktime(datetime.now().timetuple()))
			memcache.delete("macs")
			memcache.add("macs", macs_json)
		else:
			self.response.out.write("<x0>")

class MainHandler(webapp.RequestHandler):
	def get(self):
		#if self.request.get("force"):
		#	memcache.delete("status")
		
		#self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		#self.response.headers.add_header("Cache-Control", "no-cache")
		#self.response.out.write(json.dumps(get_data()))
		
		template_values = {
			#"channel_token": channel.create_channel("TOKEN"),
		}
		self.response.out.write(template.render("./template/geral.html", template_values))
		
class StatusHandler(webapp.RequestHandler):
	def get(self):
		if self.request.get("force"):
			memcache.delete("status")
		
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.headers.add_header("Cache-Control", "no-cache")
		self.response.out.write(json.dumps(get_data()))

class MacsHandler(webapp.RequestHandler):
	def get(self):
		
		self.response.headers['Content-Type'] = "application/json"
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.headers.add_header("Cache-Control", "no-cache")
		self.response.out.write(json.dumps(get_macs()))

class ImageHandler(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = "image/png"
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.headers.add_header("Cache-Control", "no-cache")
		
		json_status = get_data()
		
		image = json_status["open"] and json_status["icon"]["open"] or json_status["icon"]["closed"]
		self.redirect(image)
	
class FoursquareHandler(webapp.RequestHandler):
	def post(self):
		if self.request.get("secret") != config.FOURSQUARE_SECRET:
			self.response.out.write("INVALID SECRET")
			logging.warning("INVALID SECRET: %s." % self.request.get("secret"))
			return
		
		status = get_data()
    	
		retorno = json.loads(self.request.get("checkin"))
		logging.info(json.dumps(retorno))
		
		if retorno["venue"]["id"] != config.FOURSQUARE_VENUE_ID:
			self.response.out.write("INVALID VENUE")
			logging.warning("INVALID VENUE %s." % retorno["venue"]["id"])
			return
		
		event = Event(name = "%s %s" % (retorno["user"]["firstName"], retorno["user"]["lastName"]),
			extra = retorno["user"]["photo"]
		)
		event.put()
		memcache.delete("status")
		
		# incluir apenas o checkin
		checkins = []
		checkins.append({
			"name": event.name,
			"type": event.type,
			"t": int(time.mktime(event.t.timetuple())),
			"extra": event.extra
		})



		opener = urllib2.build_opener(urllib2.HTTPHandler)
		request = urllib2.Request(config.FIREBASE_URL % ("last_update", config.FIREBASE_SECRET), data=config.FIREBASE_TIMESTAMPJSON)
		request.add_header('Content-Type', 'your/contenttype')
		request.get_method = lambda: 'PUT'
		url = opener.open(request)			

		self.response.out.write("OK")

def main():
	handlers = [
		("/foursquare/push", FoursquareHandler),
		("/rest/(status)/(open|close)/([\w\d]*)", RestHandler),
		("/rest/(macs)/([\w\d]*)/([\w\d]*)", UpdateMacsHandler),
		("/status", StatusHandler),
		("/macs", MacsHandler),
		("/status.png", ImageHandler),
		("/view", MainHandler),
		("/", MainHandler)
	]
	application = webapp.WSGIApplication(handlers, debug=True)
	util.run_wsgi_app(application)
	
if __name__ == '__main__':
	main()
