from db_logger_core import *
import os

def create_generic_table(tableName, listElements, dbDefinitions):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        if os.path.exists(u"./data/db_logger_sip_"+ tableName +".txt"):
            # write struture
            fileNewDB = open(u"./data/db_logger_sip_"+ tableName +"_structure.txt", 'w')
            for key in listElements:
                fileNewDB.write(key +"->" + listElements[key]  + "\n")
            fileNewDB.close()
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            sqlCreate = "CREATE TABLE IF NOT EXISTS "+ tableName +" ("
            if dbDefinitions[u"serverType"] == 'sqlLite':
                sqlCreate = sqlCreate + tableName +"Id integer primary key"
            else:
                sqlCreate = sqlCreate + tableName +"Id int NOT NULL AUTO_INCREMENT"

            valveFK = False
            valveFKName = ""

            for key in listElements:
                if listElements[key] == "valve":
                    valveFK = True
                    sqlCreate = sqlCreate +", "+ key + " int NOT NULL"
                    valveFKName = key
                elif listElements[key] == "int" or listElements[key] == "double" or listElements[key] == "TEXT":
                    sqlCreate = sqlCreate +", "+ key + " "+ listElements[key] +" NOT NULL"
                elif listElements[key] == "date" or listElements[key] == "datetime":
                    if dbDefinitions[u"serverType"] == 'sqlLite':
                        sqlCreate = sqlCreate + ", " + key +" "+ listElements[key] +" default current_timestamp"
                    else:
                        sqlCreate = sqlCreate + ", " + key +" "+ listElements[key] +" NOT NULL DEFAULT NOW()"

            sqlCreate = sqlCreate + ", PRIMARY KEY("+ tableName +"Id)"
            if valveFK:
                sqlCreate = sqlCreate + ", FOREIGN KEY ("+ valveFKName +") REFERENCES valves_id(ValveId)"
            sqlCreate = sqlCreate + ");"
            curDBLog.execute(sqlCreate)

    mutexDB.release()

def change_table_name(tableOldName, tableNewName, dbDefinitions):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        if os.path.exists(u"./data/db_logger_sip_"+ tableOldName +".txt") and os.path.exists(u"./data/db_logger_sip_"+ tableOldName +"_structure.txt", 'w'):
            os.rename(u"./data/db_logger_sip_"+ tableOldName +".txt", u"./data/db_logger_sip_"+ tableNewName +".txt")
            os.rename(u"./data/db_logger_sip_"+ tableOldName +"_structure.txt", u"./data/db_logger_sip_"+ tableNewName +"_structure.txt")
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlChange = "RENAME TABLE "+ tableOldName +" TO "+ tableNewName +";"
            else:
                sqlChange = "ALTER TABLE "+ tableOldName +" RENAME TO "+ tableNewName +";"
            curDBLog.execute(sqlChange)

    mutexDB.release()

def check_if_table_exists(tableName, dbDefinitions):
    global mutexDB

    tableExits = False

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        tableExits = os.path.exists(u"./data/"+ tableName +".txt")
    else:
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)

        if dbDefinitions[u"serverType"] == 'sqlLite':
            sqlCheckTable = "SELECT count(*) as Total FROM information_schema.tables WHERE table_name = \'"+ tableName +"\' LIMIT 1"
        elif dbDefinitions[u"serverType"] == 'mySQL':
            sqlCheckTable = "SELECT count(*) as Total FROM sqlite_master WHERE type='table' AND name=\'"+ tableName +"\';"

        curDBLog.execute(sqlCheckTable)
        recordsRaw = curDBLog.fetchall()

        for currData in recordsRaw:
            if currData[0] == "1":
                tableExits = True

    mutexDB.release()

    return tableExits

def add_date_generic_table(tableName, listData, dbDefinitions, valveId = -1):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        if os.path.exists(u"./data/db_logger_sip_"+ tableName +".txt"):
            # read struture
            fileStrture = open(u"./data/db_logger_sip_"+ tableName +"_structure.txt", 'r')
            Lines = fileStrture.readlines()
            indx = 0
            indxDate = -1
            indxDateTime = -1
            for line in Lines:
                splitData = line.split("->")

                if splitData[1] == 'date' or splitData[1] == 'datetime':
                    if splitData[1] == 'date':
                        indxDate = indx
                    elif splitData[1] == 'datetime':
                        indxDateTime = indx
                    indx = indx + 1
                    continue

                if len(splitData) != 2:
                    mutexDB.release()
                    return

                if (splitData[1] == 'int' and not isinstance(listData[indx], int)) or (splitData[1] == 'float' and not isinstance(listData[indx], float)):
                    mutexDB.release()
                    return

                indx = indx + 1

            # write register to DB
            today = datetime.date.today()
            fileAdd = open(u"./data/db_logger_sip_"+ tableName +str(today.year) +"_"+ str(today.month) +".txt", 'r')

            fileAdd.write('#BEGIN\n')
            indx = 0

            for currData in listData:
                # other type of data
                if indx > 0:
                    fileAdd.write("###\n")
                    fileAdd.write(str(currData) +"\n")

                # if need to add time
                if (indxDate == 0 or indxDate == indx + 1) and (indxDateTime == 0 or indxDateTime == indx + 1):
                    indx = indx + 1
                    today = datetime.now()
                    if indxDate == 0 or indxDate == indx + 1:
                        fileAdd.write(str(today.year) + str(today.month) + str(today.day)+"\n")
                    else:
                        fileAdd.write(today.strftime("%d/%m/%Y %H:%M:%S") +"\n")
                    if indx > 0:
                        fileAdd.write("###\n")

                indx = indx + 1
            fileAdd.write('#END\n')

            fileAdd.close()
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            # get table FK
            fkFieldName = ""
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlStrutcture = "SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                sqlStrutcture = sqlStrutcture + "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '"+  tableName +"'"

                curDBLog.execute(sqlStrutcture)
                recordsFK = curDBLog.fetchall()
                for recordFK in recordsFK:
                    if recordFK[3] == 'valves_id' and recordFK[4] == 'ValveId':
                        fkFieldName = recordFK[1]
            else:
                sqlStrutcture = "PRAGMA foreign_key_list('" + tableName + "');"

                curDBLog.execute(sqlStrutcture)
                recordsFK = curDBLog.fetchall()
                for recordFK in recordsFK:
                    if recordFK[2] == 'valves_id' and recordFK[4] == 'ValveId':
                        fkFieldName = recordFK[3]

            if (len(fkFieldName) > 0 and valveId > 0) or (len(fkFieldName) == 0 and valveId <= 0):
                # get table structure
                if dbDefinitions[u"serverType"] == 'mySQL':
                    sqlStrutcture = "Describe " + tableName
                else:
                    sqlStrutcture = "PRAGMA table_info('" + tableName + "');"
                curDBLog.execute(sqlStrutcture)
                recordsRaw = curDBLog.fetchall()

                sqlAdd = "INSERT INTO "+ tableName +" ("
                sqlData = "VALUES ("
                isFirst = True
                indx = 0
                indxFieldName = 1
                if dbDefinitions[u"serverType"] == 'mySQL':
                    indxFieldName = 0
                for currData in recordsRaw:
                    if (dbDefinitions[u"serverType"] == 'mySQL' and currData[3] == 'PRI' and currData[5] == 'auto_increment') or \
                       (dbDefinitions[u"serverType"] == 'sqlLite' and currData[2] == 'integer' and currData[5] == '1'):
                        pass
                    elif currData[indxFieldName] == fkFieldName:
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + fkFieldName
                        sqlData = sqlData + str(valveId)
                    elif (dbDefinitions[u"serverType"] == 'mySQL' and (currData[1] == 'date' or currData[1] == 'datetime' or currData[1] == 'time' or currData[1].lower() == 'TEXT'.lower())) or \
                         (dbDefinitions[u"serverType"] == 'sqlLite' and (currData[1] == 'date' or currData[1] == 'datetime' or currData[1] == 'time' or currData[1].lower() == 'TEXT'.lower())):
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + currData[indxFieldName]
                        sqlData = sqlData + "'" + str(listData[indx]) + "'"

                        indx = indx + 1
                    else:
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + currData[indxFieldName]
                        sqlData = sqlData + str(listData[indx])

                        indx = indx + 1

                sqlAdd = sqlAdd + ") "
                sqlData = sqlData + ");"

                curDBLog.execute(sqlAdd + sqlData)
                conDB.commit()

    mutexDB.release()

def change_last_register(tableName, idxNumber, newValue, dbDefinitions):
    global mutexDB

    mutexDB.acquire()

    if dbDefinitions[u"serverType"] == 'fromFile':
        if os.path.exists(u"./data/db_logger_sip_"+ tableName +".txt"):
            # find last file use to save data
            today = datetime.date.today()
            lastYearSave = today.year
            lastMonthSave = today.month
            numberOfDescrement = 240

            while not os.path.exists(u"./data/db_logger_sip_"+ tableName + lastYearSave +"_"+ lastMonthSave +".txt") or numberOfDescrement > 0:
                # Try last month if any register
                lastMonthSave = lastMonthSave - 1
                if lastMonthSave < 1:
                    lastMonthSave = 12
                    lastYearSave = lastYearSave - 1
                numberOfDescrement = numberOfDescrement - 1

            if os.path.exists(u"./data/db_logger_sip_"+ tableName + lastYearSave +"_"+ lastMonthSave +".txt"):
                # Check when last line finish
                fileAdd = open(u"./data/db_logger_sip_"+ tableName + lastYearSave +"_"+ lastMonthSave +".txt", 'r')
                fileAdd.seek(-2, 2)
                tmpString = fileAdd.readline()
                lastSize = len(tmpString)

                setLocIdx = -3
                setLocDocIdx = -2
                while True:
                    fileAdd.seek(setLocIdx, 2)
                    tmpString = fileAdd.readline()
                    curretSize = len(tmpString)
                    if curretSize < lastSize:
                        break
                    else:
                        setLocDocIdx = setLocIdx
                    setLocIdx = setLocIdx - 1

                # Back space number o delete
                fileAdd.seek(setLocDocIdx, 2)
                orginalLine = fileAdd.readline()

                fileAdd.truncate()

                splitLine = orginalLine.split()
                newLine = ""
                idxPart = 0
                isFirst = False
                for partSplit in splitLine:
                    if idxNumber != idxPart:
                        newLine = newLine + partSplit
                    else:
                        newLine = newLine + newValue

                    if isFirst:
                        newLine = newLine + ","
                    else:
                        isFirst = True
                    idxPart = idxPart + 1
    elif dbDefinitions[u"serverType"] == 'sqlLite' or dbDefinitions[u"serverType"] == 'mySQL':
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlStrutcture = "DESCRIBE  "+  tableName +";"
            else:
                sqlStrutcture = "PRAGMA table_info('" + tableName + "');"

            curDBLog.execute(sqlStrutcture)
            recordsField = curDBLog.fetchall()
            curentIdx = -1 # start in -1 discount primary key

            fieldPKName = ""
            fieldNameChange = ""

            for i in range(len(recordsField)):
                if i == idxNumber:
                    if dbDefinitions[u"serverType"] == 'mySQL':
                        fieldNameChange = recordsField[i][0]
                    else:
                        pass
                    # Check type if need ""
                    if (dbDefinitions[u"serverType"] == 'mySQL' and (recordsField[i][1] == 'date' or recordsField[i][1] == 'datetime' or recordsField[i][1] == 'time' or recordsField[i][1].lower() == 'TEXT'.lower())) or \
                        (dbDefinitions[u"serverType"] == 'mySQL' and (recordsField[i]['type'] == 'date' or recordsField[i]['type'] == 'datetime' or recordsField[i]['type'] == 'time' or recordsField[i]['type'].lower() == 'TEXT'.lower())):  
                        newValue = "'"+ newValue + "'"
                elif curentIdx == -1:
                    if dbDefinitions[u"serverType"] == 'mySQL':
                        fieldPKName = recordsField[i][0]
                    else:
                        fieldPKName = recordsField[i][0]
                curentIdx = curentIdx + 1

            sqlIdLast = "SELECT MAX("+ fieldPKName +") as IdMax FROM "+ tableName
            curDBLog.execute(sqlIdLast)
            recordsField = curDBLog.fetchall()
            if len(recordsField) > 0:
                if len(recordsField[0]) > 0:
                    sqlUpdate = "UPDATE "+ tableName + " SET " + fieldNameChange + " = " + newValue + " WHERE " + fieldPKName + " = " + str(recordsField[0][0])
                    curDBLog.execute(sqlUpdate)
                    conDB.commit()

    mutexDB.release()
