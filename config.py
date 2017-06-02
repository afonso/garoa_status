#!/usr/bin/env python
# coding=utf-8
import os
from datetime import tzinfo, timedelta, datetime


TOTAL_EVENTS = 10
FOURSQUARE_VENUE_ID = os.environ['FOURSQUARE_VENUE_ID']

FOURSQUARE_SECRET = os.environ['FOURSQUARE_SECRET']
FOURSQUARE_CLIENT_ID = os.environ['FOURSQUARE_CLIENT_ID']
FOURSQUARE_CLIENT_SECRET = os.environ['FOURSQUARE_CLIENT_SECRET']

FIREBASE_SECRET = os.environ['FIREBASE_SECRET']
FIREBASE_URL = os.environ['FIREBASE_URL']
FIREBASE_JSON = os.environ['FIREBASE_JSON']
FIREBASE_TIMESTAMPJSON = os.environ['FIREBASE_TIMESTAMPJSON']

ARDUINO_TOKEN = os.environ['ARDUINO_TOKEN']

JSON_STATUS = {
	"api":"0.12",
	"space":"Garoa Hacker Clube",
	"url":"https://garoa.net.br",
	"address":"Rua Costa Carvalho, 567, Fundos - Pinheiros - 05429-130 - São Paulo/SP - Brasil",
	"contact": {
		"phone": "+551136620571",
		"twitter": "garoahc",
		"foursquare": FOURSQUARE_VENUE_ID,
		"ml":"cs@garoa.net.br",
		#"keymaster": "+551112345678 (nome)",
	},
	"status": "open for public",
	"logo":"https://garoahc.appspot.com/static/img/logo.png",
	"icon":{
		"open":"https://garoahc.appspot.com/static/img/icon_open.png",
		"closed":"https://garoahc.appspot.com/static/img/icon_closed.png"
	},
	"open":False,
	"lastchange": 1298244863,
	"events":[],
	"lon":-46.69918,
	"lat":-23.564968
}

MAC_SPREADSHEET_STR = os.environ['MAC_SPREADSHEET_STR']

JSON_MACS = {
	"unknown":0,
	"known":{},
	#"known":{
	  #"Lechuga": 123456789,
	  #"name": timestamp
	#},
	"lastchange": 1298244863
}
