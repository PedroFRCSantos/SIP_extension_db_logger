from db_logger_core import *

def estimate_number_of_turn_on_by_month(dbDefinitions):
    global mutexDB

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
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
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

def get_list_SIP_reg(numberOfReg, dbDefinitions):
    records = []

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
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
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

    return records
