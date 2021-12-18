from datetime import datetime

def avg(total, count):
	if not total:
		return 0
	if not count:
		return 0
	return round(total / count, 1) 

def pct(total, count):
	if not total:
		return 0
	if not count:
		return 0

	if total == count:
		return "1.000"
	return str(round(total / count, 3))[1:].ljust(4,'0')

def today():
    return datetime.today().strftime("%Y-%m-%d")

def small_date(date):
        #2021-11-23T00:00:00
        datetime_object = datetime.strptime(date,"%Y-%m-%dT00:00:00")
        if datetime_object.year == datetime.today().year:
            return datetime_object.strftime("%-m/%-d")
        else:
            return datetime_object.strftime("%-m/%-d/%y")
def short_date( date):
    #2021-11-23T00:00:00
    datetime_object = datetime.strptime(date,"%Y-%m-%dT00:00:00")
    if datetime_object.year == datetime.today().year:
        return datetime_object.strftime("%b %-d")
    else:
        return datetime_object.strftime("%b %-d, %Y")

def schedule_date( date):
    datetime_object = datetime.strptime(date,"%b %d, %Y")
    return datetime_object.strftime("%a %-m/%-d")

def h2h_date( date):
    datetime_object = datetime.strptime(date,"%Y-%m-%d")
    return datetime_object.strftime("%-m/%-d")

def shorten(word, length):
    if len(word) <= length + 1:
        return word
    return f"{word[:length]}."

def opp_from_matchup(matchup):
    if '@' in matchup:
        return matchup[matchup.index('@'):]
    return matchup[matchup.index('vs.'):]