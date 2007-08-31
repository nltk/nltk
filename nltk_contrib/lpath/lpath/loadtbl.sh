#! /bin/sh

usage() {
    cat <<EOF

usage: `basename $0` [-i <psql>] [-u <psql user>] [-d <database>] <table file>

    <psql> is a query interface program provided by postgresql.
    By default, "psql" is assigned to the option.

    <psql user> is a user of the database.
    
    <database> is the database in which the table will be loaded.
    By default, "qldb" is used.

    <table file> must be a bzip2 archive.

EOF
    exit 1
}

PSQL=psql
USER="-U qldb"
DBNAM=qldb
OPT=
while getopts i:u:d: OPT ; do
    case $OPT in
        i) PSQL=$OPTARG ;;
        u) USER="-U $OPTARG" ;;
        d) DBNAM=$OPTARG ;;
        *) usage ;;
    esac
done
shift `expr $OPTIND - 1`

TBL=$1
[ -z "$TBL" ] && usage
if [ ! -f $TBL ] ; then
    echo
    echo "Table $TBL doesn't exist.  Abort."
    echo
    exit 1
fi

echo "WARNING: The existing table t will be dropped."
echo "WARNING: Press any key to proceed..."
read ans
$PSQL $USER -c "drop table t" $DBNAM > /dev/null 2>&1
$PSQL $USER -c "\i lpath-schema.sql" $DBNAM && \

echo "Loading the table.  Please wait..."

load() {
bunzip2 -c $TBL | $PSQL $USER -c "\copy t from stdin with delimiter ' ' null '-'" $DBNAM
}

time load


