#!/usr/bin/env python

# Python 2/3 compatibility imports
from __future__ import print_function
from itertools import count

# standard library imports
import json
from math import floor
import subprocess
from sys import float_repr_style
import time
import os

from threading import Thread, Lock
import datetime

import calendar

from db_logger_core import *
from db_logger_valves import *
from db_logger_SIP_start import *

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
        u"/dblogturnon", u"plugins.db_logger.turn_on_display",
        u"/dblogvalve", u"plugins.db_logger.valve_status_display",
    ]
)
# fmt: on

# Add this plugin to the plugins menu
gv.plugin_menu.append([u"DB Logger", u"/dblog"])

def load_commands_db_logger():
    global dbDefinitions, mutexDB, file2SaveDB

    dbDefinitions = db_logger_read_definitions()

    if (dbDefinitions[u"serverType"] == 'sqlLite' and not withDBLoggerSQlite) or (dbDefinitions[u"serverType"] == 'mySQL' and not withDBLoggerMysql):
        return

    # start to open DB
    mutexDB.acquire()

    initiate_DB_if_not_exists(dbDefinitions)

    mutexDB.release()

    return


load_commands_db_logger()

#### output command when signal received ####
def on_zone_change(name, **kw):
    """ Send command when core program signals a change in station state."""
    global priorLogger, dbDefinitions, dbIsOpen, curDBLog

    # No library acconding to definitions
    if (dbDefinitions[u"serverType"] == 'sqlLite' and not withDBLoggerSQlite) or (dbDefinitions[u"serverType"] == 'mySQL' and not withDBLoggerMysql):
        return

    # If disable raw log exit
    if dbDefinitions[u"saveValveRaw"] == 0:
        return

    if gv.srvals != priorLogger:  # check for a change
        mutexDB.acquire()

        curDBLog = None

        if dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])

            if not dbIsOpen:
                mutexDB.release()
                return
        elif dbDefinitions[u"serverType"] == 'fromFile':
            open_file_2_save_valves()

        for i in range(len(gv.srvals)):
            if gv.srvals[i] != priorLogger[i]:  #  this station has changed
                if gv.srvals[i]:  # station is on
                    # valve turn on add to LOG
                    valve_reg_ON(i + 1, curDBLog)
                else: # station is off
                    valve_reg_OFF(i + 1, curDBLog)

        valve_reg_close_db(conDB)

        mutexDB.release()

        priorLogger = gv.srvals[:]
    return

zones = signal(u"zone_change")
zones.connect(on_zone_change)

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering db logs commands"""

    def GET(self):
        return template_render.db_logger(dbDefinitions)

class turn_on_display(ProtectedPage):
    """Load an html page for entering cli_control commands"""

    def GET(self):
        numberOfReg = 30

        qdict = web.input()
        if u"reg2view" in qdict:
            try:
                numberOfReg = int(qdict[u"reg2view"])
                if numberOfReg < 1:
                    numberOfReg = 1
            except ValueError:
                pass

        mutexDB.acquire()

        records = get_list_SIP_reg(numberOfReg, dbDefinitions)

        mutexDB.release()

        return template_render.db_logger_turn_on(records, numberOfReg)

class valve_status_display(ProtectedPage):
    """Load an html page display valves change"""

    def GET(self):
        numberOfReg = 30

        qdict = web.input()
        if u"reg2view" in qdict:
            try:
                numberOfReg = int(qdict[u"reg2view"])
                if numberOfReg < 1:
                    numberOfReg = 1
            except ValueError:
                pass

        mutexDB.acquire()

        records = get_reg_valves(numberOfReg, dbDefinitions)

        mutexDB.release()

        return template_render.db_logger_valve_status(records, numberOfReg)

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
