from qt import *
from db import *
import os
try:
    from pyPgSQL import PgSQL
    CAP_PGSQL = True
except ImportError:
    CAP_PGSQL = False
try:
    os.environ['NLS_LANG'] = '.UTF8'
    import cx_Oracle
    CAP_ORACLE = True
except ImportError:
    CAP_ORACLE = False
try:
    import MySQLdb
    CAP_MYSQL = True
except ImportError:
    CAP_MYSQL = False

class ConnectionError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class DummyPanel(QWidget):        
    def __init__(self, parent=None, name=None):
        QWidget.__init__(self, parent, name)
    def connect(self):
        raise ConnectionError("no database server type selected")

class ConnectionPanelI:
    def connect(self): pass
    
class PgsqlPanel(QWidget, ConnectionPanelI):
    def __init__(self, parent=None, name=None):
        QWidget.__init__(self, parent, name)
        
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Host: ",self),0,0)
        layout.addWidget(QLabel("Port: ",self),1,0)
        layout.addWidget(QLabel("Database: ",self),2,0)
        layout.addWidget(QLabel("User: ",self),3,0)
        layout.addWidget(QLabel("Password: ",self),4,0)
        self.entHost = QLineEdit(self)        
        self.entPort = QLineEdit("5432", self)        
        self.entDatabase = QLineEdit("qldb", self)        
        self.entUser = QLineEdit("qldb", self)        
        self.entPassword = QLineEdit(self)
        self.entPassword.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.entHost,0,1)
        layout.addWidget(self.entPort,1,1)
        layout.addWidget(self.entDatabase,2,1)
        layout.addWidget(self.entUser,3,1)
        layout.addWidget(self.entPassword,4,1)

    def connect(self):
        conninfo = {
            "host":self.entHost.text(),
            "port":self.entPort.text(),
            "database":self.entDatabase.text(),
            "user":self.entUser.text(),
            "password":self.entPassword.text()
            }
        if conninfo['password'] is None:
            del conninfo['password']
        try:
            conn = PgSQL.connect(**conninfo)
            conn2 = PgSQL.connect(**conninfo)
            return LPathPgSqlDB(conn, conn2, conninfo["user"].ascii())
        except PgSQL.libpq.DatabaseError, e:
            try:
                enc = os.environ['LANG'].split('.')[-1]
                msg = e.message.decode(enc)
            except:
                msg = e.message
            raise ConnectionError(msg)

class OraclePanel(QWidget, ConnectionPanelI):
    def __init__(self, parent=None, name=None):
        QWidget.__init__(self, parent, name)
        
        user = os.path.basename(os.path.expanduser("~"))
        try:
            orahome = os.environ["ORACLE_HOME"]
        except KeyError:
            orahome = ''
            
        layout = QGridLayout(self)
        #layout.addWidget(QLabel("ORACLE_HOME: ", self),2,0)
        layout.addWidget(QLabel("User: ",self),0,0)
        layout.addWidget(QLabel("Password: ",self),1,0)
        #self.entOraHome = QLineEdit(orahome, self)
        self.entUser = QLineEdit(user, self)        
        self.entPassword = QLineEdit(self)
        self.entPassword.setEchoMode(QLineEdit.Password)
        #layout.addWidget(self.entOraHome,2,1)
        layout.addWidget(self.entUser,0,1)
        layout.addWidget(self.entPassword,1,1)

    def connect(self):
        #orahome = self.entOraHome.text().ascii()
        user = self.entUser.text().ascii()
        if '@' in user:
            user,service = user.split('@')
            service = '@' + service
        else:
            service = ''
        pw = self.entPassword.text().ascii()
        #if orahome:
        #    os.putenv("ORACLE_HOME", str(orahome))
        try:
            conn = cx_Oracle.connect(user+'/'+pw+service)
            conn2 = cx_Oracle.connect(user+'/'+pw+service)
        except cx_Oracle.DatabaseError, e:
            try:
                enc = os.environ['LANG'].split('.')[-1]
                msg = e.__str__().decode(enc)
            except:
                msg = e.__str__()
            raise ConnectionError(msg)
        return LPathOracleDB(conn, conn2, user)

class MySQLPanel(QWidget, ConnectionPanelI):
    def __init__(self, parent=None, name=None):
        QWidget.__init__(self, parent, name)
        
        user = os.path.basename(os.path.expanduser("~"))

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Host: ",self),0,0)
        layout.addWidget(QLabel("Port: ",self),1,0)
        layout.addWidget(QLabel("Database: ",self),2,0)
        layout.addWidget(QLabel("User: ",self),3,0)
        layout.addWidget(QLabel("Password: ",self),4,0)
        self.entHost = QLineEdit(self)        
        self.entPort = QLineEdit("5432", self)        
        self.entDatabase = QLineEdit("qldb", self)        
        self.entUser = QLineEdit(user, self)        
        self.entPassword = QLineEdit(self)
        self.entPassword.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.entHost,0,1)
        layout.addWidget(self.entPort,1,1)
        layout.addWidget(self.entDatabase,2,1)
        layout.addWidget(self.entUser,3,1)
        layout.addWidget(self.entPassword,4,1)

    def connect(self):
        conninfo = {
            "host":str(self.entHost.text()),
            "port":int(self.entPort.text()),
            "db":str(self.entDatabase.text()),
            "user":str(self.entUser.text()),
            "passwd":str(self.entPassword.text())
            }
        if conninfo['passwd'] is None:
            del conninfo['passwd']
        try:
            conn = MySQLdb.connect(**conninfo)
            return LPathMySQLDB(conn)
        except MySQLdb.DatabaseError, e:
            try:
                enc = os.environ['LANG'].split('.')[-1]
                msg = e.message.decode(enc)
            except:
                msg = e.message
            raise ConnectionError(msg)

class DatabaseConnectionDialog(QDialog):
    def __init__(self, parent=None, name=None,
                 modal=False, wflag=0):
        QDialog.__init__(self, parent, name, modal, wflag)
        self.setCaption("DB Connection")

        self.wstack = QWidgetStack(self)
        self.conpans = {"--":self.conpanNone,
                       "PostgreSQL":self.conpanPostgreSQL,
                       "Oracle":self.conpanOracle,
                       "MySQL":self.conpanMySQL}
        self.conpan = None
        self.conpanNone()

        layout = QVBoxLayout(self)
        hbox = QHBox(self)
        QLabel('Server type', hbox)
        combo = QComboBox(False, hbox)
        combo.insertItem("--")
        if CAP_PGSQL: combo.insertItem("PostgreSQL")
        if CAP_ORACLE: combo.insertItem("Oracle")
        if CAP_MYSQL: combo.insertItem("MySQL")

        layout.addWidget(hbox)
        layout.addWidget(self.wstack)
        layout.setStretchFactor(self.wstack, 1)
        
        buttons = QHBox(self)
        self.btnConnect = QPushButton("Co&nnect", buttons)
        self.btnCancel = QPushButton("&Cancel", buttons)
        layout.addWidget(buttons)

        layout.setMargin(5)
        layout.setSpacing(5)
        buttons.setMargin(10)
        buttons.setSpacing(10)

        self.connect(self.btnConnect, SIGNAL("clicked()"), self.connectToDb)
        self.connect(self.btnCancel, SIGNAL("clicked()"), self.reject)
        self.connect(combo, SIGNAL("activated(const QString&)"), self.changePanel)
        
        self.db = None

    def changePanel(self, s):
        self.conpans[str(s)]()
    def conpanNone(self):
        self.conpan = DummyPanel(self)
        self.wstack.removeWidget(self.wstack.visibleWidget())
        self.wstack.addWidget(self.conpan)
        self.wstack.raiseWidget(self.conpan)
    def conpanPostgreSQL(self):
        self.conpan = PgsqlPanel(self)
        self.wstack.removeWidget(self.wstack.visibleWidget())
        self.wstack.addWidget(self.conpan)
        self.wstack.raiseWidget(self.conpan)
    def conpanOracle(self):
        self.conpan = OraclePanel(self)
        self.wstack.removeWidget(self.wstack.visibleWidget())
        self.wstack.addWidget(self.conpan)
        self.wstack.raiseWidget(self.conpan)
    def conpanMySQL(self):
        self.conpan = MySQLPanel(self)
        self.wstack.removeWidget(self.wstack.visibleWidget())
        self.wstack.addWidget(self.conpan)
        self.wstack.raiseWidget(self.conpan)

    def connectToDb(self, *args):
        try:
            self.db = self.wstack.visibleWidget().connect()
            self.accept()
        except ConnectionError, e:
            QMessageBox.critical(self, "Connection Error",
                                 "Unable to connect to database:\n" + e.__str__())

    def getLPathDb(self):
        return self.db
        

class TableSelectionDialog(QDialog):
    def __init__(self, tableNames, parent=None, name=None,
                 modal=False, wflag=0):
        QDialog.__init__(self, parent, name, modal, wflag)
        self.setCaption("DB Connection")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a table below:",self))
        listbox = QListBox(self)
        layout.addWidget(listbox)
        hbox = QHBox(self)
        okButton = QPushButton("OK", hbox)
        cancelButton = QPushButton("Cancel", hbox)
        hbox.setMargin(10)
        hbox.setSpacing(10)
        layout.addWidget(hbox)

        layout.setMargin(5)
        layout.setSpacing(5)

        L = tableNames[:]
        L.sort()
        for tab in L:
            listbox.insertItem(tab)

        self.listbox = listbox

        self.connect(okButton, SIGNAL("clicked()"), self._okClicked)
        self.connect(cancelButton, SIGNAL("clicked()"), self._cancelClicked)
        self.tab = None

    def _okClicked(self):
        sel = self.listbox.selectedItem()
        if sel is not None:
            self.tab = unicode(sel.text())
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "You didn't select a table.")
                                 
    def _cancelClicked(self):
        self.reject()

    def getSelectedTable(self):
        return self.tab
    
if __name__ == "__main__":
    app = QApplication([])
    d = TableSelectionDialog(['a','b','c','d','f','g','e','h','i'])
    d.exec_loop()
    
