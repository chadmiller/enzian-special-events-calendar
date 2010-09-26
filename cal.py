
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from icalendar import Event, Calendar

import urllib
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


def data_to_event(title, genus, d, link):
    event = Event()
    event.add('summary', title)
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
        self.response.headers['Content-Type'] = 'text/calendar'

        calendar = memcache.get("enzian-calendar")
        if calendar:
            self.response.out.write(calendar)
            return

        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//Enzian Specials by Chad//NONSCML//EN')
        cal.add('X-WR-CALID', 'dc7c97b1-951d-404f-ab20-3abcf10ad038')
        cal.add('X-WR-CALNAME', 'Enzian specials by Chad')
        cal.add('X-WR-CALDESC', "Enzian doesn't make calendars only for meat puppets.  Chad ( http://web.chad.org/ ) makes computers understand them.  Enjoy!")
        cal.add('X-WR-TIMEZONE', 'US/Eastern')
        page = urllib.urlopen("http://www.enzian.org/film/whats_playing/").read()
        soup = BeautifulSoup(page)

        for summary in soup.fetch("ul", attrs={"class":"movieSummary"}):
            for item in summary.fetch("li"):
                genus, title, t_desc, link = item.h3.contents[0], item.h4.contents[0], item.h5.contents[0], item.a["href"]
                t_desc = t_desc.replace("th,", ",").replace("rd,", ",").replace("nd,", ",").replace("st,", ",")
                if genus not in ("Special Programs", "Cult Classics", "Popcorn Flicks in the Park"): continue
                now = datetime.now()
                t = datetime.strptime(t_desc, "%B %d, %I:%M%p").replace(now.year)
                if now > (t + timedelta(days=7)):
                    t = t.replace(now.year + 1)
        
                e = data_to_event(genus, title, t, link)
                if e:
                    cal.add_component(e)

        self.response.out.write(cal.as_string())
        for retry in range(3):
            if not memcache.add("enzian-calendar", cal.as_string(), 60*60*1):
                logging.warn("Failed to add data to Memcache.")
                time.sleep(0.5)
            else:
                break

        

application = webapp.WSGIApplication(
        [
            ('/shows.ics', EventsListingCal),
            ('/', EventsListingCal),
            ('/statistics', Statistics),
            ('/about', About)
        ], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
