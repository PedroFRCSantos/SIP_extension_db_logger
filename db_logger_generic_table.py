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
            sqlStrutcture = "SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            sqlStrutcture = sqlStrutcture + "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '"+  tableName +"'"

            curDBLog.execute(sqlStrutcture)
            recordsFK = curDBLog.fetchall()
            for recordFK in recordsFK:
                if recordFK[3] == 'valves_id' and recordFK[4] == 'ValveId':
                    fkFieldName = recordFK[1]

            if (len(fkFieldName) > 0 and valveId > 0) or (len(fkFieldName) == 0 and valveId <= 0):
                # get table structure
                sqlStrutcture = "Describe " + tableName
                curDBLog.execute(sqlStrutcture)
                recordsRaw = curDBLog.fetchall()

                sqlAdd = "INSERT INTO "+ tableName +" ("
                sqlData = "VALUES ("
                isFirst = True
                indx = 0
                for currData in recordsRaw:
                    if currData[3] == 'PRI' and currData[5] == 'auto_increment':
                        pass
                    elif currData[0] == fkFieldName:
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + fkFieldName
                        sqlData = sqlData + str(valveId)
                    elif currData[1] == 'date' or currData[1] == 'datetime' or currData[1] == 'time' or currData[1].lower() == 'TEXT'.lower():
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + currData[0]
                        sqlData = sqlData + "'" + str(listData[indx]) + "'"

                        indx = indx + 1
                    else:
                        if isFirst:
                            isFirst = False
                        else:
                            sqlAdd = sqlAdd + ","
                            sqlData = sqlData + ","
                        sqlAdd = sqlAdd + currData[0]
                        sqlData = sqlData + str(listData[indx])

                        indx = indx + 1

                sqlAdd = sqlAdd + ") "
                sqlData = sqlData + ");"

                curDBLog.execute(sqlAdd + sqlData)
                conDB.commit()

    mutexDB.release()


