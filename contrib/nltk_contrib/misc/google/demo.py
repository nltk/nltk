from SOAPpy import SOAPProxy
from SOAPpy import Types

# CONSTANTS
_url = 'http://api.google.com/search/beta2'
_namespace = 'urn:GoogleSearch'

# need to marshall into SOAP types
SOAP_FALSE = Types.booleanType(0)
SOAP_TRUE = Types.booleanType(1)

# create SOAP proxy object
google = SOAPProxy(_url, _namespace)

# Google search options
_license_key = 'REPLACE THIS WITH LICENSE KEY'
_query = 'spotted owl'
_start = 0
_maxResults = 10
_filter = SOAP_FALSE
_restrict = ''
_safeSearch = SOAP_FALSE
_lang_restrict = ''

# call search method over SOAP proxy
results = google.doGoogleSearch( _license_key, _query, 
                                 _start, _maxResults, 
                                 _filter, _restrict,
                                 _safeSearch, _lang_restrict, '', '' )
           
# display results
print 'google search for  " ' + _query + ' "\n'
print 'estimated result count: ' + str(results.estimatedTotalResultsCount)
print '           search time: ' + str(results.searchTime) + '\n'
print 'results ' + str(_start + 1) + ' - ' + str(_start + _maxResults) +':\n'
                                                       
numresults = len(results.resultElements)
for i in range(numresults):
    title = results.resultElements[i].title
    noh_title = title.replace('<b>', '').replace('</b>', '')
    print 'title: ' + noh_title
    print '  url: ' + results.resultElements[i].URL + '\n'
