#! /bin/sh

usage() {

    cat <<EOF

Usage: `basename $0` -c <command> -p <parameter file>

Example:

    command line: sh launcher.sh -c 'python myprog.py' -p myprog.param

    myprog.param:
    .--------------------------
    |-f f1.dat -o r1.txt
    |-f f2.dat -o r2.txt
    |-f f3.dat -o r3.txt
    |

    The above command line will create the following jobs:
    
    python myprog.py -f f1.dat -o r1.txt
    python myprog.py -f f2.dat -o r2.txt
    python myprog.py -f f3.dat -o r3.txt

EOF

    exit 1
}

PROG=
PARAM=
OPT=
while getopts c:p: OPT ; do
    case $OPT in
	c)  PROG=$OPTARG
	    ;;
	p)  PARAM=$OPTARG
	    ;;
	\?) usage
	    ;;
    esac
done
shift `expr $OPTIND - 1`

if [ -z "$PROG" -o -z "$PARAM" ] ; then
    usage
fi

while read p ; do
    if test -z "$p" ; then
	continue
    fi

    echo "$PROG $p"
    eval exec $PROG $p &

done < $PARAM
