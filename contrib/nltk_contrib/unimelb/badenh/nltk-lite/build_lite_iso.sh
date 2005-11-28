#!/bin/bash
#
# Script to build an ISO image for complete (prereq and dist) NLTK Lite
# Assumes a Linux-like operating system (at least: bash, wget, mkisofs)
#
# badenh@cs.mu.oz.au
#
# 0.1 20050803 made for 0.2
# 0.2 20050905 updated for 0.4
# 0.3 20050906 now supports dynamic versions
#
# Still to be done: Python docs (?), NLTK site (?)
#

#
# Setup
#

export WORKDIR=/tmp/workdir		# change this to suit your system
mkdir $WORKDIR
echo "Working directory is $WORKDIR"

export MACWORKDIR=$WORKDIR/mac		# change this to suit your system
mkdir $MACWORKDIR
echo "Mac software will be placed in $MACWORKDIR"

export WINWORKDIR=$WORKDIR/windows	# change this to suit your system
mkdir $WINWORKDIR
echo "Windows software will be placed in $WINWORKDIR"

export UNXWORKDIR=$WORKDIR/unix		# change this to suit your system
mkdir $UNXWIRKDIR
echo "Unix (source) software will be placed in $UNXWORKDIR"

export ISODIR=/tmp/isodir		# change this to suit your system
mkdir $ISODIR
echo "ISO Image will be placed in $ISODIR"

export SFNETMIRROR=http://optusnet.dl.sourceforge.net/sourceforge	#change this to suit your system
echo "Using $SFNETMIRROR"

export VERSION=0.6			# change this to suit	
echo "NLTK Lite version $VERSION"

#
# Mac
#
echo "Starting download of software for Mac OS X ..."

wget -O $MACWORKDIR/MacPython-OSX-2.4.1-1.dmg http://undefined.org/python/MacPython-OSX-2.4.1-1.dmg
wget -O $MACWORKDIR/numarray-1.1.1-py2.4-macosx10.3.zip http://www.pythonmac.org/packages/numarray-1.1.1-py2.4-macosx10.3.zip
wget -O $MACWORKDIR/nltk_lite-$VERSION.tar.gz $SFNETMIRROR/nltk/nltk_lite-$VERSION.tar.gz
wget -O $MACWORKDIR/nltk_lite-corpora-$VERSION.zip $SFNETMIRROR/nltk/nltk_lite-corpora-$VERSION.zip

echo "Finished download of software for Mac OS X ..."

#
# Windows 
#

echo "Starting download of software for Windows ..."

wget -O $WINWORKDIR/Python-2.4.1.msi http://www.python.org/ftp/python/2.4.1/Python-2.4.1.msi
wget -O $WINWORKDIR/numarray-1.4.1.exe http://prdownloads.sourceforge.net/numpy/numarray-1.4.1.exe?download
wget -O $WINWORKDIR/nltk_lite-$VERSION.exe $SFNETMIRROR/nltk_lite-$VERSION.exe
wget -O $WINWORKDIR/nltk_lite-corpora-$VERSION.zip $SFNETMIRROR/nltk/nltk_lite-corpora-$VERSION.zip

echo "Finished download of software for Windows ..."

#
# Unix (Source)
#

echo "Starting download of software for Unix (Source) ..."

wget -O $UNXWORKDIR/Python-2.4.1.tgz http://www.python.org/ftp/python/2.4.1/Python-2.4.1.tgz
wget -O $UNXWORKDIR/numarray-1.4.1.tar.gz $SFNETMIRROR/numpy/numarray-1.4.1.tar.gz
wget -O $UNXWORKDIR/nltk_lite-$VERSION.tar.gz $SFNETMIRROR/nltk/nltk_lite-$VERSION.tar.gz
wget -O $UNXWORKDIR/nltk_lite-corpora-$VERSION.zip $SFNETMIRROR/nltk/nltk_lite-corpora-$VERSION.zip

echo "Finished download of software for Unix (Source) ..."

#
# Image Construction
#

echo "Making ISO image in $ISODIR ..."

mkisofs -o $ISODIR/NLTK-Lite-$VERSION.iso $WORKDIR

echo "Finished making ISO image in $ISODIR ..."
ls -la $ISODIR

#
# Cleanup
#

echo "Cleanup of $WORKDIR"
rm -rf $WORKDIR/*
rmdir $WORKDIR

