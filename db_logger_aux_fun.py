
import math

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

def estimate_compose_dif_date_time_sec(diffSeconds):
    numberOfDay = math.floor(diffSeconds / (60*60*24))
    numberOfHour = math.floor((diffSeconds - numberOfDay *60*60*24) / (60*60))
    numberOfMinute = math.floor((diffSeconds - numberOfDay *60*60*24 - numberOfHour*60*60) / 60)
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
        valrOut = valrOut + float(strDateSplit[2]) / 60.0 / 60.0

    valrOut = round(valrOut, 4)

    return valrOut
