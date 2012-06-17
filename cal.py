
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from icalendar import Event, Calendar

import urllib2
import logging
try:
    from django.utils import simplejson as json
except ImportError:
    logging.exception("no django utils simplejson")
    import json

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


def data_to_event(genus, title, d, link):
    event = Event()
    if "in the park" in genus.lower():
        event.add('summary', "park movie: " + title)
    else:
        event.add('summary', "Enzian: " + title)

    event.add('description', genus)
    event.add('dtstamp', datetime.now())  # todo: make this the modtime of page

    if type(d) == datetime:
        event.add('dtstart', d)
    else:
        event.add('dtstart;value=date', icalendar.vDate(d).ical())

    if type(d) == datetime:
        event.add('dtend', d + timedelta(minutes=120))
    else:
        event.add('dtend;value=date', icalendar.vDate(d).ical())
    event["uid"] = link
    return event
    

class EventsListingCal(webapp.RequestHandler):

    def __init__(self):
        super(EventsListingCal, self).__init__()


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
        cal.add('X-WR-CALDESC', "Enzian makes calendars only for eyeballs.  Chad ( http://web.chad.org/ ) makes computers understand them.")
        cal.add('X-WR-TIMEZONE', 'US/Eastern')
        page = urllib2.urlopen("http://www.enzian.org/film/whats_playing/").read()
        soup = BeautifulSoup(page, convertEntities=BeautifulSoup.HTML_ENTITIES)

        for summary in soup.fetch("ul", attrs={"class":"movieSummary"}):
            for item in summary.fetch("li"):
                genus, title, t_desc, link = item.h3.contents[0], item.h4.contents[0], item.h5.contents[0], item.a["href"]
                t_desc = t_desc.replace("th,", ",").replace("rd,", ",").replace("nd,", ",").replace("st,", ",")

                if not show_all and genus in set(("Feature Film", "Ballet on the Big Screen", "FilmSlam", "Opera on the Big Screen")):
                    continue

                if genus not in ("Special Programs", "Cult Classics", "Popcorn Flicks in the Park", "Wednesday Night Pitcher Show", "Saturday Matinee Classics", "KidFest"):
                    logging.info("including questionable %r", genus)

                now = datetime.now()
                try:
                    t = datetime.strptime(t_desc, "%B %d, %I:%M%p").replace(now.year)
                except ValueError:
                    logging.warn("bad date %r", t_desc)
                    continue
                if now > (t + timedelta(days=7)):
                    t = t.replace(now.year + 1)
        
                e = data_to_event(genus, title, t, link)
                if e:
                    cal.add_component(e)

        self.response.out.write(cal.as_string())
        for retry in range(10):
            if not memcache.add("enzian-calendar" + show_all, cal.as_string(), 60*60*4):
                logging.warn("Failed to add data %r to Memcache.", "enzian-calendar-" + show_all)
                time.sleep(0.1)
            else:
                break

        

application = webapp.WSGIApplication(
        [
            ('/shows.ics', EventsListingCal),
            ('/showtimes.ics', EventsListingCal),
            ('/', EventsListingCal),
            ('/statistics', Statistics),
            ('/about', About)
        ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
