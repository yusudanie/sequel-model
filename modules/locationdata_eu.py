# helper functions to use location data for data outside US/north america
# K7MHI Kelly Keeton 2024

import json # pip install json
from geopy.geocoders import Nominatim # pip install geopy
import maidenhead as mh # pip install maidenhead
import requests # pip install requests
import bs4 as bs # pip install beautifulsoup4
import xml.dom.minidom 
from modules.log import *

trap_list_location_eu = ("ukalert", "ukwx", "ukflood")

def get_govUK_alerts():
    try:
        # get UK.gov alerts
        url = 'https://www.gov.uk/alerts'
        response = requests.get(url)
        soup = bs.BeautifulSoup(response.text, 'html.parser')
        # the alerts are in <h2 class="govuk-heading-m" id="alert-status">
        alert = soup.find('h2', class_='govuk-heading-m', id='alert-status')
    except Exception as e:
        logger.warning("Error getting UK alerts: " + str(e))
        return NO_ALERTS
    
    if alert:
        return "🚨" + alert.get_text(strip=True)
    else:
        return NO_ALERTS
    
def get_wxUKgov():
    # get UK weather warnings
    url = 'https://www.metoffice.gov.uk/weather/guides/rss'
    return NO_ALERTS
    
def get_floodUKgov():
    # get UK flood warnings
    url = 'https://environment.data.gov.uk/flood-widgets/rss/feed-England.xml'
    
    return NO_ALERTS