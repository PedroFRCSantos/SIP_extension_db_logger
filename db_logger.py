#!/usr/bin/env python

# Python 2/3 compatibility imports
from __future__ import print_function

# standard library imports
import json
import subprocess
import time

# local module imports
from blinker import signal
import gv  # Get access to SIP's settings, gv = global variables
from sip import template_render
from urls import urls  # Get access to SIP's URLs
import web
from webpages import ProtectedPage

# Add a new url to open the data entry page.
# fmt: off
urls.extend(
    [
        u"/dblog", u"plugins.db_logger.settings",
        u"/dbjsonlog", u"plugins.db_logger.settings_json",
        u"/dblogupdate", u"plugins.db_logger.update",
    ]
)
# fmt: on

# Add this plugin to the plugins menu
gv.plugin_menu.append([u"DB Logger", u"/dblog"])

dbDefinitions = {}
prior = [0] * len(gv.srvals)

# Read in the commands for this plugin from it's JSON file
def load_commands():
    global dbDefinitions
    try:
        with open(u"./data/db_logger.json", u"r") as f:
            dbDefinitions = json.load(f)  # Read the commands from file
    except IOError:  #  If file does not exist create file with defaults.
        dbDefinitions = {u"serverType": "none", u"userName": "", u"passWord": "", u"ipPathDB": "", u"dbName": "SIPLog", u"saveValveRaw": 0, u"saveProgState": 0, u"saveSIPStart": 0, u"saveSIPStop": 0, u"saveSIPRest": 0, u"saveProgChange": 0, u"saveGeneralDefinitions": 0, u"saveUserLogIn": 0}
        with open(u"./data/db_logger.json", u"w") as f:
            json.dump(dbDefinitions, f, indent=4)
    return


load_commands()

#### output command when signal received ####
def on_zone_change(name, **kw):
    """ Send command when core program signals a change in station state."""
    global prior
    if gv.srvals != prior:  # check for a change
        for i in range(len(gv.srvals)):
            if gv.srvals[i] != prior[i]:  #  this station has changed
                if gv.srvals[i]:  # station is on
                    pass
                else:
                    pass
        prior = gv.srvals[:]
    return


zones = signal(u"zone_change")
zones.connect(on_zone_change)

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering cli_control commands"""

    def GET(self):
        return template_render.db_logger(dbDefinitions)


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format"""

    def GET(self):
        web.header(u"Access-Control-Allow-Origin", u"*")
        web.header(u"Content-Type", u"application/json")
        return json.dumps(dbDefinitions)


class update(ProtectedPage):
    """Save user input to cli_control.json file"""

    def GET(self):
        global dbDefinitions
        qdict = web.input()
        
        if u"dbType" in qdict:
            dbDefinitions[u"serverType"] = qdict[u"dbType"]

        if u"uname" in qdict:
            dbDefinitions[u"userName"] = qdict[u"uname"]

        if u"pwd" in qdict:
            dbDefinitions[u"passWord"] = qdict[u"pwd"]

        if u"ippath" in qdict:
            dbDefinitions[u"ipPathDB"] = qdict[u"ippath"]

        if u"dbname" in qdict:
            dbDefinitions[u"dbName"] = qdict[u"dbname"]

        if u"valRaw" in qdict:
            dbDefinitions[u"saveValveRaw"] = 1
        else:
            dbDefinitions[u"saveValveRaw"] = 0

        if u"progState" in qdict:
            dbDefinitions[u"saveProgState"] = 1
        else:
            dbDefinitions[u"saveProgState"] = 0

        if u"sipStart" in qdict:
            dbDefinitions[u"saveSIPStart"] = 1
        else:
            dbDefinitions[u"saveSIPStart"] = 0

        if u"progStop" in qdict:
            dbDefinitions[u"saveSIPStop"] = 1
        else:
            dbDefinitions[u"saveSIPStop"] = 0

        if u"sipRest" in qdict:
            dbDefinitions[u"saveSIPRest"] = 1
        else:
            dbDefinitions[u"saveSIPRest"] = 0

        if u"progChange" in qdict:
            dbDefinitions[u"saveProgChange"] = 1
        else:
            dbDefinitions[u"saveProgChange"] = 0

        if u"generalDef" in qdict:
            dbDefinitions[u"saveGeneralDefinitions"] = 1
        else:
            dbDefinitions[u"saveGeneralDefinitions"] = 0

        if u"userLogIn" in qdict:
            dbDefinitions[u"saveUserLogIn"] = 1
        else:
            dbDefinitions[u"saveUserLogIn"] = 0

        with open(u"./data/db_logger.json", u"w") as f:  # write the settings to file
            json.dump(dbDefinitions, f, indent=4)
        raise web.seeother(u"/restart")
