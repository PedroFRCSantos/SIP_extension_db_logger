from db_logger_core import *
from db_logger_aux_fun import *
from datetime import datetime, timedelta

import gv  # Get access to SIP's settings, gv = global variables

import os

file2SaveDBFlowSensor = None

def init_db_if_needed(dbDefinitions, flowDefinition):
    global mutexDB

    mutexDB.acquire()

    for i in range(len(flowDefinition["FlowRef"])):
        if dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
            dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)

            if dbDefinitions[u"serverType"] == 'sqlLite':
                # table General definition flow, sqlite
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_devices (FlowDevicesId integer primary key, FlowDevicesRef varchar(50) NOT NULL, FlowDevicesCorrFactor float NOT NULL, FlowDevicesPortSensor int NOT NULL, FlowDevicesIsSlowPulse boolean NOT NULL);")
                # Ajust to flow, sqlite
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_correction (FlowCorrectionId integer primary key, FlowCorrectionDevicesFK integer NOT NULL, FlowCorrectionDateTime datetime default current_timestamp, FlowCorrectionRealReading double NOT NULL, FlowCorrectionDiffLitters double NOT NULL, FOREIGN KEY (FlowCorrectionDevicesFK) REFERENCES flow_devices(FlowDevicesId));")
                # Flow reading
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_reading (FlowReadingId integer primary key, FlowReadingFK integer NOT NULL, FlowReadingRate double NOT NULL, FlowReadingAccum double NOT NULL, FlowReadingDate datetime default current_timestamp, FOREIGN KEY (FlowReadingFK) REFERENCES flow_devices(FlowDevicesId));")
            elif dbDefinitions[u"serverType"] == 'mySQL':
                # table General definition flow, mysql
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_devices (FlowDevicesId int NOT NULL AUTO_INCREMENT, FlowDevicesRef varchar(50) NOT NULL, FlowDevicesCorrFactor float NOT NULL, FlowDevicesPortSensor int NOT NULL, FlowDevicesIsSlowPulse boolean NOT NULL, PRIMARY KEY (FlowDevicesId));")
                # Ajust to flow, mysql
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_correction(FlowCorrectionId int NOT NULL AUTO_INCREMENT, FlowCorrectionDevicesFK int NOT NULL, FlowCorrectionDateTime datetime NOT NULL DEFAULT NOW(), FlowCorrectionRealReading double NOT NULL, FlowCorrectionDiffLitters double NOT NULL, PRIMARY KEY (FlowCorrectionId), FOREIGN KEY (FlowCorrectionDevicesFK) REFERENCES flow_devices(FlowDevicesId));")
                # Flow reading
                curDBLog.execute("CREATE TABLE IF NOT EXISTS flow_reading (FlowReadingId int NOT NULL AUTO_INCREMENT, FlowReadingFK int NOT NULL, FlowReadingRate double NOT NULL, FlowReadingAccum double NOT NULL, FlowReadingDate datetime NOT NULL DEFAULT NOW(), PRIMARY KEY (FlowReadingId), FOREIGN KEY (FlowReadingFK) REFERENCES flow_devices(FlowDevicesId));")

    mutexDB.release()

def check_and_add_flow(dbDefinitions, flowRef : str, port : int, correctionFActor : float, slowPulse : bool):
    global mutexDB

    mutexDB.acquire()

    if not dbDefinitions[u"serverType"] == 'fromFile':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)

        idFlowDevice = 0
        sqlGet = "SELECT FlowDevicesId FROM flow_devices WHERE FlowDevicesRef = '"+ flowRef +"';"
        curDBLog.execute(sqlGet)
        for currData in curDBLog:
            if len(currData) == 1:
                try:
                    idFlowDevice = int(currData[0])
                except:
                    pass

        if idFlowDevice == 0:
            sqlAdd = "INSERT INTO flow_devices (FlowDevicesRef, FlowDevicesCorrFactor, FlowDevicesPortSensor, FlowDevicesIsSlowPulse) "
            sqlAdd = sqlAdd +"VALUES ('"+ flowRef +"', "+ str(correctionFActor) +", "+ str(port) +", "+ str(slowPulse) +");"
            curDBLog.execute(sqlAdd)
            conDB.commit()

    mutexDB.release()

def add_new_register(dbDefinitions, flowRef : str, flowRate : float, flowAccum : float, dateTimeReg : datetime.date):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        fileTest = u"./data/flow_reading_"+ flowRef + str(dateTimeReg.year) +"_"+ str(dateTimeReg.month) +"_"+ str(dateTimeReg.day) +".txt"
        with open(fileTest, "a") as f:
            f.write(str(flowRate) +"|"+ str(flowAccum) +"|"+ str(dateTimeReg) +"\n")
            f.close()
    else:
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        
        # GET id from flow
        idFlowDevice = 0
        sqlGet = "SELECT FlowDevicesId FROM flow_devices WHERE FlowDevicesRef = '"+ flowRef +"';"
        curDBLog.execute(sqlGet)
        for currData in curDBLog:
            if len(currData) == 1:
                try:
                    idFlowDevice = int(currData[0])
                except:
                    pass
        
        if idFlowDevice > 0:
            sqlAdd = "INSERT INTO flow_reading (FlowReadingFK, FlowReadingRate, FlowReadingAccum, FlowReadingDate) "
            sqlAdd = sqlAdd + "VALUES ("+ str(idFlowDevice) +", "+ str(flowRate) +", "+ str(flowAccum) +", '"+ dateTimeReg.strftime("%Y-%m-%d %H:%M:%S") +"');"
            curDBLog.execute(sqlAdd)
            conDB.commit()

    mutexDB.release()

def get_last_accum_value(dbDefinitions, flowDefinition):
    global mutexDB

    listAccumFlowL = {}

    mutexDB.acquire()

    connect2DB = False

    for i in range(len(flowDefinition["FlowRef"])):
        lastFlow = 0
        lastAccum = 0

        if dbDefinitions[u"serverType"] == 'fromFile':
            dayTest = datetime.now()

            while dayTest.year < 2022:
                fileTest = u"./data/flow_reading_"+ flowDefinition["FlowRef"][i] + str(dayTest.year) +"_"+ str(dayTest.month) +"_"+ str(dayTest.day) +".txt"

                if os.path.exists(fileTest):
                    # read file until the end to read acumulate values
                    with open(fileTest) as fp:
                        line = fp.readline()
                        while line:
                            listSplit = line.split('|')
                            if len(listSplit) == 3:
                                try:
                                    lastFlow = float(listSplit[0])
                                    lastAccum = float(listSplit[1])
                                except:
                                    pass

                            line = fp.readline()
                    break
                else:
                    dayTest = dayTest - timedelta(days=-1)
        else:
            if not connect2DB:
                dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
                connect2DB = True
            if dbIsOpen:
                sqlGet = "SELECT FlowReadingRate, FlowReadingAccum FROM flow_reading, flow_devices WHERE FlowReadingFK = FlowDevicesId AND FlowDevicesRef = '"+ flowDefinition["FlowRef"][i] +"' AND FlowReadingDate ="
                sqlGet = sqlGet + "(SELECT MAX(FlowReadingDate) FROM flow_reading, flow_devices WHERE FlowReadingFK = FlowDevicesId AND FlowDevicesRef = '"+ flowDefinition["FlowRef"][i] +"');"
                curDBLog.execute(sqlGet)
                for currData in curDBLog:
                    if len(currData) == 2:
                        lastFlow = float(currData[0])
                        lastAccum = float(currData[1])

        listAccumFlowL["F-" + flowDefinition["FlowRef"][i]] = {"FlowRate": lastFlow, "AccumFlow": lastAccum}

    mutexDB.release()

    return listAccumFlowL

def add_valve_flow(dbDefinitions, valveId : int, flowRate : float, flowAccum : float, dateTimeReg : datetime.date):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        fileTest = u"./data/flow_valve_"+ str(valveId + 1) +"_"+ str(dateTimeReg.year) +"_"+ str(dateTimeReg.month) +"_"+ str(dateTimeReg.day) +".txt"
        with open(fileTest, "a") as f:
            f.write(str(flowRate) +"|"+ str(flowAccum) +"|"+ str(dateTimeReg) +"\n")
            f.close()
    else:
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            if dbDefinitions[u"serverType"] == 'sqlLite':
                sqlCreate = "CREATE TABLE IF NOT EXISTS valve_reading (ValveRreadingId integer primary key, ValveRreadingFK int NOT NULL, ValveRreadingDateTime datetime default current_timestamp, ValveRreadingAccum double NOT NULL, ValveRreadingFlow double NOT NULL, PRIMARY KEY (ValveRreadingId), FOREIGN KEY (ValveRreadingFK) REFERENCES valves_id(ValveId));"
            else:
                sqlCreate = "CREATE TABLE IF NOT EXISTS valve_reading (ValveRreadingId int NOT NULL AUTO_INCREMENT, ValveRreadingFK int NOT NULL, ValveRreadingDateTime datetime NOT NULL DEFAULT NOW(), ValveRreadingAccum double NOT NULL, ValveRreadingFlow double NOT NULL, PRIMARY KEY (ValveRreadingId), FOREIGN KEY (ValveRreadingFK) REFERENCES valves_id(ValveId));"

            curDBLog.execute(sqlCreate)
            conDB.commit()

            # save value from call
            sqlAdd = "INSERT INTO valve_reading (ValveRreadingFK, FlowReadingRate, FlowReadingAccum, FlowReadingDate) VALUES ("+ str(valveId + 1) +", "+ str(flowRate) +", "+ str(flowAccum) +", '"+ dateTimeReg.strftime("%Y-%m-%d %H:%M:%S") +"');"
            curDBLog.execute(sqlCreate)
            conDB.commit()

    mutexDB.release()

def get_last_valve_accum_val(dbDefinitions, valveId : int):
    global mutexDB

    lastAccumVal = 0.0

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        dayTest = datetime.now()

        while dayTest.year < 2022:
            fileTest =u"./data/flow_valve_"+ str(valveId + 1) +"_"+ str(dayTest.year) +"_"+ str(dayTest.month) +"_"+ str(dayTest.day) +".txt"

            if os.path.exists(fileTest):
                # read file until the end to read acumulate values
                with open(fileTest) as fp:
                    line = fp.readline()
                    while line:
                        listSplit = line.split('|')
                        if len(listSplit) == 3:
                            try:
                                lastAccumVal = float(listSplit[1])
                            except:
                                pass

                        line = fp.readline()
                break
            else:
                dayTest = dayTest - timedelta(days=-1)
    else:
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            sqlCnt = "SELECT COUNT(FlowReadingId) as Total FROM flow_reading WHERE FlowReadingFK = "+ str(valveId + 1) +";"
            curDBLog.execute(sqlCnt)
            numberOfReg = 0
            for currData in curDBLog:
                if len(currData) == 1:
                    numberOfReg = int(currData[0])

            if numberOfReg > 0:
                sqlLast = "SELECT MAX(FlowReadingId) as MaxVal FROM flow_reading WHERE FlowReadingFK = "+ str(valveId + 1) +";"
                for currData in curDBLog:
                    if len(currData) == 1:
                        lastAccumVal = float(currData[0])

    mutexDB.release()

    return lastAccumVal
