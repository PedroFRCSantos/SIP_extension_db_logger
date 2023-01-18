# Library to use DB
try:
    import sqlite3
    withDBLoggerSQlite = True
except ImportError:
    withDBLoggerSQlite = False

try:
    import mysql.connector
    withDBLoggerMysql = True
except ImportError:
    withDBLoggerMysql = False

from threading import Thread, Lock
import datetime
import calendar
import json

import gv  # Get access to SIP's settings, gv = global variables

from db_logger_aux_fun import *

mutexDB = Lock()

dbDefinitions = {}
priorLogger = [0] * len(gv.srvals)

def db_logger_read_definitions():
    dbDefinitions = {}

    try:
        with open(u"./data/db_logger.json", u"r") as f:
            dbDefinitions = json.load(f)  # Read the commands from file
    except IOError:  #  If file does not exist create file with defaults.
        dbDefinitions = {u"serverType": "none", u"userName": "", u"passWord": "", u"ipPathDB": "", u"dbName": "SIPLog", u"saveValveRaw": 0, u"saveProgState": 0, u"saveSIPStart": 0, u"saveSIPStop": 0, u"saveSIPRest": 0, u"saveProgChange": 0, u"saveGeneralDefinitions": 0, u"saveUserLogIn": 0}
        with open(u"./data/db_logger.json", u"w") as f:
            json.dump(dbDefinitions, f, indent=4)

    return dbDefinitions

# Read in the commands for this plugin from it's JSON file
def load_connect_2_DB(ipPathDB, userName, passWord, dbName, dbDefinitions):
    # No library acconding to definitions
    if (dbDefinitions[u"serverType"] == 'sqlLite' and not withDBLoggerSQlite) or (dbDefinitions[u"serverType"] == 'mySQL' and not withDBLoggerMysql):
        return

    dbIsOpen = False

    if dbDefinitions[u"serverType"] == 'sqlLite':
        # TODO check if open DB with sucess
        conDB = sqlite3.connect(ipPathDB)
        dbIsOpen = True
    elif dbDefinitions[u"serverType"] == 'mySQL':
        # Mysql
        try:
            conDB = mysql.connector.connect(host = ipPathDB, user = userName, password = passWord)
            dbIsOpen = True
        except mysql.connector.Error as err:
            print("Something went wrong: {}".format(err))
    elif dbDefinitions[u"serverType"] == 'fromFile':
        dbIsOpen = True

    if not dbIsOpen:
        return dbIsOpen, None, None
    else:
        if dbDefinitions[u"serverType"] == 'sqlLite':
            curDBLog = conDB.cursor()
        elif dbDefinitions[u"serverType"] == 'mySQL':
            curDBLog = conDB.cursor(buffered=True)

            curDBLog.execute("CREATE DATABASE IF NOT EXISTS " + dbName)
            curDBLog.execute("USE " + dbName)

        if dbDefinitions[u"serverType"] == 'fromFile':
            return dbIsOpen, None, None
        else:
            return dbIsOpen, conDB, curDBLog

def initiate_DB_if_not_exists(dbDefinitions):
    if dbDefinitions[u"serverType"] != 'none':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)

        if not dbIsOpen:
            return

        if dbDefinitions[u"serverType"] == 'sqlLite':
            curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_id (ValveId integer primary key, ValveIdName TEXT NOT NULL)")
        elif dbDefinitions[u"serverType"] == 'mySQL':
            curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_id (ValveId int NOT NULL AUTO_INCREMENT, ValveIdName TEXT NOT NULL, PRIMARY KEY (ValveId))")

        # if not exists create table with raw turn and turn off
        if dbDefinitions[u"saveValveRaw"] == 1:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_raw (ValveRawId integer primary key, ValveRawFK integer NOT NULL, ValveRawON datetime default current_timestamp, ValveRawOFF datetime default current_timestamp, FOREIGN KEY(ValveRawFK) REFERENCES valves_id(ValveId))")
            elif dbDefinitions[u"serverType"] == 'mySQL':
                # Mysql DB
                curDBLog.execute("CREATE TABLE IF NOT EXISTS valves_raw (ValveRawId int NOT NULL AUTO_INCREMENT, ValveRawFK integer NOT NULL, ValveRawON datetime NOT NULL DEFAULT NOW(), ValveRawOFF datetime NOT NULL DEFAULT NOW(), PRIMARY KEY (ValveRawId), FOREIGN KEY(ValveRawFK) REFERENCES valves_id(ValveId))")

        if dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            # Add missin valves id
            res = curDBLog.execute("SELECT COUNT(ValveId) as totalNumber FROM valves_id")
            if res is not None:
                totalNumber = res.fetchone()[0]
            else:
                totalNumber = 0
            if len(gv.srvals) > totalNumber:
                for i in range(len(gv.srvals) - totalNumber):
                    curDBLog.execute("INSERT INTO valves_id (ValveIdName) VALUES ('"+ gv.snames[totalNumber + i] +"')")
        
            # Update valve Name
            for i in range(totalNumber):
                if dbDefinitions[u"serverType"] == 'sqlLite':
                    curDBLog.execute("UPDATE valves_id SET ValveIdName = '"+ gv.snames[i] +"' WHERE ValveId = "+ str(i + 1))

        # if not exist create table to save turn on SIP
        if dbDefinitions[u"saveSIPStart"] == 1:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("CREATE TABLE IF NOT EXISTS sip_start (SIPStartId integer primary key, SIPStartTime datetime default current_timestamp)")
                curDBLog.execute("INSERT INTO sip_start (SIPStartTime) VALUES (datetime('now','localtime'))")
            elif dbDefinitions[u"serverType"] == 'fromFile':
                file2SaveDB = open(u"./data/db_logger_sip_turn_on.txt", "a")
                file2SaveDB.write(str(datetime.datetime.now()) + "\n")
                file2SaveDB.close()
            elif dbDefinitions[u"serverType"] == 'mySQL':
                curDBLog.execute("CREATE TABLE IF NOT EXISTS sip_start (SIPStartId int NOT NULL AUTO_INCREMENT, SIPStartTime datetime NOT NULL DEFAULT NOW(), PRIMARY KEY (SIPStartId))")
                curDBLog.execute("INSERT INTO sip_start (SIPStartTime) VALUES (NOW())")

        if dbDefinitions[u"serverType"] == 'mySQL' or dbDefinitions[u"serverType"] == 'sqlLite':
            conDB.commit()
