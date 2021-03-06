# a controller is all the circuits and temperatures (sensors and effectors)
# equipment bytes are 1 and 2, bits 0 - 7

import circuit
import json
import redis
import spreadsheet
import time
from python_example import StatsdClient

gSendStats = True   #  djm True
statsServer = "localhost"
statsPort = 8125

class controller(object):
	def __init__( self, circuitlist ):
		self.circuitlist = circuitlist
		self.watertemp = 70		# deg F
		self.spasettemp = 96		# deg F
		self.poolsettemp = 45		# deg F
		self.airtemp = 70		# deg F
		self.solartemp = 70		# deg F
		self.hash = 0			# for caching
		self.oldhash = 1
		self.responsestart = 0
		self.responseflag = False
		self.pooltime = "00:00"
		self.walltime = "00:00"
		self.r = redis.StrictRedis( host='localhost', port=6379, db=0)
		self.spreadsheet = spreadsheet.Spreadsheet()
		self.password = ''
		if gSendStats == True:
			self.statsclient = StatsdClient( statsServer, statsPort )
		else:
			self.statsclient = None

	def getwallclocktime( self ):
		return self.walltime

	def getpoolclocktime( self ):
		return self.pooltime

	def setwallclocktime( self, t ):
		self.walltime = t

	def setpoolclocktime( self, t ):
		self.pooltime = t

	def setResponseStart( self, t ):
		self.responsestart = t

	def setResponseFlag( self, f):
		self.responseflag = f

	def setpassword( self, pw):
		self.password = pw

	def getpassword( self ):
		return self.password

	def setwatertemp( self, temp ):
		if self.watertemp != temp:
			if gSendStats == True:
				self.statsclient.gauge( "pool.watertemp", temp )
			self.watertemp = temp
			self.updatehash()

	def setspasettemp( self, temp ):
		if self.spasettemp != temp:
			self.spasettemp = temp
			self.updatehash()

	def setpoolsettemp( self, temp ):
		if self.poolsettemp != temp:
			self.poolsettemp = temp
			self.updatehash()

	def setairtemp( self, temp ):
		if self.airtemp != temp:
			if gSendStats == True:
				self.statsclient.gauge( "pool.airtemp", temp )
			self.airtemp = temp
			self.updatehash()

	def setsolartemp( self, temp ):
		if self.solartemp != temp:
			if gSendStats == True:
				self.statsclient.gauge( "pool.solartemp", temp )
			self.solartemp = temp
			self.updatehash()

	def getwatertemp( self ):
		return self.watertemp

	def getspasettemp( self ):
		return self.spasettemp

	def getpoolsettemp( self ):
		return self.poolsettemp

	def getairtemp( self ):
		return self.airtemp

	def getsolartemp( self ):
		return self.solartemp

	def updatehash(self):
		h = 0
		for a in self.circuitlist:
			h += a.getHash()
		h += int(self.solartemp) * 10000
		h += int(self.watertemp) * 1000
		h += int(self.spasettemp) * 100
		h += int(self.poolsettemp) * 50
		h += int(self.airtemp) * 10
		self.hash = h
		return h

	def gethash( self ):
		return self.hash
	
	def appendcircuit( self, c ):
		self.circuitlist.append( c )

	def setcircuit( self, equipbyte, equipbit, val ):
		# find circuit and set to val
		retval = False
		for c in self.circuitlist:
			if c.match( equipbyte, equipbit ):
				#if val == 1:
				#	print "setting %s to %s" % (c.getname, val)
				c.setState( val )
				self.updatehash()
				retval = True
				break
		return retval

	def getcircuitlist( self ):
		return self.circuitlist

	def getcircuitnumstate( self, circuitnum ):
		for c in self.circuitlist:
			if c.getNumber() == circuitnum:
				return c.getState()
		return -1	# not found

	# save to redis as a hash with values
	def save( self ):
		if self.responseflag == True:
			t = (time.time() - self.responsestart) * 1000   # for ms
			self.responseflag = False
			if gSendStats == True:
				self.statsclient.timing( "pool.cmdresponse", t )
		# only save if we have to
		if self.oldhash == self.hash:
			return False
		else:
			d = {}
			for c in self.circuitlist:
				d[c.getNumber()] = json.dumps(c.todict())
			d["airtemp"] = self.airtemp
			d["solartemp"] = self.solartemp
			d["watertemp"] = self.watertemp
			d["spasettemp"] = self.spasettemp
			d["poolsettemp"] = self.poolsettemp
			d["hash"] = self.hash
			d["pooltime"] = self.pooltime
			d["walltime"] = self.walltime
			# pool is the redis hash key, so you can do a 
			# redis-cli hgetall pool
			# to see all the data stored in redis
			self.r.hmset( "pool", d )
			self.spreadsheet.store(d)
			self.oldhash = self.hash
			# we are never going to save the password, only
			# the set_password.py script will do this

	def load( self ):
		# get dictionary from redis
		d = self.r.hgetall( "pool" )
		# and sort it all out
		self.circuitlist = []		# empty
		for k in d.keys():
			if k == "hash":
				self.hash = d[k]
			elif k == "pooltime":
				self.pooltime = d[k]
			elif k == "walltime":
				self.walltime = d[k]
			elif k == "airtemp":
				self.airtemp = d[k]
			elif k == "solartemp":
				self.solartemp = d[k]
			elif k == "watertemp":
				self.watertemp = d[k]
			elif k == "spasettemp":
				self.spasettemp = d[k]
			elif k == "poolsettemp":
				self.poolsettemp = d[k]
			elif k == "0" or k == "1" or k == "2" or k == "3" or \
				k == "4" or k == "5" or k == "6" or k == "7" or \
				k == "8" or k == "9" or k == "10" or k == "11" or \
				k == "12" or k == "13" or k == "14" or k == "15" or \
				k == "16" or k == "17" or k == "18":	# circuit
				# decode json sting
				cdict = json.loads(d[k])				
				self.circuitlist.append( circuit.circuit(k,
								cdict["name"],
								cdict["byte"],
								cdict["bit"],
								cdict["value"] ))
			elif k =="password":
				self.password = d[k]
			else:
				#print "bad key %s found in load" % k
				a = 1				
		self.oldhash = self.hash

