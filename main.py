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
from google.appengine.ext.webapp import util
from src.controls import *
from src.models import *


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
