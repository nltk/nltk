import sys
import os

from optparse import OptionParser
import platform
import pwd
from at.table import TableModel
from at.tree import TreeModel
#from pyPgSQL import PgSQL
import re

def tb2tbl(tree,a,b):
    #conn.begin()
    #cursor.execute("begin")
    for r in tree.exportLPathTable(TableModel,a,b):
        cursor.execute(SQL1, tuple(r))
    #cursor.execute("commit")
    conn.commit()

def connectdb(opts):
    try:
        if opts.servertype == 'postgresql':
            try:
                conn = PgSQL.connect(host=opts.host, port=opts.port, database=opts.db,
                                     user=opts.user, password=opts.passwd)
            except PgSQL.libpq.DatabaseError, e:
                print e
                sys.exit(1)
            return conn
        elif opts.servertype == 'oracle':
            import cx_Oracle
            if '@' in opts.user:
                user,suffix = opts.user.split('@')
            else:
                user = opts.user
                suffix = ''
            dsn = "%s/%s@%s" % (user,opts.passwd,suffix)
            conn = cx_Oracle.connect(dsn)
            return conn
    except ImportError, e:
        print e
        sys.exit(1)

def limit(servertype, sql, num):
    if servertype == 'postgresql':
        sql += " limit %d" % num
    elif servertype == 'oracle':
        if 'where' in sql.lower():
            if 'and' in sql.lower():
                sql += " and rownum<=%d" % num
            else:
                sql += " rownum<=%d" % num
        else:
            sql += " where rownum<=%d" % num
    else:
        sql += " limit %d" % num
    return sql
 
if platform.system() == 'Windows':
    default_user = os.getenv('USERNAME')
    def getpass():
        import msvcrt
        s = ''
        c = msvcrt.getch()
        while ord(c) != 13:
            if ord(c) == 8:
                if len(s) > 0:
                    s = s[:-1]
            else:
                s += c
            c = msvcrt.getch()
        return s
else:
    # os.getlogin() seems to have some bug
    default_user = pwd.getpwuid(os.getuid())[0]
    def getpass():
        import termios
        tty = file('/dev/tty')
        attr = termios.tcgetattr(tty.fileno())
        attr[3] &= ~termios.ECHO
        termios.tcsetattr(tty.fileno(), termios.TCSANOW, attr)
        p = tty.readline().strip('\n')
        attr[3] |= termios.ECHO
        termios.tcsetattr(tty.fileno(), termios.TCSANOW, attr)
        tty.close()
        return p

usage = "%prog [options] treebank"
desc = """Load treebank data into a LPath table.
It takes one argument "treebank", which should be a path to the directory
containing treebank files. Every file under this directory tree is assumed
to be an input.  If '-' is given instead of a directory, treebank data should
be streamed into standard input.
"""
  
optpar = OptionParser(usage=usage,description=desc)
optpar.add_option("-c", "--create-table", dest="create", default=False,
                  action="store_true",
                  help="create table if not exist")
optpar.add_option("-d", "--database", dest="db", default="qldb",
                  help="use NAME as the target LPath database",
                  metavar="DB")
optpar.add_option("-f", "--file-filter", dest="filter",
                  help="use REGEX to filter treebank file names. "
                  "Ignored if treebank data is given from standard input",
                  metavar="REGEX")
optpar.add_option("-H", "--host", dest="host", default=os.uname()[1],
                  help="LPath database is hosted by HOST",
                  metavar="HOST")
optpar.add_option("-n", "--num-trees", dest="numtree", default=0,
                  help="load only NUM trees (0=all)",
                  metavar="NUM", type="int")
optpar.add_option("-P", "--port", dest="port", default=5432,
                  help="database server is listening on port PORT",
                  metavar="PORT", type="int")
optpar.add_option("-p", "--password", dest="passwd",
                  help="use PASSWD to connect to the database",
                  metavar="PASSWD")
optpar.add_option("-t", "--table", dest="table", default="t",
                  help="use TABLE as the target LPath table",
                  metavar="TABLE")
optpar.add_option("-u", "--user", dest="user", default=default_user,
                  help="use USER to connect to the database",
                  metavar="USER")
optpar.add_option("-x", "--purge", dest="purge", default=False,
                  action="store_true",
                  help="empty the database before loading")
optpar.add_option("-y", "--server-type", dest="servertype",
                  help="server type (=postgresql|oracle)",
                  metavar="STR")
opts, args = optpar.parse_args()

# check arguments
if len(args) == 0:
    optpar.error("required argument is missing")
elif len(args) > 1:
    optpar.error("too many arguments")
tbdir = args[0]
        
# check options
if not opts.user:
    optpar.error("user name is missing")
    
if opts.passwd is None:
    print "Password:",
    opts.passwd = getpass()
else:
    passwd = opts.passwd

if opts.filter is None:
    filter = re.compile(".*")
else:
    try:
        filter = re.compile(opts.filter)
    except:
        optpar.error("invalid regex for -f (--filter) option")

if opts.servertype is None:
    optpar.error("you must specify the server type; use -y option")
elif opts.servertype == 'postgresql':
    from pyPgSQL import PgSQL
    DatabaseError = PgSQL.libpq.DatabaseError
elif opts.servertype == 'oracle':
    import cx_Oracle
    from cx_Oracle import DatabaseError
else:
    optpar.error("server type should be one of the followins: postgresql, oracle")
    
# try to connect to database
conn = connectdb(opts)
cursor = conn.cursor()

print os.path.join('',os.path.dirname(sys.argv[0]))

# check if table exists
try:
    sql = limit(opts.servertype, "select * from "+opts.table, 1)
    cursor.execute(sql)
except DatabaseError, e:
    if opts.create:
        p = os.path.join(os.path.dirname(sys.argv[0]),'lpath-schema.sql')
        for line in file(p).read().replace("TABLE",opts.table).split(';'):
            if line.strip():
                cursor.execute(line)
    else:
        print "table %s doesn't exist" % `opts.table`
        sys.exit(1)

# set correct table name in the insertion SQL
if opts.servertype == 'postgresql':
    SQL1 = "insert into TABLE values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
elif opts.servertype == 'oracle':
    SQL1 = "insert into TABLE values(:c1,:c2,:c3,:c4,:c5,:c6,:c7,:c8,:c9,:c10)"
SQL1 = SQL1.replace('TABLE', opts.table)

# empty the table if necessary
if opts.purge:
    cursor.execute("delete from "+opts.table)

# obtain the next sid
cursor.execute("select max(sid) from "+opts.table)
r = cursor.fetchone()
if r[0] is None:
    sid = 1
else:
    sid = r[0] + 1
        
def do(tree):
    global sid
    t = tree.children[0]
    t.prune()
    tb2tbl(t, sid, 1)
    sid += 1

count = opts.numtree
if tbdir == '-':
    for tree in TreeModel.importTreebank(sys.stdin):
        print tree
        do(tree)
        count -= 1
        if count == 0: break
else:
    for root, dirs, files in os.walk(tbdir):
        for f in files:
            print f,
            if filter.match(f):
                p = os.path.join(root,f)
                for tree in TreeModel.importTreebank(file(p)):
                    do(tree)
                    count -= 1
                    if count == 0: sys.exit(0)  # done
                print sid
            else:
                print 'skipped'
        
