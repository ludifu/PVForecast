"""
Copyright (C) 2022    Stefan Eichenberger   se_misc ... hotmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

This is the main script to run a simulation of PVControl for one or multiple days. 
This script is typically called interactively on a performant machine. By default, 
config.ini in the local directory is the configuration file. But argument -c can
specify a different file.
"""

import sqlite3
from datetime  import datetime, timezone
from .forecast import Forecast

class DBRepository:
    """Class for storing PVForecast related data into sqlite database"""

    def __init__(self, config):
        """Initialize DBRepository
        config      configparser object with section [PVSystem]"""
        self.config  = config
        path         = self.config['DBRepo'].get('storePath')
        self.dbName  = path + '/' + self.config['DBRepo'].get('dbName')                   # database name (including path)
        self._db     = sqlite3.connect(self.dbName)                                       # db connector
        c            = self._db.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablenames   = c.fetchall()
        self._tables = [''.join(table) for table in tablenames]                           # tuples in tablenames are like (name, ) - and we need get rid of the empty last element
        c.close()

    def __del__(self):
        """Deconstructor: close database connection"""
        self._db.close()

    def loadData(self, data: Forecast):
        """Store data (subclass of Forecast) in SQLite database"""
        
        c = self._db.cursor()
        table = data.SQLTable
        if (table not in self._tables):                                                  # create database table table
            sql = (' real, ').join(data.get_ParaNames()) + ' real'
            sql = 'CREATE TABLE ' + table + ' (IssueTime text, PeriodEnd text, ' + sql + ', PRIMARY KEY(IssueTime, PeriodEnd));'
            c.execute(sql)
            myData = data.DataTable
        else:                                                                            # check wether we have omitted / newfields
            c.execute("SELECT name FROM PRAGMA_TABLE_INFO('" + table + "') WHERE name <> 'PeriodEnd';")
            colnames = c.fetchall()
            cols     = [''.join(col) for col in colnames]                                # tuples in colnames are like (name, ) - and we need get rid of the empty last element
            myData   = data.DataTable[data.DataTable.columns.intersection(cols)]
            newCols  = data.DataTable.columns.difference(cols)                           # we load only columns existing in database, but warn on new columns
            if (len(newCols) > 0):
                print("Warning - New columns found in incoming data for table " + table + " at " + data.IssueTime)
                print(*newCols)
        
        c.execute("SELECT IssueTime FROM " + table + " WHERE IssueTime='" + data.IssueTime + "';")
        if (c.fetchone() != None):
            print("Message - IssueTime " + data.IssueTime + " already exists in table " + table + ", no data to add to DB")
        else:
            myData['IssueTime'] = data.IssueTime
            myData.to_sql(table, self._db, if_exists='append')
        c.close()

    def getLastIssueTime(self, table):
        if (table in self._tables): 
            c = self._db.cursor()
            c.execute("SELECT max(IssueTime) FROM " + table + ";")
            t = c.fetchone()[0]
            IssueTime = datetime.fromisoformat(t)
        else:
            IssueTime = datetime(1990, 1, 1, 0, 0, 0, 0,timezone.utc)
        return(IssueTime)
