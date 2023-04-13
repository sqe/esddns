"""ESDDNS Web-Service with Flask
Flask application launches with ESDDNS to heat up dynamic cache, initiates
background daemon thread as scheduled daemon to manage the dynamic cache, interval is 
configured in configuration file.
    
How It Works:

    Initialize current_state() and g_cached_state() with Flask application context,
    i.e. when Flask application starts. To address the cold start scenario where user
    would have waited for the first request response to populate the current 
    ESDDNS state. 
    
    Scheduling a daemon to run ESDDNS in background also takes place right after 
    initial current_state() call in Flask application context.  

    FLASK application context is only used to pre-heat the cache for cold start, and 
    to render the state populated as dynamic global cached state.

    The global dynamic cached state gets refreshed each time daemon exuctes (runs 
    the current_state function). 

    Daemon is scheduled `interval` retrieved from configs and will run forever until
    service is forced to stop.    

Returns:

    - Dictionary: ESDDNS State 
        - Syncrhonized Union of managed WAN IP and DNS A Record states

    - endpoint: `http://localhost:port/`
        - HTML template with current ESDDNS state for example
            - Current ESDDNS State:
                - State Poll Date: 2023-04-02 20:12:00
                - WAN IP State: 
                    - Is IP address usable?: True
                    - Your WAN IPv4 address: xx.xx.xx.xx
                - DNS Record State: 
                    - Is DNS Record in sync?: True
                    - Recordset Data:
                        - Record Set Name: @
                        - Record Set Type: A
                        - Record Set Time To Live: 300
                        - Record Set Values: ['xx.xx.xx.xx']
                        - Record Set HREF: 
                            https://api.gandi.net/v5/livedns/domains/your_domain.com/records/%40/A

    - endpoint: `http://localhost:port/raw`
        - Syncrhonized union of managed WAN IP and DNS A Record states as RAW json 
"""

from configparser import ConfigParser
from esddns.esddns import ESDDNS as ESDDNSC 
from flask import Flask, render_template
from api.logs import logger as logger_wrapper
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

config = ConfigParser()
scheduled_daemon = BackgroundScheduler(daemon=True)
logger = logger_wrapper()
config.read('dns.ini')
esddns_config = dict(config["ESDDNS"])
g_cached_state = {}
date_format = "%Y-%m-%d %H:%M:%S"
cur_state = ESDDNSC()

def timestamp():
    """Stored date time stamp

    Returns:
        class: datetime.datetime
        Formatted with "%Y-%m-%d %H:%M:%S"
    """
    return datetime.now()

poll_timestamp = {"poll_date": {}}
poll_timestamp["poll_date"] = timestamp().strftime(date_format)

def global_cache():
    """Stored dynamic global cached state

    Returns:
        dict: `g_cached_state`
    """
    global g_cached_state
    return g_cached_state

def current_state():
    """
    Reads and fills `g_cached_state`, current union of WAN IP and DNS Record states 
    with timestamp is stored as `state_cache`.

        - During initial start `g_cached_state` is empty
            - Assign value of current state cache with timestamp
            - Addresses cold start
        - During subsequent scheduled daemon thread transactions
            - `g_cached_state` doesn't equal to current state_cache, 
            assign the most recent state_cache with current timestamp 
            (not from timestamp() function) and returns globally cached state   
    
    Returns:
        dict: current state cache
    """
    global g_cached_state
    state_val = cur_state()
    state_date = poll_timestamp
    state_cache = state_val | state_date     
    if not g_cached_state:
        g_cached_state = state_cache
    elif g_cached_state is not state_cache:
        poll_timestamp["poll_date"] = datetime.now().strftime(date_format)
        g_cached_state = state_val | poll_timestamp 
        return  g_cached_state
    return state_cache

scheduled_daemon.add_job(
    current_state,
    'interval',
    seconds=int(esddns_config["daemon_thread_interval"]))
scheduled_daemon.start()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True
with app.app_context():
    global_cache()
    current_state()

@app.route("/raw")
def start():
    """endpoint: /raw 

    Renders:
        dict: dynamic global cached state
    """
    return g_cached_state

@app.route("/")
def render_page():
    """endpoint: / 

    Renders:
        html: HTML page with data composed from dynamic global cached state
    """
    return render_template("esddns.html", display_cached=g_cached_state)

if __name__ == '__main__':
    app.run(
        debug=True, 
        host=config["ESDDNS"]["service_host"], 
        port=config["ESDDNS"]["service_port"], 
        threaded=True)