import re
import traceback
import sys
import time
from qt import *
from threading import Thread, Lock
import lpath
import at_lite as at
#from pyPgSQL import PgSQL
try:
    from sqlite3 import dbapi2 as sqlite
except ImportError:
    from pysqlite2 import dbapi2 as sqlite
from lpathtree_qt import *


__all__ = ["LPathDB", "LPathDbI", "LPathPgSqlDB", "LPathOracleDB", "LPathMySQLDB"]

class Prefetcher(QThread):
    def __init__(self, conn, indexSql, tableName, maxQueue=25, callback=None):
        """
        @param conn:
        @param indexSql: a query that returns a list of (sid,tid)
        @param tableName: the LPath table to query
        @param maxQueue: the maximum size of the queue
        @param callback: a callback function called for each tree loaded with
        the number of trees in the queue as an argument.
        """
        QThread.__init__(self)

        self.conn = conn
        self.indexSql = indexSql
        self.sqlTemplate = "select * from %s where sid=%%d and tid=%%d" % tableName
        self.maxQueue = maxQueue
        if callback is not None:
            self.callback = callback
        else:
            self.callback = lambda x:1
        self.queue = []
        self.keepRunning = True
        self.lock = QMutex()

    def run(self):
        indexCursor = self.conn.cursor()
        queryCursor = self.conn.cursor()
        queryCursor.arraysize = 250
        indexCursor.execute(self.indexSql.encode('utf-8'))
        
        row = indexCursor.fetchone()
        while row and self.keepRunning:
            if len(self.queue) >= self.maxQueue:
                time.sleep(1)
                continue
            sql = self.sqlTemplate % tuple(row)
            queryCursor.execute(sql.encode('utf-8'))
            tab = queryCursor.fetchall()
            self.lock.lock()
            ### critical region begins ###
            self.queue.append(tab)
            ### critical region ends #####
            self.lock.unlock()
            self.callback(len(self.queue))
            row = indexCursor.fetchone()

        indexCursor.close()
        queryCursor.close()
        
    def getNumTrees(self):
        return len(self.queue)
    
    def getNextTree(self):
        self.lock.lock()
        ### critical region begins ###
        if self.queue:
            row = self.queue[0]
            del self.queue[0]
        else:
            row = None
        ### critical region ends #####
        self.lock.unlock()
        return row

    def stop(self):
        self.callback = lambda x:1
        self.keepRunning = False
        

class LPathDbI:
    LPATH_TABLE_HEADER = [
        ('sid',int),('tid',int),('id',int),('pid',int),
        ('left',int),('right',int),('depth',int),
        ('type',unicode),('name',unicode),('value',unicode)
        ]

    EVENT_MORE_TREE = QEvent.User
    
    def submitQuery(self, query):
        """
        Run a given SQL query.
        
        @type  query: string
        @param query: SQL query to run.
        @return: True is query is submitted successfully, False otherwise.
        """
        return True
    
    def fetchNextTree(self):
        """
        @rtype: list
        @return: List of sentence ID, tree ID, SQL query cuased current result,
        TreeModel object corresponding to the tree, and LPathLocalDB object
        for the current tree.
        """
        pass

    def switchLPathTable(self, tableName):
        """
        @param tableName: Name of the new table to switch to.
        """
        pass

    def listTables(self):
        """
        @return: List of table names.
        """
        return ['T']
    
class LPathDB(LPathDbI):
    def __init__(self, conn, conn2=None):
        """
        @param conn: DB API 2 database connection object.
        @param conn2: DB connection object used for prefetcher. Note that the
        second connection is needed when the DB module cannot provide thread
        safety.
        """
        self.conn = conn
        self.conn2 = conn2
        self.tableName = None
        self.currentSql = None
        self.currentSql2 = None
        self.emitter = QObject()
        self.prefetcher = None
        self.eventReceivers = {}
        
    def _prefetchCallback(self, numTrees):
        for obj in self.eventReceivers[QEvent.User]:
            QApplication.postEvent(obj, QCustomEvent(self.EVENT_MORE_TREE,numTrees))
        #self.emitter.emit(PYSIGNAL("gotMoreTree"), (numTrees,))

    def connectToEvent(self, event, receiver):
        if event in self.eventReceivers:
            L = self.eventReceivers[event]
            if receiver not in L:
                L.append(receiver)
        else:
            self.eventReceivers[event] = [receiver]

    def disconnectFromEvent(self, event, receiver):
        try:
            self.eventReceivers[event].remove(receiver)
        except KeyError:
            pass
        except ValueError:
            pass
                
    def submitQuery(self, query):
        self.currentSql, self.currentSql2 = lpath.translate2(query, self.tableName)
        if self.currentSql is None:
            return False
        
        sql = re.sub(r"\s(%s[0-9]+).\*\s(.*)$" % self.tableName,
                     r" distinct \1.sid, \1.tid \2 order by \1.sid, \1.tid",
                     self.currentSql, 1)
        if self.prefetcher.running():
            self.prefetcher.stop()
            self.prefetcher.wait()
        if self.conn2 is not None:
            conn = self.conn2
        else:
            conn = self.conn
        self.prefetcher = Prefetcher(conn, sql, self.tableName,
                                     callback=self._prefetchCallback)
        self.prefetcher.start()
        return True

    def fetchNextTree(self):
        if self.prefetcher:
            rawtab = self.prefetcher.getNextTree()
            if rawtab:
                tab = at.TableModel(self.LPATH_TABLE_HEADER)
                for row in rawtab:
                    v = row[-1]
                    if v is not None:
                        row = list(row)
                        row[-1] = v.decode('utf-8')
                    tab.insertRow(row=row)
                tree = LPathTreeModel.importLPathTable(tab)
                sid, tid = rawtab[0][0:2]
                return sid, tid, self.currentSql, tree, \
                       LPathLocalDB(tab,self.tableName), self.currentSql2
        return None

    def switchLPathTable(self, tableName):
        if self.prefetcher and self.prefetcher.running():
            self.prefetcher.stop()
            self.prefetcher.wait()
        self.tableName = tableName
        self.currentSql = "select distinct sid, tid from %s order by sid, tid" % self.tableName
        self.currentSql2 = None
        if self.conn2 is not None:
            conn = self.conn2
        else:
            conn = self.conn
        self.prefetcher = Prefetcher(conn, self.currentSql, self.tableName,
                                     callback=self._prefetchCallback)
        self.prefetcher.start()
        
    def getNumTreesInMem(self):
        return self.prefetcher.getNumTrees()

class LPathPgSqlDB(LPathDB):
    def __init__(self, conn, conn2, user):
        LPathDB.__init__(self, conn, conn2)
        self.user = user

    def listTables(self):
        cur = self.conn.cursor()
        cur.execute("select tablename from pg_tables where tableowner=%s",
                    (self.user,))
        L = [x[0] for x in cur.fetchall()]
        cur.close()
        return L
    
class LPathOracleDB(LPathDB):
    def __init__(self, conn, conn2, user):
        """
        @param conn: DB API 2 connection object for an Oracle database.
        @param conn2: Another db connection object user for prefetcher.
        """
        LPathDB.__init__(self, conn, conn2)
        self.user = user

    def listTables(self):
        cur = self.conn.cursor()
        cur.execute("select table_name from all_tables where owner=:1",
                    (self.user.upper(),))
        L = [x[0] for x in cur.fetchall()]
        cur.close()
        return L
        
class LPathMySQLDB(LPathDB):
    def __init__(self, conn, conn2=None):
        """
        @param conn: DB API 2 database connection object.
        @param conn2: DB connection object used for prefetcher.
        """
        LPathDB.__init__(self, conn, conn2)

    def listTables(self):
        cur = self.conn.cursor()
        cur.execute("show tables")
        L = [x[0] for x in cur.fetchall()]
        cur.close()
        return L
        
class LPathLocalDB(LPathDbI):
    def __init__(self, tab, tableName='T'):
        self.tableName = tableName
        self.conn = sqlite.connect(':memory:')
        self.cursor = self.conn.cursor()
        self.cursor.execute("create table %s (sid,tid,id,pid,l,r,d,type,name,value)" % self.tableName)
        sql = "insert into %s values (?,?,?,?,?,?,?,?,?,?)" % self.tableName
        for r in tab:
            self.cursor.execute(sql, r)

    def _fetchTreeAsTable(self, sid, tid):
        sql = "select * from %s where sid=%d and tid=%d" % (self.tableName,sid,tid)
        c = self.conn.cursor()
        c.execute(sql)
        tab = at.TableModel(self.LPATH_TABLE_HEADER)
        for row in c.fetchall():
            tab.insertRow(row=row)
        return tab

    def submitQuery(self, query):
        if not self.conn:
            #raise Exception("no database connection")
            return False

        self.currentSql, self.currentSql2 = lpath.translate2(query, self.tableName)
        sql = re.sub(r"\s(%s[0-9]+).\*\s(.*)$" % self.tableName,
                     r" distinct \1.sid, \1.tid \2 order by \1.sid, \1.tid",
                     self.currentSql, 1)
        self.cursor.execute(sql)
        return True

    def fetchNextTree(self):    
        if self.cursor:
            res = self.cursor.fetchone()
            if res:
                sid, tid = res
                tab = self._fetchTreeAsTable(sid, tid)
                tree = LPathTreeModel.importLPathTable(tab)
                return sid, tid, self.currentSql, tree, \
                       LPathLocalDB(tab,self.tableName), self.currentSql2
            else:
                return None

