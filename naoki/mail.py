#!/usr/bin/python

import email.mime.multipart
import email.mime.text
import logging
import os
import smtplib

from constants import *

def report_error(package):
	# Do not send a report if no recipient is configured
	if not config["error_report_recipient"]:
		return

	try:
		connection = smtplib.SMTP(config["smtp_server"])
		#connection.set_debuglevel(1)

		if config["smtp_user"] and config["smtp_password"]:
			connection.login(config["smtp_user"], config["smtp_password"])

	except smtplib.SMTPConnectError, e:
		logging.error("Could not establish a connection to the smtp server: %s" % e)
		return
	except smtplib.SMTPAuthenticationError, e:
		logging.error("Could not successfully login to the smtp server: %s" % e)
		return

	msg = email.mime.multipart.MIMEMultipart()
	msg["From"] = config["error_report_sender"]
	msg["To"] = config["error_report_recipient"]
	msg["Subject"] = config["error_report_subject"] % package.all
	msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'

	body = """\
The package %(name)s had a difficulty to build itself.
This email will give you a short report about the error.

Package information:
  Name    : %(name)s - %(summary)s
  Version : %(version)s
  Release : %(release)s

  This package in maintained by %(maintainer)s.


A detailed logfile is attached.

Sincerely,
    Naoki
	""" % {
		"name" : package.name,
		"summary" : package.summary,
		"version" : package.version,
		"release" : package.release,
		"maintainer" : package.maintainer,
	}

	msg.attach(email.mime.text.MIMEText(body))

	# Read log and append it to mail
	loglines = []
	if os.path.exists(package.logfile):
		f = open(package.logfile)
		line = f.readline()
		while line:
			line = line.rstrip()
			if line.endswith(LOG_MARKER):
				# Reset log
				loglines = []

			loglines.append(line)
			line = f.readline()

		f.close()

	if not loglines:
		loglines = ["Logfile wasn't found."]

	log = email.mime.text.MIMEText("\n".join(loglines), _subtype="plain")
	log.add_header('Content-Disposition', 'attachment',
		filename="%s.log" % package.id)
	msg.attach(log)

	try:
		connection.sendmail(config["error_report_sender"],
			config["error_report_recipient"], msg.as_string())
	except Exception, e:
		logging.error("Could not send error report: %s: %s" % (e.__class__.__name__, e))
		return

	connection.quit()
