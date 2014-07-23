#!/usr/bin/env python
"""
This is a Titan module

- Analyze local wireless networks
  including name and bssid/signal

To use:

    sudo pip install --upgrade titantools

"""

import json
import logging
from sys import argv
from titantools.orm import TiORM
from titantools.data_science import DataScience
from titantools.system import execute_command as shell_out
from titantools import plist

from time import time, gmtime, strftime
from os.path import dirname,basename,isfile
from os import chmod
#from titantools.decorators import run_every_5

# Set Logging Status
logging_enabled = False

# Set datastore directory
DATASTORE = argv[1]

#@run_every_5
class AnalyzeNearNetworks(object):
    """ AnalyzeNearNetworks """

    def __init__(self):
      self.message = type(self).__name__
      self.status = 0
      self.datastore = []

    def get_local_networks(self):
      """
      Log all networks
      """
      # Create the temp plist file
      shell_out('system_profiler SPAirPortDataType -xml > /tmp/titan-localnet.plist').split('\n')

      # Read them from plist
      access_points = plist.read_plist('/tmp/titan-localnet.plist')

      # Check for connected or not
      if 'spairport_airport_other_local_wireless_networks' in access_points[0]['_items'][0]['spairport_airport_interfaces'][0]:
        aps = access_points[0]['_items'][0]['spairport_airport_interfaces'][0]['spairport_airport_other_local_wireless_networks']

        # Add in current connected network
        aps += [access_points[0]['_items'][0]['spairport_airport_interfaces'][0]['spairport_current_network_information']]

      elif 'spairport_airport_local_wireless_networks' in access_points[0]['_items'][0]['spairport_airport_interfaces'][0]:
        aps = access_points[0]['_items'][0]['spairport_airport_interfaces'][0]['spairport_airport_local_wireless_networks']

      # Loop through discovered AP's
      for ap in aps:
        if 'spairport_network_rate' in ap:
          connected = 'true'
        else:
          connected = 'false'

        # Add to data store
        self.datastore.append({
          "date": exec_date,
          "ssid": ap['_name'],
          "name": ap['spairport_network_bssid'],
          "channel": ap['spairport_network_channel'],
          "mode": ap['spairport_network_phymode'],
          "security": ap['spairport_security_mode'].replace('spairport_security_mode_', ''),
          "signal": ap['spairport_signal_noise'].split(' / ')[0],  
          "noise": ap['spairport_signal_noise'].split(' / ')[1],  
          "connected": connected,
          }) 

      # Set Message
      self.message = "Found %d Networks" % len(self.datastore)

      # If no issues, return 0
      self.status = 0

    def analyze(self):
      """
      This is the 'main' method that launches all of the other checks
      """
      self.get_local_networks()

      return json.JSONEncoder().encode({"status": self.status, "message": self.message})

    def store(self):
      # the table definitions are stored in a library file. this is instantiating
      # the ORM object and initializing the tables
      module_schema_file = '%s/schema.json' % dirname(__file__)

      # Is file
      if isfile(module_schema_file):
        with open(module_schema_file) as schema_file:   
          schema = json.load(schema_file)

        # ORM 
        ORM = TiORM(DATASTORE)
        if isfile(DATASTORE):
            chmod(DATASTORE, 0600)
        for k, v in schema.iteritems():
            ORM.initialize_table(k, v)

        # Insert apps to database
        data_science = DataScience(ORM, self.datastore, "local_networks")
        data_science.get_new_entries()
        
if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S-%Z", gmtime())

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeNearNetworks()
        if a is not None:
            output = a.analyze()
            a.store()
            print output

    except Exception, error:
        print error

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
      logging_enabled = True
      logging.basicConfig(format='%(message)s', level=logging.INFO)
    
    logging.info("Execution took %s seconds.", str(end - start))
