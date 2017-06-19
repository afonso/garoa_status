#!/usr/bin/env python
# coding=utf-8

import time
import json
import logging
import random
import config
from datetime import datetime

import cStringIO
import urllib2

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.api import datastore, memcache, urlfetch


def get_data():
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

				else:
					logging.info("REFRESH OPEN")
				self.response.out.write("<o1>")

			elif acao == "close":
				if not last_log is None and not last_log.closed:
					logging.info("NEW CLOSE")
					last_log.closed = True
					last_log.closed_in = datetime.now()
					last_log.put()
				else:
					logging.info("REFRESH OPEN")
				self.response.out.write("<o1>")



			logging.info("publishing firebase...")

			opener = urllib2.build_opener(urllib2.HTTPHandler)
			request = urllib2.Request(config.FIREBASE_URL % ("",
				config.FIREBASE_SECRET), data=config.FIREBASE_JSON % (acao))

			request.add_header('Content-Type', 'your/contenttype')
			request.get_method = lambda: 'PUT'
			url = opener.open(request)

			memcache.delete("log")
			memcache.add("log", last_log)
			memcache.delete("status")

		elif objeto == "event":
			#TODO: implementar registro de outros eventos
			self.response.out.write("<e0>")

		else:
			self.response.out.write("<x0>")

#TODO: Change to POST
class UpdateMacsHandler(webapp.RequestHandler):
	def get(self, objeto, macs_str=None, token=None):
		if token != config.ARDUINO_TOKEN:
			self.response.out.write("<e9>")
			return True

		if objeto == "macs":
			logging.info("UPDATE MACS")

			macs_list=macs_str.split('_')
			macs_json = get_macs()

			logging.info("Getting Spreadsheet information")
			MAC_SPREADSHEET_STR = config.MAC_SPREADSHEET_STR
			result = urlfetch.fetch(MAC_SPREADSHEET_STR)
			if result.status_code == 200:
				buf = result.content
			else:
				raise Exception('Error getting Spreadsheet information')

			lines = buf.split("\n").pop(0)
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

			try:
				del names["IGNORE"]
			except:
				logging.info("No ignore to remove")

			macs_json = {
				"unknown": unknown,
				"known": names,
				"lastchange": int(time.mktime(datetime.now().timetuple()))
			}

			memcache.delete("macs")
			memcache.add("macs", macs_json)
		else:
			self.response.out.write("<x0>")

class MainHandler(webapp.RequestHandler):
	def get(self):
		template_values = {}
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
