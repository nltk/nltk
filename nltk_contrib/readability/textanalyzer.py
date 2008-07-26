#!/usr/bin/python
# -*- coding: utf-8 -*- 
# Sets the encoding to utf-8 to avoid problems with æøå
import nltk.data
from nltk.tokenize import *
import syllables_en
import syllables_no
from languageclassifier import *

class textanalyzer(object):

    tokenizer = RegexpTokenizer('(?u)\W+|\$[\d\.]+|\S+')
    special_chars = ['.', ',', '!', '?']
    lang = "eng"
    
    def __init__(self, lang):
        self.lang = lang
    
    def setLang(self,lang):
        self.lang = lang

    def analyzeText(self, text=''):
        words = self.getWords(text)
        charCount = self.getCharacterCount(words)
        wordCount = len(words)
        sentenceCount = len(self.getSentences(text))
        syllablesCount = self.countSyllables(words)
        complexwordsCount = self.countComplexWords(text)
        averageWordsPerSentence = wordCount/sentenceCount
        print ' Language: ' + self.lang
        print ' Number of characters: ' + str(charCount)
        print ' Number of words: ' + str(wordCount)
        print ' Number of sentences: ' + str(sentenceCount)
        print ' Number of syllables: ' + str(syllablesCount)
        print ' Number of complex words: ' + str(complexwordsCount)
        print ' Average words per sentence: ' + str(averageWordsPerSentence)
    #analyzeText = classmethod(analyzeText)  
        

    def getCharacterCount(self, words):
        characters = 0
        for word in words:
            word = self._setEncoding(word)
            characters += len(word.decode("utf-8"))
        return characters
    #getCharacterCount = classmethod(getCharacterCount)    
        
    def getWords(self, text=''):
        text = self._setEncoding(text)
        words = []
        words = self.tokenizer.tokenize(text)
        filtered_words = []
        for word in words:
            if word in self.special_chars or word == " ":
                pass
            else:
                new_word = word.replace(",","").replace(".","")
                new_word = new_word.replace("!","").replace("?","")
                filtered_words.append(new_word)
        return filtered_words
    #getWords = classmethod(getWords)
    
    def getSentences(self, text=''):
        sentences = []
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
        sentences = tokenizer.tokenize(text)
        return sentences
    #getSentences = classmethod(getSentences)
    
    def countSyllables(self, words = []):
#        if self.lang == "":
#            self.lang = NaiveBayes().classifyText(" " .join(words))
            
        if self.lang == "unknown":
            print "WARNING: Unknown language, using English\n"
            self.lang = "eng"    
        
        syllableCount = 0
        syllableCounter = {}
        syllableCounter['eng'] = syllables_en.count
        syllableCounter['no'] = syllables_no.count
        for word in words:
            syllableCount += syllableCounter[self.lang](word)
            
        return syllableCount
    #countSyllables = classmethod(countSyllables)
    
    
    #This method must be enhanced. At the moment it only
    #considers the number of syllables in a word.
    #This often results in that too many complex words are detected.
    def countComplexWords(self, text=''):
        words = self.getWords(text)
        sentences = len(self.getSentences(text));
        sentencesList = self.getSentences(text);
        complexWords = 0
        found = False;
        #Just for manual checking and debugging.
        cWords = []
        curWord = []
        
        for word in words:          
            curWord.append(word)
            if self.countSyllables(curWord)>= 3:
                
                #Checking proper nouns. If a word starts with a capital letter
                #and is NOT at the beginning of a sentence we don't add it
                #as a complex word.
                if not(word[0].isupper()):
                    complexWords += 1
                    #cWords.append(word)
                else:
                    for sentence in sentencesList:
                        if str(sentence).startswith(word):
                            found = True
                            break
                    
                    if found: 
                        complexWords+=1
                        found = False
                    
            curWord.remove(word)
        #print cWords
        return complexWords
    #countComplexWords = classmethod(countComplexWords)
    
    def _setEncoding(self,text):
        try:
            text = unicode(text, "utf8").encode("utf8")
        except UnicodeError:
            try:
                text = unicode(text, "iso8859_1").encode("utf8")
            except UnicodeError:
                text = unicode(text, "ascii", "replace").encode("utf8")
        return text
    #_setEncoding = classmethod(_setEncoding)
        
        
    def demo(self):
#        text = "It is for us the living, rather,\
#                \nto be dedicated here to the unfinished\
#                \nwork which they who fought here have\
#                \nthus far so nobly advanced. It is\
#                \nrather for us to be here dedicated\
#                \nto the great task remaining before us,\
#                \nthat from these honored dead we take\
#                \nincreased devotion to that cause for which they\
#                \ngave the last full measure of devotion, that we\
#                \nhere highly resolve that these dead shall not have\
#                \ndied in vain, that this nation, under God, shall have a\
#                \nnew birth of freedom, and that government of the people, by\
#                \nthe people, for the people, shall not perish from this earth."
        text = "Den 10. desember 1948 vedtok og kunngjorde De Forente Nasjoners tredje Generalforsamling Verdenserklæringen om Menneskerettighetene. Erklæringen ble vedtatt med 48 lands ja-stemmer. Ingen land stemte mot. 8 land avsto. Umiddelbart etter denne historiske begivenhet henstilte Generalforsamlingen til alle medlemsstater å bekjentgjøre Erklæringens tekst og sørge for at den blir distribuert, framvist, lest og forklart spesielt i skoler og andre læreinstitusjoner, uten hensyn til de forskjellige lands eller områders politiske status. Erklæringens offisielle tekst foreligger på FNs seks arbeidsspråk: arabisk, engelsk, fransk, kinesisk, russisk og spansk. En lang rekke av FNs medlemsstater har fulgt Generalforsamlingens oppfordring og oversatt Erklæringen til de nasjonale språk. Denne oversettelsen til norsk er utarbeidet i Utenriksdepartementet. På henvendelse til FNs nordiske informasjonskontor i København kan en få gratis eksemplarer av Erklæringen på FNs offisielle språk, de øvrige nordiske språk og et begrenset antall andre språk. VERDENSERKLÆRINGEN OM MENNESKERETTIGHETENE INNLEDNING Da anerkjennelsen av menneskeverd og like og umistelige rettigheter for alle medlemmer av menneskeslekten er grunnlaget for frihet, rettferdighet og fred i verden, da tilsidesettelse av og forakt for menneskerettighetene har ført til barbariske handlinger som har rystet menneskehetens samvittighet, og da framveksten av en verden hvor menneskene har tale- og trosfrihet og frihet fra frykt og nød, er blitt kunngjort som folkenes høyeste mål, da det er nødvendig at menneskerettighetene blir beskyttet av loven for at menneskene ikke skal tvinges til som siste utvei å gjøre opprør mot tyranni og undertrykkelse, da det er viktig å fremme utviklingen av vennskapelige forhold mellom nasjonene, da De Forente Nasjoners folk i Pakten på ny har bekreftet sin tro på grunnleggende menneskerettigheter, på menneskeverd og på like rett for menn og kvinner og har besluttet å arbeide for sosialt framskritt og bedre levevilkår under større Frihet, da medlemsstatene har forpliktet seg til i samarbeid med De Forente Nasjoner å sikre at menneskerettighetene og de grunnleggende friheter blir alminnelig respektert og overholdt, da en allmenn forståelse av disse rettigheter og friheter er av den største betydning for å virkeliggjøre denne forpliktelse, kunngjør GENERALFORSAMLINGEN nå denne VERDENSERKLÆRING OM MENNESKERETTIGHETENE som et felles mål for alle folk og alle nasjoner, for at hvert individ og hver samfunnsmyndighet, med denne erklæring stadig i tankene, skal søke gjennom undervisning og oppdragelse å fremme respekt for disse rettigheter og friheter, og ved nasjonale og internasjonale tiltak å sikre at de blir allment og effektivt anerkjent og overholdt både blant folkene i medlemsstatene selv og blant folkene i de områder som står under deres overhøyhet. Artikkel 1. Alle mennesker er født frie og med samme menneskeverd og menneskerettigheter. De er utstyrt med fornuft og samvittighet og bør handle mot hverandre i brorskapets ånd. Artikkel 2. Enhver har krav på alle de rettigheter og friheter som er nevnt i denne erklæring, uten forskjell av noen art, f. eks. på grunn av rase, farge, kjønn, språk, religion, politisk eller annen oppfatning, nasjonal eller sosial opprinnelse eiendom, fødsel eller annet forhold. Det skal heller ikke gjøres noen forskjell på grunn av den politiske, rettslige eller internasjonale stilling som innehas av det land eller det område en person hører til, enten landet er uavhengig, står under tilsyn, er ikke-selvstyrende, eller på annen måte har begrenset suverenitet. Artikkel 3. Enhver har rett til liv, frihet og personlig sikkerhet. Artikkel 4. Ingen må holdes i slaveri eller trelldom. Slaveri og slavehandel i alle former er forbudt. Artikkel 5. Ingen må utsettes for tortur eller grusom, umenneskelig eller nedverdigende behandling eller straff. Artikkel 6. Ethvert menneske har krav på overalt å bli anerkjent som rettssubjekt. Artikkel 7. Alle er like for loven og har uten diskriminering rett til samme beskyttelse av loven. Alle har krav på samme beskyttelse mot diskriminering i strid med denne erklæring og mot enhver oppfordring til slik diskriminering. Artikkel 8. Enhver har rett til effektiv hjelp av de kompetente nasjonale domstoler mot handlinger som krenker de grunnleggende rettigheter han er gitt i forfatning eller lov. Artikkel 9. Ingen må utsettes for vilkårlig arrest, fengsling eller landsforvisning. Artikkel 10. Enhver har krav på under full likestilling å få sin sak rettferdig og offentlig behandlet av en uavhengig og upartisk domstol når hans rettigheter og plikter skal fastsettes,og når en straffeanklage mot ham skal avgjøres. Artikkel 11. 1. Enhver som er anklaget for en straffbar handling har rett til å bli ansett som uskyldig til det er bevist ved offentlig domstolsbehandling, hvor han har hatt alle de garantier som er nødvendig for hans forsvar, at han er skyldig etter loven. 2. Ingen må dømmes for en handling eller unnlatelse som i henhold til nasjonal lov eller folkeretten ikke var straffbar på den tid da den ble begått. Heller ikke skal det kunne idømmes strengere straff enn den som det var hjemmel for på den tid da den straffbare handling ble begått. Artikkel 12. Ingen må utsettes for vilkårlig innblanding i privatliv, familie, hjem og korrespondanse, eller for angrep på ære og anseelse. Enhver har rett til lovens beskyttelse mot slik innblanding eller slike angrep. Artikkel 13. 1. Enhver har rett til å bevege seg fritt og til fritt å velge oppholdssted innenfor en stats grenser. 2. Enhver har rett til å forlate et hvilket som helst land innbefattet sitt eget og til å vende tilbake til sitt land. Artikkel 14. 1. Enhver har rett til i andre land å søke og ta imot asyl mot forfølgelse. 2. Denne rett kan ikke påberopes ved rettsforfølgelse som har reelt grunnlag i upolitiske forbrytelser eller handlinger som strider mot De Forente Nasjoners formål og prinsipper. Artikkel 15. 1. Enhver har rett til et statsborgerskap. Ingen skal vilkårlig berøves sitt statsborgerskap eller nektes retten til å forandre det. Artikkel 16. 1. Voksne menn og kvinner har rett til å gifte seg og stifte familie uten noen begrensning som skyldes rase, nasjonalitet eller religion. De har krav på like rettigheter ved inngåelse av ekteskapet, under ekteskapet og ved dets oppløsning. 2. Ekteskap må bare inngås etter fritt og fullt samtykke av de vordende ektefeller. 3. Familien er den naturlige og grunnleggende enhet i samfunnet og har krav på samfunnets og statens beskyttelse. Artikkel 17. 1. Enhver har rett til å eie eiendom alene eller sammen med andre. 2. Ingen må vilkårlig fratas sin eiendom. Artikkel 18. Enhver har rett til tanke-, samvittighets- og religionsfrihet. Denne rett omfatter frihet til å skifte religion eller tro, og frihet til enten alene eller sammen med andre, og offentlig eller privat, å gi uttrykk for sin religion eller tro gjennom undervisning, utøvelse, tilbedelse og ritualer. Artikkel 19. Enhver har rett til menings- og ytringsfrihet. Denne rett omfatter frihet til å hevde meninger uten innblanding og til å søke, motta og meddele opplysninger og ideer gjennom ethvert meddelelsesmiddel og uten hensyn til landegrenser. Artikkel 20. 1. Enhver har rett til fritt å delta i fredelige møter og organisasjoner. 2. Ingen må tvinges til å tilhøre en organisasjon. Artikkel 21. 1. Enhver har rett til å ta del i sitt lands styre, direkte eller gjennom fritt valgte representanter. 2. Enhver har rett til lik adgang til offentlig tjeneste i sitt land. 3. Folkets vilje skal være grunnlaget for offentlig myndighet. Denne vilje skal komme til uttrykk gjennom periodiske og reelle valg med allmenn og lik stemmerett og med hemmelig avstemning eller likeverdig fri stemmemåte. Artikkel 22. Enhver har som medlem av samfunnet rett til sosial trygghet og har krav på at de økonomiske, sosiale og kulturelle goder som er uunnværlige for hans verdighet og den frie utvikling av hans personlighet, blir skaffet til veie gjennom nasjonale tiltak og internasjonalt samarbeid i samsvar med hver enkelt stats organisasjon og ressurser. Artikkel 23. 1. Enhver har rett til arbeid, til fritt valg av yrke, til rettferdige og gode arbeidsforhold og til beskyttelse mot arbeidsløshet. 2. Enhver har uten diskriminering rett til lik betaling for likt arbeid. 3. Enhver som arbeider har rett til en rettferdig og god betaling som sikrer hans familie og ham selv en menneskeverdig tilværelse, og som om nødvendig blir utfylt ved annen sosial beskyttelse. 4. Enhver har rett til å danne og gå inn i fagforeninger for å beskytte sine interesser. Artikkel 24. Enhver har rett til hvile og fritid, herunder rimelig begrensning av arbeidstiden og regelmessige ferier med lønn. Artikkel 25. 1. Enhver har rett til en levestandard som er tilstrekkelig for hans og hans families helse og velvære, og som omfatter mat, klær, bolig og helseomsorg og nødvendige sosiale ytelser, og rett til trygghet i tilfelle av arbeidsløshet, sykdom, arbeidsuførhet, enkestand, alderdom eller annen mangel på eksistensmuligheter som skyldes forhold han ikke er herre over. 2. Mødre og barn har rett til spesiell omsorg og hjelp. Alle barn skal ha samme sosiale beskyttelse enten de er født i eller utenfor ekteskap. Artikkel 26. 1. Enhver har rett til undervisning. Undervisningen skal være gratis, i det minste på de elementære og grunnleggende trinn. Elementærundervisning skal være obligatorisk. Alle skal ha adgang til yrkesopplæring, og det skal være lik adgang for alle til høyere undervisning på grunnlag av kvalifikasjoner. 2. Undervisningen skal ta sikte på å utvikle den menneskelige personlighet og styrke respekten for menneskerettighetene og de grunnleggende friheter. Den skal fremme forståelse, toleranse og vennskap mellom alle nasjoner og rasegrupper eller religiøse grupper og skal støtte De Forente Nasjoners arbeid for å opprettholde fred. 3. Foreldre har fortrinnsrett til å bestemme hva slags undervisning deres barn skal få. Artikkel 27. 1. Enhver har rett til fritt å delta i samfunnets kulturelle liv, til å nyte kunst og til å få del i den vitenskapelige framgang og dens goder. 2. Enhver har rett til beskyttelse av de åndelige og materielle interesser som er et resultat av ethvert vitenskapelig, litterært eller kunstnerisk verk som han har skapt. Artikkel 28. Enhver har krav på en sosial og internasjonal orden som fullt ut kan virkeliggjøre de rettigheter og friheter som er nevnt i denne erklæring. Artikkel 29. 1. Enhver har plikter overfor samfunnet som alene gjør den frie og fulle utvikling av hans personlighet mulig. 2. Under utøvelsen av sine rettigheter og friheter skal enhver bare være undergitt slike begrensninger som er fastsatt i lov utelukkende med det formål å sikre den nødvendige anerkjennelse av og respekt for andres rettigheter og friheter, og de krav som moralen, den offentlige orden og den alminnelige velferd i et demokratisk samfunn med rette stiller. 3. Disse rettigheter og friheter må ikke i noe tilfelle utøves i strid med De Forente Nasjoners formål og prinsipper. Artikkel 30. Intet i denne erklæring skal tolkes slik at det gir noen stat, gruppe eller person rett til å ta del i noen virksomhet eller foreta noen handling som tar sikte på å ødelegge noen av de rettigheter og friheter som er nevnt i Erklæringen." 

        print "The text : \n" + ("=" * 40)
        print text
        print ("=" * 40) + "\nHas the following statistics\n" + ("=" * 40)
        nb = NaiveBayes()
        ta = textanalyzer(nb.classifyText(text))
        ta.analyzeText(text)
        pass
    demo = classmethod(demo)
    
def demo():
    textanalyzer.demo()
    
if __name__ == "__main__":
    textanalyzer.demo()
    
        
        
        
        
        
    
    
