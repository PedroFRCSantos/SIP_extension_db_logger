
from copy import deepcopy
import math
import calendar
import datetime
import copy

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

    strDateSpace = strDate.split(" ")
    if len(strDateSpace) == 2:
        strDateSplit = strDateSpace[1].split(":")
        valrOut = valrOut + int(strDateSpace[0][:-1]) * 24
    else:
        strDateSplit = strDate.split(":")

    if len(strDateSplit) == 3:
        valrOut = valrOut + float(strDateSplit[0])
        valrOut = valrOut + float(strDateSplit[1]) / 60.0
        valrOut = valrOut + float(strDateSplit[2]) / 60.0 / 60.0

    valrOut = round(valrOut, 4)

    return valrOut

def estimate_valve_turn_on_by_day_entry(dOn, dOff, minDate : datetime, maxDate : datetime, statsPeriod):
    lastDayTest = maxDate + datetime.timedelta(days=1)
    currentDateBegin = copy.deepcopy(minDate)
    currentDateBegin.replace(hour = 0, minute = 0, second = 0, microsecond = 0)

    currentDateEnd = copy.deepcopy(minDate)
    currentDateEnd.replace(hour = 23, minute = 59, second = 59, microsecond = 999999)

    while currentDateBegin < lastDayTest:
        accumTimeSeconds = 0

        if not (dOff < currentDateBegin or dOn > currentDateEnd):
            accumTimeSeconds = accumTimeSeconds + 24 * 60 * 60

        if dOn.year == currentDateBegin.year and dOn.month == currentDateBegin.month and dOn.day == currentDateBegin.day:
            time2Discount = (dOn - currentDateBegin).total_seconds()
            accumTimeSeconds = accumTimeSeconds - time2Discount

        if dOff.year == currentDateBegin.year and dOff.month == currentDateBegin.month and dOff.day == currentDateBegin.day:
            time2Discount = (currentDateEnd - dOff).total_seconds()
            accumTimeSeconds = accumTimeSeconds - time2Discount

        try:
            statsPeriod[str(currentDateBegin.year) + str(currentDateBegin.month).zfill(2) + str(currentDateBegin.day).zfill(2)] = statsPeriod[str(currentDateBegin.year).zfill(2) + str(currentDateBegin.month).zfill(2) + str(currentDateBegin.day).zfill(2)] + accumTimeSeconds
        except:
            statsPeriod[str(currentDateBegin.year) + str(currentDateBegin.month).zfill(2) + str(currentDateBegin.day).zfill(2)] = accumTimeSeconds

        currentDateBegin += datetime.timedelta(days=1)
        currentDateEnd += datetime.timedelta(days=1)

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
            statsMonthOut[str(currentYear) + str(currentMonth).zfill(2)] = statsMonthOut[str(currentYear) + str(currentMonth).zfill(2)] + accumTimeSeconds
        except:
            statsMonthOut[str(currentYear) + str(currentMonth).zfill(2)] = accumTimeSeconds

        currentMonth = currentMonth + 1
        if currentMonth > 12:
            currentMonth = 1
            currentYear = currentYear + 1
