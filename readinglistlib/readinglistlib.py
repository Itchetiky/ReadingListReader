import os
import subprocess
import plistlib
import datetime
from copy import deepcopy
from dateutil.parser import parse

# Set epoch to Epoch as datetime.datetime.min returns a year of 1 instead of 1900
# strftime formats: 2012-07-17T12:02:47Z (this is how the raw dates are formatted)
# we use the same format except without the T and Z
epochseed = datetime.datetime.utcfromtimestamp(0).strftime("%Y-%m-%d %H:%M:%S")
epoch = datetime.datetime.strptime(epochseed, '%Y-%m-%d %H:%M:%S')

class ReadingListReader:
	
	# input is path to a Safari bookmarks file; if None, use default file	
	def __init__(self, input=None):

		if None == input:
			input = os.path.expanduser('~/Library/Safari/Bookmarks.plist')

		# Read and parse the bookmarks file
		pipe = subprocess.Popen(('/usr/bin/plutil', '-convert', 'xml1', '-o', '-', input), shell=False, stdout=subprocess.PIPE).stdout
		xml = plistlib.readPlist(pipe)
		pipe.close()
		
		# Locate reading list section
		section = filter(lambda record: 'com.apple.ReadingList' == record.get('Title'), xml['Children'])
		reading_list = section[0].get('Children')
		if None == reading_list:
			reading_list = []
		
		# Assemble list of bookmark items
		self._articles = []
		for item in reading_list:
					
			# Use epoch time as a placeholder for undefined dates
			# (potentially facilitates sorting and filtering)
			added = item['ReadingList'].get('DateAdded')
			if None == added:
				added = epoch
			
			viewed = item['ReadingList'].get('DateLastViewed')
			if None == viewed:
				viewed = epoch
			
			date = item['ReadingList'].get('DateLastFetched')
			if None == date:
				date = epoch

			self._articles.append({
					'title': item['URIDictionary']['title'],
					'url': item['URLString'],
					'preview': item['ReadingList'].get('PreviewText',''),
					'date': date,
					'added': added,
					'viewed': viewed,
					'uuid': item['WebBookmarkUUID'],
					'synckey': item['Sync'].get('Key'),
					'syncserverid': item['Sync'].get('ServerID')})
				
	# show specifies what articles to return: 'unread' or 'read'; if None, all.
	# sortfield is one of the _articles dictionary keys
	# ascending determines sort order; if false, sort is descending order
	# dateformat is used to format dates; if None, datetime objects are returned
	def read(self, show='all', sortfield='date', ascending=True, dateformat=None, syncdate=None):
			
		# Filter, sort, and return a fresh copy of the internal article list
		articles = deepcopy(self._articles)

		# Filter article list to only send the 'later than' arcticles
		if None != syncdate:
			syncdate = datetime.datetime.strptime(syncdate, '%Y-%m-%d')
			print 'Sync from date of:', syncdate
			articles = filter(lambda record: syncdate <= record['added'] or syncdate <= record['date'], articles)

		# Filter article list to show only unread or read articles, if requested		
		if 'unread' == show:
			articles = filter(lambda record: epoch == record['viewed'], articles)
		elif 'read' == show:
			articles = filter(lambda record: epoch != record['viewed'], articles)
		else:
			pass
		
		# Sort articles.
		articles = sorted(articles, key=lambda record: record[sortfield])
		if not ascending:
			articles.reverse()
		
		# Replace any datetime.min sort/filter placeholders with None
		articles = map(self.resetUndefinedDates, articles)
		
		# If a date format (such as '%Y-%m-%d %H:%M:%S') is specified,
		# convert all defined dates to that format and undefined dates to ''.
		if None != dateformat:
			articles = map(self.formatDates, articles, [dateformat for i in range(len(articles))])

		return articles
	
	def resetUndefinedDates(self, article):
		if epoch == article['viewed']:
			article['viewed'] = None
		if epoch == article['added']:
			article['added'] = None
		if epoch == article['date']:
			article['date'] = None	
		return article
	
	def formatDates(self, article, dateformat):
		if None != article['viewed']:
			article['viewed'] = article['viewed'].strftime(dateformat)
		else:
			article['viewed'] = ''
		if None != article['added']:
			article['added'] = article['added'].strftime(dateformat)
		else:
			article['added'] = ''
		if None != article['date']:
			article['date'] = article['date'].strftime(dateformat)
		else:
			article['date'] = ''
		return article
		
