#!venv/bin/python
from app import db 
from app.models import Parts
import xlrd, sys 
#file_location = '/Users/eduaalva/Documents/Lab_Database_Project/savbu_database/spreadsheet.xlsx'

#try:
workbook = xlrd.open_workbook(str(sys.argv[1]))
sheet = workbook.sheet_by_index(0)

# read header values into the list    
keys = [sheet.cell(0, col_index).value for col_index in xrange(sheet.ncols)]

dict_list = []
for row_index in xrange(1, sheet.nrows):
	d = {keys[col_index]: sheet.cell(row_index, col_index).value 
		for col_index in xrange(sheet.ncols)}
	dict_list.append(d)

for i in dict_list:
	for j in range(0, int(i['Qty'])):
		db.session.add(Parts(
			i['PO#'], 
			i['PR#'], 
			i['Part'], 
			i['Project Name'],
			i['Requestor'],
			i['Supplier'],
			i['Supplier Contact'],
			i['Item Description'],
			i['CPN'],
			i['PID'],
			i['Manufacturer Part#'],
			i['Submit Date'],
			i['Tracking#']
			))

db.session.commit()
#except:
#	print 'error: try ./db_import.py <filename.xlsx>'
