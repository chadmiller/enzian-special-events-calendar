# coding: UTF-8

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from icalendar import Event, Calendar

import urllib2
import logging
import json
import re

from datetime import date, datetime, timedelta
import time

import icalendar
from BeautifulSoup import BeautifulSoup, NavigableString

from google.appengine.api import memcache

class About(webapp.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(open(__file__).read())

class Statistics(webapp.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(memcache.get_stats()))


def qualified_date(texty, year):
    cal_date = datetime.strptime(texty, "%B %d @ %I:%M %p")
    return cal_date.replace(year=year)


class EventsListingCal(webapp.RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/calendar; charset=utf-8'

        show_all = "-all" if self.request.get("all") else ""
        calendar = memcache.get("enzian-calendar" + show_all)
        if calendar:
            self.response.out.write(calendar)
            return

        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//Enzian Specials by Chad//NONSCML//EN')
        cal.add('X-WR-CALID', 'dc7c97b1-951d-404f-ab20-3abcf10ad038')
        cal.add('X-WR-CALNAME', 'Enzian specials')
        cal.add('X-WR-CALDESC', "Enzian makes calendars only for eyeballs.  Chad ( https://chad.org/ ) makes computers understand them.")
        cal.add('X-WR-TIMEZONE', 'US/Eastern')

        seen = set()
        for fortnights_in_advance in range(4):  # no "month" math in timedelta.
            month = datetime.utcnow().date() + timedelta(days=14*fortnights_in_advance)
            if month.strftime("%Y-%m") in seen:
                continue
            seen.add(month.strftime("%Y-%m"))

            req = urllib2.Request("http://enzian.org/calendar/" + month.strftime("%Y-%m"), None, headers={ 'User-Agent': 'Mozilla/5.0' })
            page = urllib2.urlopen(req).read()
            soup = BeautifulSoup(page, convertEntities=BeautifulSoup.HTML_ENTITIES)

            for item in soup.fetch("div", attrs={"data-tribejson":True}):
                doc = json.loads(item["data-tribejson"])
                tags = set(doc["categoryClasses"].split())

                if u'cat_special-program' not in tags:
                    continue

                if u'tribe-events-category-film-slam' in tags:
                    continue

                event = Event()
                if u'cat_popcorn-flicks-in-the-park' in tags:
                    event.add('summary', "park movie: " + doc["title"])
                else:
                    event.add('summary', "Enzian: " + doc["title"])

                event.add('description', re.sub(u"….*", u"…", doc["excerpt"]).replace("<p>", ""))
                event.add('dtstamp', datetime.now())  # todo: make this the modtime of page

                start = qualified_date(doc["startTime"], month.year)
                end = qualified_date(doc["endTime"], month.year)

                event.add('dtstart', start)
                event.add('dtend', end)
                event["uid"] = doc["eventId"]

                cal.add_component(event)

        self.response.out.write(cal.as_string())

app = webapp.WSGIApplication(
        [
            ('/shows.ics', EventsListingCal),
            ('/showtimes.ics', EventsListingCal),
            ('/', EventsListingCal),
            ('/statistics', Statistics),
            ('/about', About)
        ], debug=True)
