#!/usr/bin/python
"""
Classes to read and process MedLine XML record files, for use in processing modules.

They can handle the XML format used by PubMed and MedLine services, for example as returned by eutils online services

   >>> xml_records = urllib.urlopen('http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id='+list_of_pmids+'&retmode=xml').read()

When used, an object is created as a global repository, from which records (also objects) can be queried and extracted. These record-objects have properties like title, authors, abstracts that return their string values.

Somewhat long loading times can be shortened later by serializing objects using  cPickle module

   USAGE:
   >>> from BioReader import *
   >>> data = DataContainer('AllAbstracts.xml','pubmed')
   >>> data.howmany # len(data.dictRecords.keys())
   >>> data.keys    # data.dictRecords.keys()
   >>> record = data.Read('7024555')
   >>> record.title

           u'The birA gene of Escherichia coli encodes a biotin holoenzyme synthetase.'
           record +
                  - B{.title}
                  - B{.pmid}
                  - B{.Abs} I{(abstracts)}
                  - B{.year}
                  - B{.journal}
                  - B{.auth} I{(list of authors)}
                  - B{.m} I{(list of MeSH keywords, descriptors and qualifiers)}
                  - B{.MD} I{(MesH Descriptors)}
                  - B{.MQ} I{(MesH Qualifiers, if any)}
                  - B{.MDMay} I{(list of Mayor MesH Descriptors, if any)}
                  - B{.MQMay} I{(list of Mayor MesH Qualifiers, if any)}
                  - B{.paper} I{(full text flat file if exists in user-defined repository

The Search method inside the DataContainer class is not working well, and should be rewritten  using better XML techniques and methods

A class (CreateXML) has been added recently to create the pubmed XML file from a list of PubMed ids. Has not been fully integrated with the data container class

Another class shoud be able to query keywords directly to pubmed, to either get the pubmed ids or the xml directly, using either BioPython's PubMed modules of directly through Eutil's facilities

""" 
#__docformat__ = 'epytext en'

# General info
__version__ = '5.0'
__author__ = 'Carlos Rodriguez'
__url__ = 'http://www.cnio.es'
__license__ = 'GNU'

from xml.dom.minidom import parseString
import string
import re
import os

class BioReader:
    """
    Class BioReader for BioMedical files
    """
    def __init__(self, string, path=None):
        """
        Initialize class with XML string  and returns record data and body of text objects.
        
            >>> single_record = BioReader(record)

            >>> single_record.title
            u'The birA gene of Escherichia coli encodes a biotin holoenzyme synthetase.'
         
            >>> single_record.pmid
            u'7024555'
            
        single_record +
           - B{.title}
           - B{.pmid}
           - B{.Abs} I{(abstracts)}
           - B{.year}
           - B{.journal}
           - B{.auth} I{(list of authors)}
           - B{.m} I{(list of MeSH keywords, descriptors and qualifiers)}
           - B{.MD} I{(MesH Descriptors)}
           - B{.MQ} I{(MesH Qualifiers, if any)}
           - B{.MDMay} I{(list of Mayor MesH Descriptors, if any)}
           - B{.MQMay} I{(list of Mayor MesH Qualifiers, if any)}
           - B{.paper} I{(full text flat file if exists in user-defined repository [see notes below])}
                  
        If we use a repository with full text papers (with pmid+<pmidnumber>+txt format), 
        we can use the following, after specifying it in the Data Container we instantiated:
        
             >>> data.Repository("/repositorio/Regulontxt/")

             >>> record = data.dictRecords['9209026']

             >>> single_record = BioReader(record,data.repository)# or directly inputing path, if it was  not done\\
                  through the DataContainer class: single_record = BioReader(record,'/path/to/repository/')

             >>> single_record.paper

             'Aerobic Regulation of the sucABCD Genes of Escherichia coli,Which Encode \xef\xbf\xbd-Ketoglutarate Dehydrogenase andSuccinyl Coenzyme A Synthetase: Roles of ArcA,Fnr, and the Upstream sdhCDAB Promoter\n.....'
             
        """
        self.tags = re.compile("<.*?>")
        self.parsed = parseString(string)
        self.document = self.parsed.documentElement
        self.pmid = self.document.getElementsByTagName("PMID")[0].firstChild.data
        self.year = self.document.getElementsByTagName("DateCreated")[0].getElementsByTagName("Year")[0].firstChild.data
        self.journal = self.document.getElementsByTagName("MedlineJournalInfo")[0].getElementsByTagName("MedlineTA")[0].firstChild.data
        self.testAbs = self.document.getElementsByTagName("Abstract")
        if path != None:
            self.path = path
            self.paper = self.GetFullPaper()
        else:
            self.path = None
            self.paper = None
        try:
            self.year = self.document.getElementsByTagName("PubDate")[0].getElementsByTagName("Year")[0].firstChild.data
        except IndexError:
            self.year = self.document.getElementsByTagName("DateCreated")[0].getElementsByTagName("Year")[0].firstChild.data
        try:
            self.Abs = self.document.getElementsByTagName("Abstract")[0].getElementsByTagName("AbstractText")[0].firstChild.data
        except IndexError:
            self.Abs = "n/a"
        self.title = self.document.getElementsByTagName("ArticleTitle")[0].firstChild.data
        try:
            self.authorsList = self.document.getElementsByTagName("AuthorList")[0].getElementsByTagName("Author")
            self.Lista = [self.authorize(y.childNodes) for y in self.authorsList]
            s = ""
            for x in self.Lista:
                s = s + x + "\n"
            self.auth = s
        except AttributeError:
            self.auth = " "
        except IndexError:
            self.auth = " "
        try:
            self.meshes = self.document.getElementsByTagName("MeshHeadingList")[0].getElementsByTagName("MeshHeading")
            self.ListaMs = [self.Meshes(z.childNodes) for z in self.meshes]
            self.MD = []
            self.MQ = []
            self.MDMay = []
            self.MQMay = []
            for z in self.meshes:
                MD,MQ,MDMay,MQMay = self.MeshKeys(z)
                self.MD = MD + self.MD
                self.MQ = MQ + self.MQ
                self.MDMay = MDMay + self.MDMay
                self.MQMay = MQMay + self.MQMay
                
            self.m = ""
            for x in self.ListaMs:
                self.m = x+" \n "+self.m
            #self.p = None
        except IndexError:
            self.m = "n/a"            
            self.meshes = "n/a"
            self.MQ = None
            self.MD = None
            self.MDMay = None
            self.MQMay = None
            #self.p = None
        #from DataContainer import repository
        #self.authors = string.join( self.Lista )#[self.authorize(x)+"\n" for x in self.Lista]
    def __repr__(self):
        return "<BioReader record instance: pmid: "+self.pmid+" title: "+self.title+" abstract: "+self.Abs+">"
    
    def authorize(self, node):
        s = ""
        for z in node:
            f = z.toxml()
            f = re.sub(self.tags,"",f)
            f  = re.sub("\n","",f)
            f  = re.sub("\t"," ",f)
            f  = re.sub("  ","",f)
            s = s + f+" "
        return s

    def Meshes(self, node):
        s = ""
        for z in node:
            f = z.toxml()
            f = re.sub(self.tags,"",f)
            f  = re.sub("\n","",f)
            f  = re.sub("\t"," ",f)
            f  = re.sub("  ","",f)
            s = s + f+" "
        return s

    def MeshKeys(self,node):
        """
        Create sets of MesH Keywords, separating qualifiers and descriptors, as well as //
        MajorTopics for each one. returns Lists.
        """
        listDescriptors = node.getElementsByTagName("DescriptorName")
        listQualifiers =  node.getElementsByTagName("QualifierName")
        MD = [x.firstChild.data for x in listDescriptors]
        MQ = [x.firstChild.data for x in listQualifiers]
        MQMay = [q.firstChild.data for q in listQualifiers if (q.getAttribute("MajorTopicYN") == "Y")]
        MDMay = [q.firstChild.data for q in listDescriptors if (q.getAttribute("MajorTopicYN") == "Y")]
        return MD,MQ,MDMay,MQMay
    def GetFullPaper(self):
        """
        Gets the full paper from the path of an (optional) repository.
        The full papers must have the following format:
        pmid+<pmidnumber>+.txt (last extension optional)
        """
        pmidList = os.listdir(self.path)
        if pmidList[0][-4:] == '.txt':
            pmidList = [x[4:-4] for x in pmidList]
            formato = 1
        else:
            pmidList = [x[4:] for x in pmidList]
            formato = None
        if self.pmid in pmidList:
            if formato:
                self.paper = open(self.path+"pmid"+self.pmid+".txt").read()
                return self.paper
            else:
                self.paper = open(self.path+"pmid"+self.pmid).read()
                return self.paper
        else:
            self.paper = None
        
        
class DataContainer:
    """
    Data container for Pubmed and Medline XML files.
    The instance creates a dictionary object (dictRecords) of PMIDs, 
    referenced to string of record, which BioReader class can parse. 
    The method C{Read} creates a queryable object for each record  assoicated with a PMID:

        >>> from BioReader import *
        >>> data = DataContainer('AllAbs.xml','pubmed')
        >>> data.dictRecords.keys()[23]
        >>> u'7024555'
        >>> data.howmany
        >>> 14350

    1) Method One

       >>> record = data.Read('7024555')
       >>> record.title

           u'The birA gene of Escherichia coli encodes a biotin holoenzyme synthetase.'
           record +
                  - B{.title}
                  - B{.pmid}
                  - B{.Abs} I{(abstracts)}
                  - B{.year}
                  - B{.journal}
                  - B{.auth} I{(list of authors)}
                  - B{.m} I{(list of MeSH keywords, descriptors and qualifiers)}
                  - B{.MD} I{(MesH Descriptors)}
                  - B{.MQ} I{(MesH Qualifiers, if any)}
                  - B{.MDMay} I{(list of Mayor MesH Descriptors, if any)}
                  - B{.MQMay} I{(list of Mayor MesH Qualifiers, if any)}
                  - B{.paper} I{(full text flat file if exists in user-defined repository [see notes below])}
    If we use a repository with full text papers 
    (with pmid+<pmidnumber>+txt format (extension optional), 
    we can use the following, after specifying it in the DataContainer we instantiated:
        
    >>> data.Repository("/repositorio/Regulontxt/")
    >>> record.paper

        'Aerobic Regulation of the sucABCD Genes of Escherichia coli, Which Encode \xef\xbf\xbd-Ketoglutarate Dehydrogenase andSuccinyl Coenzyme A Synthetase: Roles of ArcA,Fnr, and the Upstream sdhCDAB Promoter\n.....       

    2) Method two
        
    >>> record = data.dictRecords['7024555']
    >>> single_record = BioReader(record)
    >>> single_record.title
    >>> u'The birA gene of Escherichia coli encodes a biotin holoenzyme synthetase.'   etc ...

    (See L{BioReader})
    """
    def __init__(self,file,format="medline"):
        """
        Initializes class and returns record data and body of text objects
        """
        import time
        tinicial = time.time()
        self.file = file
        whole = open(self.file).read()
        if format.lower() == "medline":
            self.rerecord = re.compile(r'\<MedlineCitation Owner="NLM" Status="MEDLINE"\>'r'(?P<record>.+?)'r'\</MedlineCitation\>',re.DOTALL)
        elif format.lower() == "pubmed":
            self.rerecord  = re.compile(r'\<PubmedArticle\>'r'(?P<record>.+?)'r'\</PubmedArticle\>',re.DOTALL)
        else:
            print "Unrecognized format"
        self.RecordsList = re.findall(self.rerecord,whole)
        whole = ""
        self.RecordsList =  ["<PubmedArticle>"+x.rstrip()+"</PubmedArticle>" for x in self.RecordsList]
        self.dictRecords = self.Createdict()
        self.RecordsList = []
        self.howmany = len(self.dictRecords.keys())
        self.keys = self.dictRecords.keys()
        tfinal = time.time()
        self.repository = None
        print "finished loading at ",time.ctime(tfinal)
        print "loaded in", tfinal-tinicial," seconds, or",((tfinal-tinicial)/60)," minutes"
    def __repr__(self):
        return "<BioReader Data Container Instance: source filename: "+self.file+" \nnumber of files: "+str(self.howmany)+">"

    def Repository(self,repository):
        """
        Establish path to a full text repository, in case you want to use that variable in the BioReader 
        """
        self.repository = repository
        return self.repository
    def Createdict(self):
        """
        Creates a dictionary with pmid number indexing record xml string
        """
        i = 0
        dictRecords = {}
        for p in self.RecordsList:
            r = BioReader(p)
            dictRecords[r.pmid] = self.RecordsList[i]
            i += 1
        return dictRecords

    def Read(self,pmid):
        if self.repository:
            self.record = BioReader(self.dictRecords[pmid],self.repository)
        else:
            self.record = BioReader(self.dictRecords[pmid])
        return self.record

    def Search(self,cadena,where=None):
        """
        This method is not working. Needs to be redone to comply with more up-to-date XML search methods
        Searches for "cadena" string inside the selected field, and returns a list of pmid where it was found.

        If not "where" field is provided, will search in all of the record.
        You can search in the following fields:
         - title
         - year
         - journal
         - auth or authors
         - 'abs' or 'Abs' or 'abstract'
         - paper or "full" (if full-text repository has been defined)
         - pmid

        With defined field search is very slow but much more accurate. See for comparison:
        
        >>> buscados = data.Search("Richard")
        
            Searched in 0.110424995422  seconds, or 0.00184041659037  minutes

            Found a total of  75  hits for your query, in all fields

            >>> buscados = data.Search("Richard","auth")

                Searched in 66.342936039  seconds, or 1.10571560065  minutes

                Found a total of  75  hits for your query, in the  auth  field
        """
        tinicial = time.time()
        resultlist = []
        if where:
            for cadapmid in self.dictRecords.keys():
                d = self.Read(cadapmid)
                if where == 'title':
                    tosearch = d.title
                elif where == 'year':
                    tosearch = d.year
                elif where == 'journal':
                    tosearch = d.journal
                elif where == ('auth' or 'authors'):
                    tosearch = d.auth
                elif where == ('m' or 'mesh'):
                    tosearch = d.m
                elif where == ('abs' or 'Abs' or 'abstract'):
                    tosearch = d.Abs
                elif where == ('paper' or 'full'):
                    tosearch = d.paper
                    if self.repository:
                        pass
                    else:
                        print "No full text repository has been defined...."
                        return None
                elif where == 'pmid':
                    tosearch = d.pmid
                hit = re.search(cadena,tosearch)
                if hit:
                    resultlist.append(d.pmid)
                else:
                    pass
            if len(resultlist)!= 0:
                tfinal = time.time()
                print "Searched in", tfinal-tinicial," seconds, or",((tfinal-tinicial)/60)," minutes"
                print "Found a total of ",str(len(resultlist))," hits for your query, in the ",where," field"
                return resultlist
            else:
                print "Searched in", tfinal-tinicial," seconds, or",((tfinal-tinicial)/60)," minutes"
                print "Query not found"
                return None
        else:
            tosearch = ''
            for cadapmid in self.dictRecords.keys():
                tosearch = self.dictRecords[cadapmid]
                hit = re.search(cadena,tosearch)
                if hit:
                    resultlist.append(cadapmid)
                else:
                    pass
        if len(resultlist)!= 0:
            tfinal = time.time()
            print "Searched in", tfinal-tinicial," seconds, or",((tfinal-tinicial)/60)," minutes"
            print "Found a total of ",str(len(resultlist))," hits for your query, in all fields"
            return resultlist
        else:
            tfinal = time.time()
            print "Searched in", tfinal-tinicial," seconds, or",((tfinal-tinicial)/60)," minutes"
            print "Query not found"
            return None
                

class CreateXML:
    
    """
    Class to generate PubMed XMLs from a list of ids (one per line), to use with BioRea.
    downloads in 100 batch.
    Usage:

    outputfile = "NuevosPDFRegulon.xml"
    inputfile = "/home/crodrigp/listaNuevos.txt"
       >>> XMLCreator = CreateXML()
       >>> XMLCreator.GenerateFile(inputfile,outputfile)
       >>> parseableString = XMLCreator.Generate2String(inputfile)

       or
       >>> XMLString = XMLCreator.Generate2String()

    """
    def __init__(self):
        #global urllib,time,string,random
        import urllib,time,string,random
 
    def getXml(self,s):
        pedir = urllib.urlopen("http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id="+s+"&retmode=xml")
        stringxml = pedir.read()
        self.salida.write(stringxml[:-20]+"\n")
        
    def getXmlString(self,s):
        pedir = urllib.urlopen("http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id="+s+"&retmode=xml")
        stringxml = pedir.read()
        return stringxml[:-20]+"\n"
    
    def listastring(self,list):
        suso = string.join(list,",")
        return suso

    def GenerateFile(self,inputfile,outputfile):
        self.outputfile = outputfile
        self.inputfile = inputfile
        self.salida = open(self.outputfile,"w")
        self.listaR = open(self.inputfile).readlines()
        self.listafin = [x.rstrip() for x in self.listaR]
        self.listacorr = []
        while self.listafin != []:
            if len(self.listafin) < 100:
                cientos = self.listafin[:]
                #self.listafin = []
            else:
                cientos = self.listafin[:100]


            print "new length self.listacorr", len(self.listafin)
            if len(self.listafin) <= 0:
                break
            else:
                #time.sleep(120)
                nueva = self.listastring(cientos)
                self.getXml(nueva)
            for c in cientos:
                print c
                self.listafin.remove(c)
        self.salida.close()

    def Generate2String(self,inputfile):
        self.inputfile = inputfile
        self.listaR = open(self.inputfile).readlines()
        self.AllXML = ''
        self.listafin = [x.rstrip() for x in self.listaR]
        self.listacorr = []
        while self.listafin != []:
            if len(self.listafin) < 100:
                cientos = self.listafin[:]
                #self.listafin = []
            else:
                cientos = self.listafin[:100]


            print "new length self.listacorr", len(self.listafin)
            if len(self.listafin) <= 0:
                break
            else:
                time.sleep(120)
                nueva = self.listastring(cientos)
                newX = self.getXmlString(nueva)
                self.AllXML = self.AllXML + newX
            for c in cientos:
                print c
                self.listafin.remove(c)
        return self.AllXML
