
#
# NLTK & Dependencies install script for OS X
#
# simply run as a shell script
#

# Python
echo "Obtaining and Installing MacPython ..."
cd $HOME
curl -o MacPython-OSX-2.4.1-1.dmg http://undefined.org/python/MacPython-OSX-2.4.1-1.dmg
hdid MacPython-OSX-2.4.1-1.dmg
cd /Volumes/MacPython-OSX-2.4.1-1/
sudo /usr/sbin/installer -pkg MacPython-OSX.pkg -target /Volumes/MacPython-OSX-2.4.1-1-PKG
cd /usr/bin
sudo rm python
sudo ln -s /Library/Frameworks/Python.framework/Versions/2.4/Resources/Python.app/Contents/MacOS/python python

# NumArray
echo "Obtaining and Installing NumArray ..."
cd $HOME
curl -o numarray-1.1.1-py2.4-macosx10.3.zip http://www.pythonmac.org/packages/numarray-1.1.1-py2.4-macosx10.3.zip
unzip numarray-1.1.1-py2.4-macosx10.3.zip
cd numarray-1.1.1-py2.4-macosx10.3
sudo installer -target / -pkg numarray-1.1.1.mpkg

# NLTK Lite
echo "Obtaining and Installing NLTK-Lite Corpora ..."
cd $HOME
curl -o nltk_lite-0.5.tar.gz http://optusnet.dl.sourceforge.net/sourceforge/nltk/nltk_lite-0.5.tar.gz
gunzip nltk_lite-0.5.tar.gz
tar -xvf nltk_lite-0.5.tar
cd nltk_lite-0.5
sudo python setup.py install

# NLTK Lite Data
echo "Obtaining and Installing NLTK-Lite Corpora ..."
cd $HOME
curl -o nltk_lite-corpora-0.5.zip http://optusnet.dl.sourceforge.net/sourceforge/nltk/nltk_lite-corpora-0.5.zip
unzip nltk_lite-corpora-0.5.zip
sudo mv corpora /usr/share/nltk
export NLTK_LITE_CORPORA=/usr/share/nltk
echo "export NLTK_LITE_CORPORA=/usr/share/nltk" >> $HOME/.bash_profile

# Cleanup
echo "Cleaning Up ..."

cd $HOME
hdiutil detach /Volumes/MacPython-OSX-2.4.1-1





