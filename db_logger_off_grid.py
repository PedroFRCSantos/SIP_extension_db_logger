from db_logger_core import *
from db_logger_aux_fun import *
from datetime import datetime, timedelta

import gv  # Get access to SIP's settings, gv = global variables

import os

def add_db_values(dbDefinitions, offGridDefinition, dataOffGrind):
    global mutexDB

    mutexDB.acquire()

    # check if table stuture is valid
    if dbDefinitions[u"serverType"] == 'fromFile':
        fileTest = u"./data/off_grid_reading_"+ dataOffGrind["OffGridRef"] +"_"+ str(dataOffGrind["DateTime"].year) +"_"+ str(dataOffGrind["DateTime"].month) +"_"+ str(dataOffGrind["DateTime"].day) +".txt"
        with open(fileTest, "a") as f:
            f.write(str(dataOffGrind["DateTime"]) +"|" + os.linesep)

            f.write("SOLAR|" + str(offGridDefinition[dataOffGrind["OffGridRef"]]["SolarN"]) + os.linesep)
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["SolarN"]):
                f.write("SOLAR"+ str(i + 1) +"|")
                f.write(str(dataOffGrind["VSOLAR" + str(i + 1)]) +"|"+ str(dataOffGrind["CSOLAR" + str(i + 1)]) +"|"+ str(dataOffGrind["ESOLAR" + str(i + 1)]))
                f.write(os.linesep)

            f.write("WIND|" + str(offGridDefinition[dataOffGrind["OffGridRef"]]["WindN"]) + os.linesep)
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["WindN"]):
                f.write("WIND"+ str(i + 1) +"|")
                f.write(str(dataOffGrind["VWIND" + str(i + 1)]) +"|"+ str(dataOffGrind["CWIND" + str(i + 1)]) +"|"+ str(dataOffGrind["EWIND" + str(i + 1)]))
                f.write(os.linesep)

            f.write("GENTOTAL|" + str(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalGen"]) + os.linesep)
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalGen"]):
                f.write("GENTOTAL"+ str(i + 1) +"|")
                f.write(str(dataOffGrind["VGENTOTAL" + str(i + 1)]) +"|"+ str(dataOffGrind["CGENTOTAL" + str(i + 1)]) +"|"+ str(dataOffGrind["EGENTOTAL" + str(i + 1)]))
                f.write(os.linesep)

            f.write("TotalConsp|" + str(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalConspN"]) + os.linesep)
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalConspN"]):
                f.write("TotalConsp"+ str(i + 1) +"|")
                f.write(str(dataOffGrind["VCONSP" + str(i + 1)]) +"|"+ str(dataOffGrind["CCONSP" + str(i + 1)]) +"|"+ str(dataOffGrind["ECONSP" + str(i + 1)]))
                f.write(os.linesep)

            f.close()
    else:
        dbIsOpen, conDB, curDBLog = load_connect_2_DB(dbDefinitions[u"ipPathDB"], dbDefinitions[u"userName"], dbDefinitions[u"passWord"], dbDefinitions[u"dbName"], dbDefinitions)
        if dbIsOpen:
            # create table if not exists with names of off-grid
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_name (OffGridNameId int NOT NULL AUTO_INCREMENT, OffGridNameVal varchar(50) NOT NULL, PRIMARY KEY (OffGridNameId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_name (OffGridNameId integer primary key, OffGridNameVal varchar(50) NOT NULL);"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # add new reading, master table for reading
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_reading (OffGridReadingId int NOT NULL AUTO_INCREMENT, OffGridReadingFK int NOT NULL, OffGridReadingDate datetime NOT NULL DEFAULT NOW(), PRIMARY KEY (OffGridReadingId), FOREIGN KEY (OffGridReadingFK) REFERENCES off_grid_name(OffGridNameId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_reading (OffGridReadingId integer primary key, OffGridReadingFK integer NOT NULL, OffGridReadingDate datetime default current_timestamp, FOREIGN KEY (OffGridReadingFK) REFERENCES off_grid_name(OffGridNameId));"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # create table off-grid reading SOLAR
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_solar (OffGridReadSolarId int NOT NULL AUTO_INCREMENT, OffGridReadSolarFK int NOT NULL, OffGridReadSolarN int NOT NULL, OffGridReadSolarV double NOT NULL, OffGridReadSolarA double NOT NULL, OffGridReadSolarE double NOT NULL, PRIMARY KEY (OffGridReadSolarId), FOREIGN KEY (OffGridReadSolarFK) REFERENCES off_grid_reading(OffGridReadingId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_solar (OffGridReadSolarId integer primary key, OffGridReadSolarFK integer NOT NULL, OffGridReadSolarN integer NOT NULL, OffGridReadSolarV double NOT NULL, OffGridReadSolarA double NOT NULL, OffGridReadSolarE double NOT NULL, FOREIGN KEY (OffGridReadSolarFK) REFERENCES off_grid_reading(OffGridReadingId));"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # create table off-grid reading WIND
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_wind (OffGridReadWindId int NOT NULL AUTO_INCREMENT, OffGridReadWindFK int NOT NULL, OffGridReadWindN int NOT NULL, OffGridReadWindV double NOT NULL, OffGridReadWindA double NOT NULL, OffGridReadWindE double NOT NULL, PRIMARY KEY (OffGridReadWindId), FOREIGN KEY (OffGridReadWindFK) REFERENCES off_grid_reading(OffGridReadingId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_wind (OffGridReadWindId integer primary key, OffGridReadWindFK integer NOT NULL, OffGridReadWindN integer NOT NULL, OffGridReadWindV double NOT NULL, OffGridReadWindA double NOT NULL, OffGridReadWindE double NOT NULL, FOREIGN KEY (OffGridReadWindFK) REFERENCES off_grid_reading(OffGridReadingId));"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # create table off-grid reading Total-Gen
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_total_gen (OffGridReadTGenId int NOT NULL AUTO_INCREMENT, OffGridReadTGenFK int NOT NULL, OffGridReadTGenN int NOT NULL, OffGridReadTGenV double NOT NULL, OffGridReadTGenA double NOT NULL, OffGridReadTGenE double NOT NULL, PRIMARY KEY (OffGridReadTGenId), FOREIGN KEY (OffGridReadTGenFK) REFERENCES off_grid_reading(OffGridReadingId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_total_gen (OffGridReadTGenId integer primary key, OffGridReadTGenFK integer NOT NULL, OffGridReadTGenN integer NOT NULL, OffGridReadTGenV double NOT NULL, OffGridReadTGenA double NOT NULL, OffGridReadTGenE double NOT NULL, FOREIGN KEY (OffGridReadTGenFK) REFERENCES off_grid_reading(OffGridReadingId));"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # create table off-grid reading consuption
            if dbDefinitions[u"serverType"] == 'mySQL':
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_total_consp (OffGridReadTConsId int NOT NULL AUTO_INCREMENT, OffGridReadTConsFK int NOT NULL, OffGridReadTConsN int NOT NULL, OffGridReadTConsV double NOT NULL, OffGridReadTConsA double NOT NULL, OffGridReadTConsE double NOT NULL, PRIMARY KEY (OffGridReadTConsId), FOREIGN KEY (OffGridReadTConsFK) REFERENCES off_grid_reading(OffGridReadingId));"
            else:
                sqlAdd = "CREATE TABLE IF NOT EXISTS off_grid_read_total_consp (OffGridReadTConsId integer primary key, OffGridReadTConsFK integer NOT NULL, OffGridReadTConsN integer NOT NULL, OffGridReadTConsV double NOT NULL, OffGridReadTConsA double NOT NULL, OffGridReadTConsE double NOT NULL, FOREIGN KEY (OffGridReadTConsFK) REFERENCES off_grid_reading(OffGridReadingId));"
            curDBLog.execute(sqlAdd)
            conDB.commit()

            # check if off-grid reference exists
            id2OffGrid = -1
            while True:
                sqlCheck = "SELECT OffGridNameId FROM off_grid_name WHERE OffGridNameVal = '"+ dataOffGrind["OffGridRef"] +"';"
                curDBLog.execute(sqlCheck)
                recordsField = curDBLog.fetchall()
                if len(recordsField) > 0:
                    id2OffGrid = int(recordsField[0][0])
                    break
                else:
                    sqlCheck = "INSERT INTO off_grid_name (OffGridNameVal) VALUES ('"+ dataOffGrind["OffGridRef"] +"');"
                    curDBLog.execute(sqlCheck)
                    conDB.commit()

            # add new readinf to table
            sqlNewReg = "INSERT INTO off_grid_reading (OffGridReadingFK, OffGridReadingDate) "
            sqlNewReg = sqlNewReg +"VALUES ("+ str(id2OffGrid) +", '"+ dataOffGrind["DateTime"].strftime("%Y-%m-%d %H:%M:%S") +"');"
            curDBLog.execute(sqlNewReg)
            conDB.commit()

            # get id of register
            sqlGet = "SELECT MAX(OffGridReadingId) as LastId FROM off_grid_reading;"
            lastIdRegister = -1
            curDBLog.execute(sqlGet)
            recordsField = curDBLog.fetchall()
            if len(recordsField) > 0:
                lastIdRegister = int(recordsField[0][0])

            if lastIdRegister <= 0:
                mutexDB.release()
                return

            # save solar sensors
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["SolarN"]):
                sqlAdd = "INSERT INTO off_grid_read_solar (OffGridReadSolarFK, OffGridReadSolarN, OffGridReadSolarV, OffGridReadSolarA, OffGridReadSolarE) "
                sqlAdd = sqlAdd +"VALUES ("+ str(lastIdRegister) +", "+ str(i + 1) +", "+ dataOffGrind["VSOLAR" + str(i + 1)] +", "+ dataOffGrind["CSOLAR" + str(i + 1)] +", "+ dataOffGrind["ESOLAR" + str(i + 1)] +");"
                curDBLog.execute(sqlAdd)

            # save wind sensors
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["WindN"]):
                sqlAdd = "INSERT INTO off_grid_read_wind (OffGridReadWindFK, OffGridReadWindN, OffGridReadWindV, OffGridReadWindA, OffGridReadWindE) "
                sqlAdd = sqlAdd +"VALUES ("+ str(lastIdRegister) +", "+ str(i + 1) +", "+ dataOffGrind["VWIND" + str(i + 1)] +", "+ dataOffGrind["CWIND" + str(i + 1)] +", "+ dataOffGrind["EWIND" + str(i + 1)] +");"
                curDBLog.execute(sqlAdd)

            # save total gen
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalGen"]):
                sqlAdd = "INSERT INTO off_grid_read_total_gen (OffGridReadTGenFK, OffGridReadTGenN, OffGridReadTGenV, OffGridReadTGenA, OffGridReadTGenE) "
                sqlAdd = sqlAdd +"VALUES ("+ str(lastIdRegister) +", "+ str(i + 1) +", "+ dataOffGrind["VGENTOTAL" + str(i + 1)] +", "+ dataOffGrind["CGENTOTAL" + str(i + 1)] +", "+ dataOffGrind["EGENTOTAL" + str(i + 1)] +");"
                curDBLog.execute(sqlAdd)

            # save total consuption
            for i in range(offGridDefinition[dataOffGrind["OffGridRef"]]["TotalConspN"]):
                sqlAdd = "INSERT INTO off_grid_read_total_consp (OffGridReadTConsFK, OffGridReadTConsN, OffGridReadTConsV, OffGridReadTConsA, OffGridReadTConsE) "
                sqlAdd = sqlAdd +"VALUES ("+ str(lastIdRegister) +", "+ str(i + 1) +", "+ dataOffGrind["VCONSP" + str(i + 1)] +", "+ dataOffGrind["CCONSP" + str(i + 1)] +", "+ dataOffGrind["ECONSP" + str(i + 1)] +");"
                curDBLog.execute(sqlAdd)

            conDB.commit()

    mutexDB.release()

def change_off_grid_station_name(dbDefinitions, oldName, newName):
    if dbDefinitions[u"serverType"] == 'fromFile':
        pass
    else:
        pass
