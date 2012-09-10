#!/usr/bin/env python

# Requires https://github.com/mrtazz/InstapaperLibrary
from instapaperlib import Instapaper

from readinglistlib import ReadingListReader

# Standard library modules
import argparse
import sys
import os
import re
import datetime
from dateutil.parser import parse

# Configure and consume command line arguments.
ap = argparse.ArgumentParser(description='This script adds your Safari Reading List articles to Instapaper.')
ap.add_argument('-u', '--username', action='store', default='', help='Instapaper username or email.')
ap.add_argument('-p', '--password', action='store', default='', help='Instapaper password (if any).')
ap.add_argument('-v', '--verbose', action='store_true', help='Print article URLs as they are added.')
ap.add_argument('-s', '--syncdate', action='store', default=None, help='Syncronizes links on or after \'Last Fetch\' and \'Date Added\' times. Defaults to reading the last syncronized date (last run date/time) from the file: \'~/.readinglist2instapaper/.lastsyncdate\'. If file not present the syncronize \'from date\' defaults to 1970-01-01 00:00:00.')
args = ap.parse_args()

if '' == args.username:
	# For compatibility with instapaperlib's instapaper.py tool,
	# attempt to read Instapaper username and password from ~/.instapaperrc.
	# (Login pattern modified to accept blank passwords.)
	login = re.compile("(.+?):(.*)")
	try:
		config = open(os.path.expanduser('~/.readinglist2instapaper') + '/.instapaperrc')
		for line in config:
			matches = login.match(line)
			if matches:
				args.username = matches.group(1).strip()
				args.password = matches.group(2).strip()
				break
		if '' == args.username:
			print >> sys.stderr, 'No username:password line found in ~/.readinglist2instapaper/.instapaperrc'
			ap.exit(-1)
	except IOError:
		ap.error('Please specify a username with -u/--username.')

if None == args.syncdate:
	try:
		# Check for last syncdate file, if there is then read it
		lastsyncdateFile = open(os.path.expanduser('~/.readinglist2instapaper') + '/.lastsyncdate')
		lastsyncdateFile.seek(0)
		args.syncdate = lastsyncdateFile.readline()
		print 'lastsyncdate:', args.syncdate
	except IOError:
		print 'File \'~/.readinglist2instapaper/.lastsyncdate\' not found. Using 1970-01-01 00:00:00 as synconize from date.'

# Storing our current time for syncing later.
# Doing it this way could mean a duplicate article is sync'ed, but I'd rather have a dup then loss an article.
print 'Updating ~/.readinglist2instapaper/.lastsyncdate file.'
print 'lastsyncdate before write:', args.syncdate
lastsyncdate = parse(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))
lastsyncdateFile = open(os.path.expanduser('~/.readinglist2instapaper') + '/.lastsyncdate', 'w+')
lastsyncdateFile.write(str(lastsyncdate))
# Paranoia..
lastsyncdateFile.seek(0)
lastsyncdate = lastsyncdateFile.readline()
print 'Using %s as the next syncronized date.' % lastsyncdate

# Log in to the Instapaper API.
instapaper = Instapaper(args.username, args.password)
(auth_status, auth_message) = instapaper.auth()

# 200: OK
# 403: Invalid username or password.
# 500: The service encountered an error.
if 200 != auth_status:
	print >> sys.stderr, auth_message
	ap.exit(-1)

# Get the Reading List items
rlr = ReadingListReader()
articles = rlr.read(
		show = all,
		syncdate = args.syncdate)

for article in articles:

	(add_status, add_message) = instapaper.add_item(article['url'].encode('utf-8'), title=article['title'].encode('utf-8'), selection=article['preview'].encode('utf-8'))
	
	# Debug junk
	lastsyncdate = article['date']
	print "Last syncdate is:", lastsyncdate
	
	# 201: Added
	# 400: Rejected (malformed request or exceeded rate limit; probably missing a parameter)
	# 403: Invalid username or password; in most cases probably should have been caught above.
	# 500: The service encountered an error.
	if 201 == add_status:
		if args.verbose:
			print article['url'].encode('utf-8')
	else:
		print >> sys.stderr, add_message
		ap.exit(-1)
