import gspread
import time

from oauth2client.service_account import ServiceAccountCredentials

class Spreadsheet(object):
  def __init__(self):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    self.credentials = ServiceAccountCredentials.from_json_keyfile_name('cred.json', scope)
    self.timeoflast = None

  def store(self, d):
    if self.timeoflast is not None and time.time() - self.timeoflast < 3600:
      print "Not writing, too recent"
      return
    tod = time.strftime("=DATEVALUE(\"%m/%d/%Y\") + TIMEVALUE(\"%H:%M\")")
    values = [tod, d["watertemp"], d["airtemp"], d["solartemp"]]
    print "About to write %s" % values
    gc = gspread.authorize(self.credentials)
    sheet = gc.open("Pool Temperature").sheet1
    sheet.insert_row(values, index=2, value_input_option='USER_ENTERED')
    print "Wrote values to spreadsheet"
    self.timeoflast = time.time()
