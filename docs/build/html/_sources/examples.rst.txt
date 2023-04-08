.. ESDDNS documentation master file, created by
   sphinx-quickstart on Mon Apr  3 00:28:38 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


ESDDNS usage examples
=====================

.. note::
   ESDDNS currently supports `gandi.net <https://www.gandi.net/>`_ only.

   I do not have any affiliation with `gandi.net <https://www.gandi.net/>`_ except buying few domains from them,
   They have a really good service and LIVE DNS API which is used by ESDDNS.

   Next major version of ESDDNS will focus on support for managing of 
   `AWS Route 53 DNS A Record. <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/ResourceRecordTypes.html#AFormat>`_ 

Sensitive data management
#########################
Or the data which should not be stored neither online or inside this repo

Create a hidden folder in your home directory

.. warning::
   Author acknowledges the above sugesstion is mediocretes level solution
   and promises to get you a proper secret management with Keyring in near future.

**Step 1.**
Open terminal application, paste following code to create `env_vars.sh` file with environment variables
in your home directory under `~/.esddns` 

   .. code-block:: bash

      mkdir ~/.esddns
      tee -a ~/.esddns/env_vars.sh << EOF
      export API_KEY="********"
      export TARGET_DOMAIN_FQDN=example.com
      export RECORD_NAME_ROOT=@
      export RECORD_TYPE_A=A
      export RECORD_TTL=300
      export LOG_TO_CONSOLE=True
      export WAN_IP_RETRY_ATTEMPTS=3
      export WAN_IP_RETRY_COOLDOWN_SECONDS=15
      export ESDDNS_DAEMON_INTERVAL=300
      EOF

**Step 2.**
Edit `~/.esddns/env_vars.sh` file by replacing **API_KEY** and **TARGET_DOMAIN_FQDN**
or other variable per your desire, save changes

.. note::

   ESDDNS is capable running as a standalone server with scheduled daemon thread,
   daemon thread's component `interval` is set in the configuration file `esddns/dns.ini`
   as a reference to the environment variable `ESDDNS_DAEMON_INTERVAL`

      Example      
      - ``ESDDNS_DAEMON_INTERVAL=300``

   Logging to console is toggled by `LOG_TO_CONSOLE` environment variable
      - ``LOG_TO_CONSOLE=True``- To enable logging to both console and file 
      - ``LOG_TO_CONSOLE=False`` - To disable console logs 


Running ESDDNS as Standalone
############################

**Step 1.**
Execute ``. ~/.esddns/env_vars.sh``
Exports environment variables for ESDDNS to read from environment variables  

**Step 2.**
Execute ``python3 esddns.py`` - Run ESDDNS in Standalone Mode!

**Expected behavior**

You will see similar output:
  
.. image:: _static/esddns_standalone.png
   :width: 800

.. code:: 

   sqe@sqe-ThinkPad-X220 ~/e/esddns> python3 esddns.py
   2023-04-06 15:59:40,136 INFO 
      --------------|----|----------
      ,---.,---.,---|,---|,---.,---.
      |---'`---.|   ||   ||   |`---.
      `---'`---'`---'`---'`   '`---'
               For Emil and Stella!
      
      Welcome to ESDDNS Standalone mode!

      ESDDNS is an Open Source solution to automatically synchronize public 
      WAN IPv4 address with a target DNS A Record when there is a configuration drift 
      due to IPv4 address changes. 
      
      Creates and manages dynamic states for WAN IPv4 and DNS Record.  
      Utilizes dynamic public WAN IPv4 address discovered and retrieved from 
      external IPv4 check services, automatically synchronizes it with 
      managed DNS A record via REST APIs.

      ---------------------------------
      Scheduled Daemon Thread Interval: 300 seconds
         
   2023-04-06 15:59:40,137 INFO "ESDDNS Standalone scheduler started!"
   2023-04-06 15:59:40,138 INFO "Running scheduled daemon thread!"
   2023-04-06 15:59:40,147 DEBUG Starting new HTTPS connection (1): api.ipify.org:443
   2023-04-06 15:59:40,147 DEBUG Starting new HTTPS connection (1): checkip.amazonaws.com:443
   2023-04-06 15:59:40,149 DEBUG Starting new HTTPS connection (1): ifconfig.me:443
   2023-04-06 15:59:40,442 DEBUG https://ifconfig.me:443 "GET /ip HTTP/1.1" 200 13
   2023-04-06 15:59:40,443 INFO "SUCCESS: https://ifconfig.me/ip Returned: 73.96.163.207 as your WAN IPv4"
   2023-04-06 15:59:40,534 DEBUG https://api.ipify.org:443 "GET /?format=text HTTP/1.1" 200 13
   2023-04-06 15:59:40,536 INFO "SUCCESS: https://api.ipify.org/?format=text Returned: 73.96.163.207 as your WAN IPv4"
   2023-04-06 15:59:40,653 DEBUG https://checkip.amazonaws.com:443 "GET / HTTP/1.1" 200 14
   2023-04-06 15:59:40,655 INFO "SUCCESS: https://checkip.amazonaws.com/ Returned: 73.96.163.207 as your WAN IPv4"
   2023-04-06 15:59:40,657 INFO "SUCCESS: IPv4 addresses from external services match! {'wan_ip_state': {'usable': True, 'IP': '73.96.163.207'}}"
   2023-04-06 15:59:40,659 DEBUG Starting new HTTPS connection (1): api.gandi.net:443
   2023-04-06 15:59:41,570 DEBUG https://api.gandi.net:443 "GET /v5/livedns/domains HTTP/1.1" 200 2821
   2023-04-06 15:59:41,571 INFO "Get all domains"
   2023-04-06 15:59:41,573 INFO "Searching for the target domain..."
   2023-04-06 15:59:41,573 INFO "SUCCESS: Target domain has been found! sqapy.com"
   2023-04-06 15:59:41,575 DEBUG Starting new HTTPS connection (1): api.gandi.net:443
   2023-04-06 15:59:42,569 DEBUG https://api.gandi.net:443 "GET /v5/livedns/domains/sqapy.com/records HTTP/1.1" 200 2674
   2023-04-06 15:59:42,570 INFO "Get all records for the domain"
   2023-04-06 15:59:42,572 INFO "SUCCESS: A record for Root has been found {'rrset_name': '@', 'rrset_type': 'A', 'rrset_ttl': 300, 'rrset_values': ['73.96.163.207'], 'rrset_href': 'https://api.gandi.net/v5/livedns/domains/sqapy.com/records/%40/A'}"
   2023-04-06 15:59:42,572 INFO "Validating IPv4 from A record state: 73.96.163.207 vs IPv4 from wan_ip_state: 73.96.163.207"
   2023-04-06 15:59:42,572 INFO A Record state has correct IP!
   2023-04-06 15:59:42,572 INFO "SUCCESS: IPv4 and DNS A record states are in sync: {'wan_ip_state': {'usable': True, 'IP': '73.96.163.207'}, 'record_state': {'in_sync': True, 'record_data': {'rrset_name': '@', 'rrset_type': 'A', 'rrset_ttl': 300, 'rrset_values': ['73.96.163.207'], 'rrset_href': 'https://api.gandi.net/v5/livedns/domains/sqapy.com/records/%40/A'}}}"
   2023-04-06 15:59:42,573 INFO "Next scheduled run in 300 seconds"

.. warning::

   If you see following output, means that you have not exported API_KEY correctly,
   please revise and make sure you have correct API_KEY in ``~/.esddns/env_vars.sh``

   .. code::

      023-04-06 20:04:17,346 DEBUG https://api.gandi.net:443 "GET /v5/livedns/domains HTTP/1.1" 401 92
      2023-04-06 20:04:17,349 CRITICAL 401 Client Error: Unauthorized for url: https://api.gandi.net/v5/livedns/domains
      401 Client Error: Unauthorized for url: https://api.gandi.net/v5/livedns/domains