
#
# NLTK & Dependencies install script for Unix
# Assumes source and sudo access, plus standard gcc toolchain
#
# simply run as a shell script
#

# Python
echo "Obtaining and Installing Python ..."
cd /tmp
curl -o /tmp/Python-2.4.2.tgz http://www.python.org/ftp/python/2.4.2/Python-2.4.2.tgz
gunzip /tmp/Python-2.4.2.tgz
tar -xvf /tmp/Python-2.4.2.tar
cd /tmp/Python-2.4.2
./configure
make
sudo make install

# NumArray
echo "Obtaining and Installing NumArray ..."
cd /tmp
curl -o http://optusnet.dl.sourceforge.net/sourceforge/numpy/numarray-1.3.3.tar.gz
cd /tmp
gunzip /tmp/numarray-1.3.3.tar.gz
tar -xvf /tmp/numarray-1.3.3.tar.gz
cd /tmp/numarray-1.3.3
sudo python setup.py install

# NLTK Lite
echo "Obtaining and Installing NLTK-Lite ..."
cd $HOME
curl -o /tmp/nltk_lite-0.5.tar.gz http://optusnet.dl.sourceforge.net/sourceforge/nltk/nltk_lite-0.5.tar.gz
gunzip /tmp/nltk_lite-0.5.tar.gz
tar -xvf /tmp/nltk_lite-0.5.tar
cd /tmp/nltk_lite-0.5
sudo python setup.py install

# NLTK Lite Data
echo "Obtaining and Installing NLTK-Lite Corpora ..."
cd $HOME
curl -o /tmp/nltk_lite-corpora-0.5.zip http://optusnet.dl.sourceforge.net/sourceforge/nltk/nltk_lite-corpora-0.5.zip
unzip /tmp/nltk_lite-corpora-0.5.zip
sudo mv corpora /usr/share/nltk
export NLTK_LITE_CORPORA=/usr/share/nltk
echo "export NLTK_LITE_CORPORA=/usr/share/nltk" >> $HOME/.bash_profile

# Cleanup
echo "Cleaning Up ..."

cd /tmp
rm Python*.tar
rm nltk.tar





