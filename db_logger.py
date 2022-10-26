#!/usr/bin/env python

# Python 2/3 compatibility imports
from __future__ import print_function

# standard library imports
import json
import subprocess
import time

# Library to use DB
import sqlite3
from threading import Thread, Lock

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

mutexDB = Lock()

# Read in the commands for this plugin from it's JSON file
def load_connect_2_DB(ipPathDB, userName, passWord, dbName):
    global dbDefinitions

    if dbDefinitions[u"serverType"] == 'sqlLite':
        # TODO check if open DB with sucess
        conDB = sqlite3.connect(ipPathDB)
        dbIsOpen = True
    else:
        # Mysql
        pass

    if not dbIsOpen:
        return dbIsOpen, conDB, None
    else:
        curDBLog = conDB.cursor()
        return dbIsOpen, conDB, curDBLog

def load_commands():
    global dbDefinitions, mutexDB
    try:
        with open(u"./data/db_logger.json", u"r") as f:
            dbDefinitions = json.load(f)  # Read the commands from file
    except IOError:  #  If file does not exist create file with defaults.
        dbDefinitions = {u"serverType": "none", u"userName": "", u"passWord": "", u"ipPathDB": "", u"dbName": "SIPLog", u"saveValveRaw": 0, u"saveProgState": 0, u"saveSIPStart": 0, u"saveSIPStop": 0, u"saveSIPRest": 0, u"saveProgChange": 0, u"saveGeneralDefinitions": 0, u"saveUserLogIn": 0}
        with open(u"./data/db_logger.json", u"w") as f:
            json.dump(dbDefinitions, f, indent=4)

    # start to open DB
    mutexDB.acquire()

    if dbDefinitions[u"serverType"] != 'none':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB("./data/" + dbDefinitions[u"ipPathDB"] + ".db", dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])

        if not dbIsOpen:
            mutexDB.release()
            return

        if dbDefinitions[u"serverType"] == 'sqlLite':
            curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_id (ValveId integer primary key, ValveIdName TEXT NOT NULL)")
        else:
            # Mysql DB
            pass

        # if not exists create table with raw turn and turn off
        if dbDefinitions[u"saveValveRaw"] == 1:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_raw (ValveRawId integer primary key, ValveRawFK integer NOT NULL, ValveRawON datetime default current_timestamp, ValveRawOFF datetime default current_timestamp, FOREIGN KEY(ValveRawFK) REFERENCES valves_id(ValveId))")
            else:
                # Mysql DB
                pass

        #for i in range(len(gv.srvals)):
        res = curDBLog.execute("SELECT COUNT(ValveId) as totalNumber FROM valves_id")
        totalNumber = res.fetchone()[0]
        if len(gv.srvals) > totalNumber:
            for i in range(len(gv.srvals) - totalNumber):
                if dbDefinitions[u"serverType"] == 'sqlLite':
                    curDBLog.execute("INSERT INTO valves_id (ValveIdName) VALUES ('"+ gv.snames[totalNumber + i] +"')")
                else:
                    # Mysql DB
                    pass
        
        # Update valve Name
        for i in range(totalNumber):
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("UPDATE valves_id SET ValveIdName = '"+ gv.snames[i] +"' WHERE ValveId = "+ str(i + 1))
            else:
                # Mysql DB
                pass

        # if not exist create table to save turn on SIP
        if dbDefinitions[u"saveSIPStart"] == 1:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("CREATE TABLE IF NOT EXISTS sip_start (SIPStartId integer primary key, SIPStartTime datetime default current_timestamp)")
                curDBLog.execute("INSERT INTO sip_start (SIPStartTime) VALUES (datetime('now','localtime'))")
            else:
                # Mysql DB
                pass

        conDB.commit()

    mutexDB.release()

    return


load_commands()

#### output command when signal received ####
def on_zone_change(name, **kw):
    """ Send command when core program signals a change in station state."""
    global prior, dbDefinitions, dbIsOpen, curDBLog

    # If disable raw log exit
    if dbDefinitions[u"saveValveRaw"] == 0:
        return

    if gv.srvals != prior:  # check for a change
        mutexDB.acquire()
        dbIsOpen, conDB, curDBLog = load_connect_2_DB("./data/" + dbDefinitions[u"ipPathDB"] + ".db", dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])

        if not dbIsOpen:
            mutexDB.release()
            return

        for i in range(len(gv.srvals)):
            if gv.srvals[i] != prior[i]:  #  this station has changed
                if gv.srvals[i]:  # station is on
                    # valve turn on add to LOG
                    if dbDefinitions[u"serverType"] == 'sqlLite':
                        curDBLog.execute("INSERT INTO valves_raw (ValveRawFK, ValveRawON, ValveRawOFF) VALUES ("+ str(i + 1) +", datetime('now','localtime'), datetime('now','localtime'))")
                    else:
                        # Mysql DB
                        pass
                else: # station is off
                    # start to check if any on to complete with of
                    res = curDBLog.execute("SELECT * FROM valves_raw WHERE ValveRawON = ValveRawOFF AND ValveRawFK = "+ str(i + 1) +" ORDER BY ValveRawId DESC")
                    data = res.fetchone()
                    if data is not None:
                        if len(data) == 4:
                            # Add turn of in on register
                            curDBLog.execute("UPDATE valves_raw SET ValveRawOFF = datetime('now','localtime') WHERE ValveRawId = "+ str(data[0]))

        conDB.commit()
        mutexDB.release()

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
