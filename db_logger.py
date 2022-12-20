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

dbDefinitions = {}
prior = [0] * len(gv.srvals)

mutexDB = Lock()

# Read in the commands for this plugin from it's JSON file
def load_connect_2_DB(ipPathDB, userName, passWord, dbName):
    global dbDefinitions

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

def load_commands():
    global dbDefinitions, mutexDB, file2SaveDB

    try:
        with open(u"./data/db_logger.json", u"r") as f:
            dbDefinitions = json.load(f)  # Read the commands from file
    except IOError:  #  If file does not exist create file with defaults.
        dbDefinitions = {u"serverType": "none", u"userName": "", u"passWord": "", u"ipPathDB": "", u"dbName": "SIPLog", u"saveValveRaw": 0, u"saveProgState": 0, u"saveSIPStart": 0, u"saveSIPStop": 0, u"saveSIPRest": 0, u"saveProgChange": 0, u"saveGeneralDefinitions": 0, u"saveUserLogIn": 0}
        with open(u"./data/db_logger.json", u"w") as f:
            json.dump(dbDefinitions, f, indent=4)

    if (dbDefinitions[u"serverType"] == 'sqlLite' and not withDBLoggerSQlite) or (dbDefinitions[u"serverType"] == 'mySQL' and not withDBLoggerMysql):
        return

    # start to open DB
    mutexDB.acquire()

    if dbDefinitions[u"serverType"] != 'none':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])

        if not dbIsOpen:
            mutexDB.release()
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

    mutexDB.release()

    return


load_commands()

#### output command when signal received ####
def on_zone_change(name, **kw):
    """ Send command when core program signals a change in station state."""
    global prior, dbDefinitions, dbIsOpen, curDBLog

    # No library acconding to definitions
    if (dbDefinitions[u"serverType"] == 'sqlLite' and not withDBLoggerSQlite) or (dbDefinitions[u"serverType"] == 'mySQL' and not withDBLoggerMysql):
        return

    # If disable raw log exit
    if dbDefinitions[u"saveValveRaw"] == 0:
        return

    if gv.srvals != prior:  # check for a change
        mutexDB.acquire()
        if dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])

            if not dbIsOpen:
                mutexDB.release()
                return
        elif dbDefinitions[u"serverType"] == 'fromFile':
            today = datetime.date.today()
            file2SaveDB = open(u"./data/db_logger_valves_raw"+ str(today.year) +"_"+ str(today.month) +".txt", "a")

        for i in range(len(gv.srvals)):
            if gv.srvals[i] != prior[i]:  #  this station has changed
                if gv.srvals[i]:  # station is on
                    # valve turn on add to LOG
                    if dbDefinitions[u"serverType"] == 'sqlLite':
                        curDBLog.execute("INSERT INTO valves_raw (ValveRawFK, ValveRawON, ValveRawOFF) VALUES ("+ str(i + 1) +", datetime('now','localtime'), datetime('now','localtime'))")
                    elif dbDefinitions[u"serverType"] == 'fromFile':
                        file2SaveDB.write(str(i + 1) + ", " + str(datetime.datetime.now()) + ", ON\n")
                    elif dbDefinitions[u"serverType"] == 'mySQL':
                        curDBLog.execute("INSERT INTO valves_raw (ValveRawFK, ValveRawON, ValveRawOFF) VALUES ("+ str(i + 1) +", NOW(), NOW())")
                else: # station is off
                    if dbDefinitions[u"serverType"] == 'fromFile':
                        file2SaveDB.write(str(i + 1) + ", " + str(datetime.datetime.now()) + ", OFF\n")
                    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
                        # start to check if any on to complete with of
                        curDBLog.execute("SELECT * FROM valves_raw WHERE ValveRawON = ValveRawOFF AND ValveRawFK = "+ str(i + 1) +" ORDER BY ValveRawId DESC")
                        data = curDBLog.fetchone()
                        if data is not None:
                            if len(data) == 4:
                                # Add turn of in on register
                                if dbDefinitions[u"serverType"] == 'sqlLite':
                                    curDBLog.execute("UPDATE valves_raw SET ValveRawOFF = datetime('now','localtime') WHERE ValveRawId = "+ str(data[0]))
                                else:
                                    # Mysql
                                    curDBLog.execute("UPDATE valves_raw SET ValveRawOFF = NOW() WHERE ValveRawId = "+ str(data[0]))

        if dbDefinitions[u"serverType"] == 'fromFile':
            file2SaveDB.close()
        elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
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
    """Load an html page for entering db logs commands"""

    def GET(self):
        return template_render.db_logger(dbDefinitions)

class turn_on_display(ProtectedPage):
    """Load an html page for entering cli_control commands"""

    def GET(self):
        records = []
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

        if dbDefinitions[u"serverType"] == 'fromFile':
            fileLog = open(u"./data/db_logger_sip_turn_on.txt", 'r')
            while True:
                line = fileLog.readline()
                records.append(line)
                if len(records) > numberOfReg + 1:
                    records.pop(0)

                if not line:
                    break

            fileLog.close()
            records.reverse()

            records.pop(0)
        elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])
            if dbIsOpen:
                curDBLog.execute("SELECT SIPStartTime FROM sip_start ORDER BY SIPStartTime DESC LIMIT "+str(numberOfReg))
                recordsRaw = curDBLog.fetchall()
                # Clean up data to display in page
                for currData in recordsRaw:
                    if dbDefinitions[u"serverType"] == 'sqlLite':
                        records.append(currData[0])
                    else:
                        # mySQL
                        records.append(str(currData[0].year)+"/"+str(currData[0].month)+"/"+str(currData[0].day)+" "+str(currData[0].hour)+":"+str(currData[0].minute)+":"+str(currData[0].second))

        mutexDB.release()

        return template_render.db_logger_turn_on(records, numberOfReg)

def estimate_number_of_turn_on_by_month():
    statsMonthOut = {}

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        fileLog = open(u"./data/db_logger_sip_turn_on.txt", 'r')
        while True:
            line = fileLog.readline()

            if not line:
                break
            else:
                lineSplit = line.split("-")
                if len(lineSplit) == 3:
                    if (lineSplit[0] + "-" + lineSplit[1]) not in statsMonthOut:
                        statsMonthOut[lineSplit[0] + "-" + lineSplit[1]] = 1
                    else:
                        statsMonthOut[lineSplit[0] + "-" + lineSplit[1]] = statsMonthOut[lineSplit[0] + "-" + lineSplit[1]] + 1

        fileLog.close()
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])
        if dbIsOpen:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                curDBLog.execute("SELECT SIPStartTime, COUNT(SIPStartTime) as Total FROM sip_start GROUP BY strftime(\"%m-%Y\", SIPStartTime)")
            else:
                curDBLog.execute("SELECT SIPStartTime, COUNT(SIPStartTime) as Total FROM sip_start GROUP BY YEAR(SIPStartTime), MONTH(SIPStartTime)")
            recordsRaw = curDBLog.fetchall()
            # Clean up data to display in page
            for currData in recordsRaw:
                if dbDefinitions[u"serverType"] == 'sqlLite':
                    lineSplit = currData[0].split("-")
                    statsMonthOut[lineSplit[0] + "-" + lineSplit[1]] = int(currData[1])
                else:
                    # mySQL
                    statsMonthOut[str(currData[0].year) + "-" + str(currData[0].month)] = int(currData[1])

    mutexDB.release()

    return statsMonthOut

def get_list_of_files_valves_raw():
    res = []

    if dbDefinitions[u"serverType"] == 'fromFile':
        dirPath = u"./data/"

        for path in os.listdir(dirPath):
            if os.path.isfile(os.path.join(dirPath, path)):
                if path[0:len("db_logger_valves_raw")] == "db_logger_valves_raw":
                    res.append(path)

        res = sorted(res, reverse=False)

    return res

def get_list_of_valves():
    listValves = []

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        dirPath = u"./data/"

        listOfFiles = get_list_of_files_valves_raw()
        for file2Read in listOfFiles:
            fileLog = open(dirPath + file2Read, 'r')
            while True:
                line = fileLog.readline()
                if not line:
                    break
                lineSplit = line.split(',')
                if len(lineSplit) == 3 and lineSplit[0].isnumeric():
                    listValves.append(int(lineSplit[0]))

            listValves = list(set(listValves))
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])
        if dbIsOpen:
            sqlQuery = "SELECT DISTINCT ValveRawFK FROM valves_raw"
            curDBLog.execute(sqlQuery)
            # Clean up data to display in page
            for currData in curDBLog:
                listValves.append(currData[0])

    listValves.sort()

    mutexDB.release()

    listValvesWithNames = []
    for indexRecord in listValves:
        listValvesWithNames.append([indexRecord, gv.snames[indexRecord - 1]])

    return listValvesWithNames

def estimate_valves_turnon_in_month():
    statsMonthOut = {}

    mutexDB.acquire()

    mutexDB.release()

    return statsMonthOut

def min_year_month(year1, month1, year2, month2):
    minYear = 0
    minMonth = 0

    if year1 < year2:
        minYear = year1
        minMonth = month1
    elif year1 > year2:
        minYear = year2
        minMonth = month2
    elif month1 < month2:
        minYear = year1
        minMonth = month1
    else:
        minYear = year2
        minMonth = month2

    return minYear, minMonth

def max_year_month(year1, month1, year2, month2):
    minYear = 0
    minMonth = 0

    if year1 < year2:
        minYear = year2
        minMonth = month2
    elif year1 > year2:
        minYear = year1
        minMonth = month1
    elif month1 < month2:
        minYear = year2
        minMonth = month2
    else:
        minYear = year2
        minMonth = month2

    return minYear, minMonth

def estive_valve_turnon_by_month_entry(dOn, dOff, yearMin, monthMin, yearMax, monthMax, statsMonthOut):
    gapLowYear, gapLowMonth = max_year_month(dOn.year, dOn.month, yearMin, monthMin)
    gapHigthYear, gapHigthMonth = max_year_month(dOff.year, dOff.month, yearMax, monthMax)

    currentYear = gapLowYear
    currentMonth = gapLowMonth

    while currentYear < gapHigthYear or (currentYear == gapHigthYear and currentMonth <= gapHigthMonth):
        accumTimeSeconds = 0
        currentMonthMaxDay = calendar.monthrange(currentYear, currentMonth)[1]

        if (currentYear > dOn.year or (currentYear == dOn.year and currentMonth >= dOn.month)) and (currentYear < dOff.year or (currentYear == dOff.year and currentMonth <= dOff.month)):
            accumTimeSeconds = accumTimeSeconds + currentMonthMaxDay * 24 * 60 * 60

        if dOn.year == currentYear and dOn.month == currentMonth:
            # on in the current month, discont from begin of month
            beginDateTimeMonth = datetime.datetime(currentYear, currentMonth, 1)
            time2Discount = (dOn - beginDateTimeMonth).total_seconds()
            accumTimeSeconds = accumTimeSeconds - time2Discount

        if dOff.year == yearMin and dOff.month == currentMonth:
            # off is inside, discount until the end of month
            endDateTimeMonth = datetime.datetime(currentYear, currentMonth, currentMonthMaxDay, 23, 59, 59, 999999)
            time2Discount = (endDateTimeMonth - dOff).total_seconds()
            accumTimeSeconds = accumTimeSeconds - time2Discount

        try:
            statsMonthOut[str(currentYear) + str(currentMonth)] = statsMonthOut[str(currentYear) + str(currentMonth)] + accumTimeSeconds
        except:
            statsMonthOut[str(currentYear) + str(currentMonth)] = accumTimeSeconds

        currentMonth = currentMonth + 1
        if currentMonth > 12:
            currentMonth = 1
            currentYear = currentYear + 1

def estimate_valve_turnon_by_month(valveId, yearMin, monthMin, yearMax, monthMax):
    statsMonthOut = {}

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        listOfFiles = get_list_of_files_valves_raw()
        dirPath = u"./data/"

        auxValveOn = {}

        for file2Read in listOfFiles:
            fileLog = open(dirPath + file2Read, 'r')
            while True:
                line = fileLog.readline()
                if not line:
                    break

                # split line to get data
                lineSplit = line.split(',')
                if len(lineSplit) == 3:
                    if lineSplit[0].isnumeric():
                        lineValveRaw = int(lineSplit[0])
                        if valveId == lineValveRaw and lineSplit[2].replace(" ", "").replace("\n", "").replace("\r", "") == 'ON':
                            auxValveOn["Valve"+str(valveId)] = lineSplit[1]
                        elif valveId == lineValveRaw and lineSplit[2].replace(" ", "").replace("\n", "").replace("\r", "") == 'OFF':
                            if "Valve"+str(valveId) in auxValveOn:
                                dOn = datetime.datetime.strptime((((auxValveOn["Valve"+str(valveId)]).split('.'))[0].replace('-', '/'))[1:], '%Y/%m/%d %H:%M:%S')
                                dOff = datetime.datetime.strptime((((lineSplit[1]).split('.'))[0].replace('-', '/'))[1:], '%Y/%m/%d %H:%M:%S')

                                # if out of gap
                                if dOn.year > yearMax or (dOn.year == yearMax and dOn.month > monthMax):
                                    continue
                                if dOff.year < yearMin or (dOff.year == yearMin and dOff.month < monthMin):
                                    continue

                                estive_valve_turnon_by_month_entry(dOn, dOff, yearMin, monthMin, yearMax, monthMax, statsMonthOut)
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])
        if dbIsOpen:
            currentMonthMaxDay = calendar.monthrange(yearMax, monthMax)[1]
            sqlQuery = "SELECT ValveRawFK, ValveRawON, ValveRawOFF FROM valves_raw WHERE ValveRawON != ValveRawOFF AND ValveRawON <= '"+ str(yearMax) +"-"+ str(monthMax) +"-"+ str(currentMonthMaxDay) +" 23:59:59' AND ValveRawOFF >= '"+ str(yearMin) +"-"+ str(monthMin) +"-01 00:00:00'"
            curDBLog.execute(sqlQuery)
            # Clean up data to display in page
            for currData in curDBLog:
                if dbDefinitions[u"serverType"] == 'mySQL':
                    # mySQL
                    newRow = [str(currData[1].year)+"/"+str(currData[1].month)+"/"+str(currData[1].day)+" "+str(currData[1].hour)+":"+str(currData[1].minute)+":"+str(currData[1].second), str(currData[2].year)+"/"+str(currData[2].month)+"/"+str(currData[2].day)+" "+str(currData[2].hour)+":"+str(currData[2].minute)+":"+str(currData[2].second)]
                else:
                    newRow = [currData[0], currData[1], currData[2]]

                dOn = datetime.datetime.strptime(str(newRow[0]), '%Y/%m/%d %H:%M:%S')
                dOff = datetime.datetime.strptime(str(newRow[1]), '%Y/%m/%d %H:%M:%S')

                estive_valve_turnon_by_month_entry(dOn, dOff, yearMin, monthMin, yearMax, monthMax, statsMonthOut)

    mutexDB.release()

    for key in statsMonthOut:
        statsMonthOut[key] = estimate_compose_dif_date_time_sec(statsMonthOut[key])

    return statsMonthOut

def estimate_compose_dif_date_time_sec(diffSeconds):
    numberOfDay = floor(diffSeconds / (60*60*24))
    numberOfHour = floor((diffSeconds - numberOfDay *60*60*24) / (60*60))
    numberOfMinute = floor((diffSeconds - numberOfDay *60*60*24 - numberOfHour*60*60) / 60)
    numberOfSecond = round(diffSeconds - numberOfDay *60*60*24 - numberOfHour*60*60 - numberOfMinute*60, 2)

    str2ShowDiff = "";
    if numberOfDay > 0:
        str2ShowDiff = str2ShowDiff + str(numberOfDay) +"d "
    if numberOfHour < 10:
        str2ShowDiff = str2ShowDiff +"0"+ str(numberOfHour)
    else:
        str2ShowDiff = str2ShowDiff + str(numberOfHour)
    if numberOfMinute < 10:
        str2ShowDiff = str2ShowDiff +":0"+ str(numberOfMinute)
    else:
        str2ShowDiff = str2ShowDiff +":"+ str(numberOfMinute)
    str2ShowDiff = str2ShowDiff +":"+ str(numberOfSecond)

    return str2ShowDiff

def estimate_compose_dif_date_time(d1, d2):
    # estimate diff for human
    diff = (d2 - d1).total_seconds()
    return estimate_compose_dif_date_time_sec(diff)

def estimte_time_str_2_hour_float(strDate):
    valrOut = 0.0

    strDateSplit = strDate.split(":")

    if len(strDateSplit) == 3:
        valrOut = valrOut + float(strDateSplit[0])
        valrOut = valrOut + float(strDateSplit[1]) / 60.0
        valrOut = valrOut + float(strDateSplit[1]) / 60.0 / 60.0

    valrOut = round(valrOut, 4)

    return valrOut

class valve_status_display(ProtectedPage):
    """Load an html page display valves change"""

    def GET(self):
        records = []
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

        if dbDefinitions[u"serverType"] == 'fromFile':
            dirPath = u"./data/"

            res = []
            for path in os.listdir(dirPath):
                if os.path.isfile(os.path.join(dirPath, path)):
                    if path[0:len("db_logger_valves_raw")] == "db_logger_valves_raw":
                        res.append(path)

            res = sorted(res, reverse=False)
            for file2Read in res:
                fileLog = open(dirPath + file2Read, 'r')
                while True:
                    line = fileLog.readline()
                    if not line:
                        break

                    lineSplit = line.split(',')
                    if len(lineSplit) != 3:
                        continue

                    lineSplit[2] = lineSplit[2].strip()

                    if lineSplit[2] == "ON":
                        records.insert(0, [lineSplit[1], "", lineSplit[0], ""])
                        if len(records) > numberOfReg:
                            records.pop(len(records) - 1)
                    elif lineSplit[2] == "OFF":
                        for checkRecord in records:
                            if checkRecord[2] == lineSplit[0]:
                                checkRecord[1] = lineSplit[1]
                                # estimate on time
                                d1 = datetime.datetime.strptime((((checkRecord[0]).split('.'))[0].replace('-', '/'))[1:], '%Y/%m/%d %H:%M:%S')
                                d2 = datetime.datetime.strptime((((checkRecord[1]).split('.'))[0].replace('-', '/'))[1:], '%Y/%m/%d %H:%M:%S')

                                checkRecord[3] = estimate_compose_dif_date_time(d1, d2)
            
            # Sustitute numbers by names
            for record2Change in records:
                indexRecord = int(record2Change[2])
                record2Change[2] = gv.snames[indexRecord - 1]
        elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"])
            if dbIsOpen:
                curDBLog.execute("SELECT ValveRawON, ValveRawOFF, ValveIdName FROM valves_raw, valves_id WHERE ValveId = ValveRawFK ORDER BY ValveRawON DESC LIMIT "+str(numberOfReg))
                recordsRaw = curDBLog.fetchall()
                # Clean up data to display in page
                for currData in recordsRaw:
                    newRow = []
                    if dbDefinitions[u"serverType"] == 'sqlLite':
                        newRow = [currData[0], currData[1], currData[2]]
                    else:
                        # mySQL
                        newRow = [str(currData[0].year)+"/"+str(currData[0].month)+"/"+str(currData[0].day)+" "+str(currData[0].hour)+":"+str(currData[0].minute)+":"+str(currData[0].second), str(currData[1].year)+"/"+str(currData[1].month)+"/"+str(currData[1].day)+" "+str(currData[1].hour)+":"+str(currData[1].minute)+":"+str(currData[1].second), currData[2]]
                    
                    d1 = datetime.datetime.strptime(str(newRow[0]), '%Y/%m/%d %H:%M:%S')
                    d2 = datetime.datetime.strptime(str(newRow[1]), '%Y/%m/%d %H:%M:%S')

                    newRow.append(estimate_compose_dif_date_time(d1, d2))
                    records.append(newRow)

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
