from db_logger_core import *
from db_logger_aux_fun import *

import gv  # Get access to SIP's settings, gv = global variables

import os

def open_file_2_save_valves():
    global file2SaveDB

    today = datetime.date.today()
    file2SaveDB = open(u"./data/db_logger_valves_raw"+ str(today.year) +"_"+ str(today.month) +".txt", "a")

def valve_reg_ON(valveId, curDBLog):
    global dbDefinitions

    if dbDefinitions[u"serverType"] == 'sqlLite':
        curDBLog.execute("INSERT INTO valves_raw (ValveRawFK, ValveRawON, ValveRawOFF) VALUES ("+ str(valveId) +", datetime('now','localtime'), datetime('now','localtime'))")
    elif dbDefinitions[u"serverType"] == 'fromFile':
        file2SaveDB.write(str(valveId) + ", " + str(datetime.datetime.now()) + ", ON\n")
    elif dbDefinitions[u"serverType"] == 'mySQL':
        curDBLog.execute("INSERT INTO valves_raw (ValveRawFK, ValveRawON, ValveRawOFF) VALUES ("+ str(valveId) +", NOW(), NOW())")

def valve_reg_OFF(valveId, curDBLog):
    global dbDefinitions, file2SaveDB

    if dbDefinitions[u"serverType"] == 'fromFile':
        file2SaveDB.write(str(valveId) + ", " + str(datetime.datetime.now()) + ", OFF\n")
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        # start to check if any on to complete with of
        curDBLog.execute("SELECT * FROM valves_raw WHERE ValveRawON = ValveRawOFF AND ValveRawFK = "+ str(valveId) +" ORDER BY ValveRawId DESC")
        data = curDBLog.fetchone()
        if data is not None:
            if len(data) == 4:
                # Add turn of in on register
                if dbDefinitions[u"serverType"] == 'sqlLite':
                    curDBLog.execute("UPDATE valves_raw SET ValveRawOFF = datetime('now','localtime') WHERE ValveRawId = "+ str(data[0]))
                else:
                    # Mysql
                    curDBLog.execute("UPDATE valves_raw SET ValveRawOFF = NOW() WHERE ValveRawId = "+ str(data[0]))

def valve_reg_close_db(conDB):
    global dbDefinitions, file2SaveDB

    if dbDefinitions[u"serverType"] == 'fromFile':
        file2SaveDB.close()
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        conDB.commit()

def get_list_of_files_valves_raw(dbDefinitions):
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
    global mutexDB

    dbDefinitions = gv.dbDefinitions

    listValves = []

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        dirPath = u"./data/"

        listOfFiles = get_list_of_files_valves_raw(dbDefinitions)
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
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
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

def estimate_valve_turnon_by_month(valveId, yearMin, monthMin, yearMax, monthMax):
    global mutexDB

    dbDefinitions = gv.dbDefinitions

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
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            currentMonthMaxDay = calendar.monthrange(yearMax, monthMax)[1]
            sqlQuery = "SELECT ValveRawFK, ValveRawON, ValveRawOFF FROM valves_raw WHERE ValveRawON != ValveRawOFF AND ValveRawON <= '"+ str(yearMax) +"-"+ str(monthMax) +"-"+ str(currentMonthMaxDay) +" 23:59:59' AND ValveRawOFF >= '"+ str(yearMin) +"-"+ str(monthMin) +"-01 00:00:00'"
            curDBLog.execute(sqlQuery)
            # Clean up data to display in page
            for currData in curDBLog:
                if int(currData[0]) == valveId:
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

def estimate_valve_turnon_by_day(valveId, yearMin, monthMin, dayMin, yearMax, monthMax, dayMax):
    global mutexDB

    statsPeriod = {}

    dbDefinitions = gv.dbDefinitions

    minDate = datetime.datetime(yearMin, monthMin, dayMin)
    maxDate = datetime.datetime(yearMax, monthMax, dayMax)

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

                                estimate_valve_turn_on_by_day_entry(dOn, dOff, minDate, maxDate, statsPeriod)
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            currentMonthMaxDay = calendar.monthrange(yearMax, monthMax)[1]
            sqlQuery = "SELECT ValveRawFK, ValveRawON, ValveRawOFF FROM valves_raw WHERE ValveRawON != ValveRawOFF AND ValveRawON <= '"+ str(yearMax) +"-"+ str(monthMax) +"-"+ str(currentMonthMaxDay) +" 23:59:59' AND ValveRawOFF >= '"+ str(yearMin) +"-"+ str(monthMin) +"-01 00:00:00'"
            curDBLog.execute(sqlQuery)
            # Clean up data to display in page
            for currData in curDBLog:
                if int(currData[0]) == valveId:
                    if dbDefinitions[u"serverType"] == 'mySQL':
                        # mySQL
                        newRow = [str(currData[1].year)+"/"+str(currData[1].month)+"/"+str(currData[1].day)+" "+str(currData[1].hour)+":"+str(currData[1].minute)+":"+str(currData[1].second), str(currData[2].year)+"/"+str(currData[2].month)+"/"+str(currData[2].day)+" "+str(currData[2].hour)+":"+str(currData[2].minute)+":"+str(currData[2].second)]
                    else:
                        newRow = [currData[0], currData[1], currData[2]]

                    dOn = datetime.datetime.strptime(str(newRow[0]), '%Y/%m/%d %H:%M:%S')
                    dOff = datetime.datetime.strptime(str(newRow[1]), '%Y/%m/%d %H:%M:%S')

                    estimate_valve_turn_on_by_day_entry(dOn, dOff, minDate, maxDate, statsPeriod)

    mutexDB.release()

    for key in statsPeriod:
        statsPeriod[key] = estimate_compose_dif_date_time_sec(statsPeriod[key])

    return statsPeriod

def get_reg_valves(numberOfReg, dbDefinitions):
    records = []

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

    return records



