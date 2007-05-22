#! /bin/sh

usage() {
    cat <<EOF

usage: `basename $0` [-h] [-i <psql>] [-d <database>] [<file list>]

    -h	display usage
    -i	specify psql command
    -d	specify database name

    <psql> is a query interface program provided by postgresql.
    By default, "psql" is assigned to the option.

    <database> is the database in which the table will be loaded.
    By default, "qldb" is used.

    <file list> is a list of treebank files.  If it is omitted,
    STDIN is assumed to be the input.

EOF
    exit 1
}

PSQL=psql
DBNAM=qldb
OPT=
while getopts hi:d: OPT ; do
    case $OPT in
        h) usage  ;;
        i) PSQL=$OPTARG ;;
        d) DBNAM=$OPTARG ;;
        *) usage ;;
    esac
done
shift `expr $OPTIND - 1`
LST=$1
if [ -n "$LST" -a ! -f "$LST" ]; then
    echo
    echo "file $LST not found"
    echo
    exit 1
fi


echo "WARNING: The existing table t will be dropped."
echo "WARNING: Press Ctrl+C to exit or any key to proceed."
read ans </dev/tty
$PSQL -c "drop table t" $DBNAM > /dev/null 2>&1
$PSQL -c "\i lpath-schema.sql" $DBNAM && \

echo "Loading the table.  Please wait..."

load() {
    if [ -n "$LST" ]; then
        cat $LST | xargs cat
    else
        xargs cat
    fi |
    python tb2tbl.py |
    $PSQL -c "\copy t from stdin with delimiter ' ' null '-'" $DBNAM
}

time load


