#!/usr/bin/python

# A decorator to use singleton on a class
# http://en.wikipedia.org/wiki/Singleton_pattern#Python_.28using_decorators.29
def singleton(cls):
	instance_container = []
	def getinstance():
		if not len(instance_container):
			instance_container.append(cls())
		return instance_container[0]
	return getinstance

