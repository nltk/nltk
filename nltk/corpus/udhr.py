# Natural Language Toolkit: UDHR Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Sam Huston <shuston@students.csse.unimelb.edu.au>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read tokens from UDHR Corpus

This corpus contains examples of text in over 300 language/encoding combinations,
from the Universal Declaration of Human Rights
"""

import os
from util import *
from nltk import tokenize

documents = ['Abkhaz-Cyrillic+Abkh', 'Abkhaz-UTF8', 'Achehnese-Latin1', 'Achuar-Shiwiar-Latin1', 'Adja-UTF8',
         'Afaan_Oromo_Oromiffa-Latin1', 'Afrikaans-Latin1', 'Aguaruna-Latin1', 'Akuapem_Twi-UTF8',
         'Albanian_Shqip-Latin1', 'Amahuaca-Latin1', 'Amahuaca', 'Amarakaeri-Latin1',
         'Amharic-Afenegus6..60375', 'Amuesha-Yanesha-UTF8', 'Arabela-Latin1', 'Arabic_Alarabia-Arabic',
         'Armenian-DallakHelv', 'Asante-UTF8', 'Ashaninca-Latin1', 'Asheninca-Latin1', 'Asturian_Bable-Latin1',
         'Aymara-Latin1', 'Azeri_Azerbaijani_Cyrillic-Az.Times.Cyr.Normal0117',
         'Azeri_Azerbaijani_Latin-Az.Times.Lat0117', 'Balinese-Latin1', 'Bambara-UTF8',
         'Baoule-UTF8', 'Basque_Euskara-Latin1', 'Batonu_Bariba-UTF8', 'Belorus_Belaruski-Cyrillic',
         'Belorus_Belaruski-UTF8', 'Bemba-Latin1', 'Bengali-UTF8', 'Beti-UTF8', 'Bhojpuri-Agra',
         'Bichelamar-Latin1', 'Bikol_Bicolano-Latin1', 'Bora-Latin1', 'Bosnian_Bosanski-Cyrillic',
         'Bosnian_Bosanski-Latin2', 'Bosnian_Bosanski-UTF8', 'Breton-Latin1', 'Bugisnese-Latin1',
         'Bulgarian_Balgarski-Cyrillic', 'Bulgarian_Balgarski-UTF8', 'Burmese_Myanmar-UTF8',
         'Burmese_Myanmar-WinResearcher', 'Cakchiquel-Latin1', 'Campa_Pajonalino-Latin1',
         'Candoshi-Shapra-Latin1', 'Caquinte-Latin1', 'Cashibo-Cacataibo-Latin1', 'Cashinahua-Latin1',
         'Catalan_Catala-Latin1', 'Catalan-Latin1', 'Cebuano-Latin1', 'Chamorro-Latin1', 'Chayahuita-Latin1',
         'Chechewa_Nyanja-Latin1', 'Chickasaw-Latin1', 'Chinanteco-Ajitlan-Latin1', 'Chinanteco-UTF8',
         'Chinese_Mandarin-GB2312', 'Chinese_Mandarin-HZ', 'Chinese_Mandarin-UTF8', 'Chuuk_Trukese-Latin1',
         'Cokwe-Latin1', 'Corsican-Latin1', 'Croatian_Hrvatski-Latin2', 'Czech_Cesky-Latin2', 'Czech_Cesky-UTF8',
         'Czech-Latin2-err', 'Czech-Latin2', 'Czech-UTF8', 'Dagaare-UTF8', 'Dagbani-UTF8', 'Dangme-UTF8',
         'Danish_Dansk-Latin1', 'Dendi-UTF8', 'Ditammari-UTF8', 'Dutch_Nederlands-Latin1', 'Edo-Latin1',
         'English-Latin1', 'Esperanto-T61', 'Esperanto-UTF8', 'Estonian_Eesti-Latin1', 'Ewe_Eve-UTF8',
         'Fante-UTF8', 'Faroese-Latin1', 'Farsi_Persian-UTF8', 'Farsi_Persian-v2-UTF8', 'Fijian-Latin1',
         'Filipino_Tagalog-Latin1', 'Finnish_Suomi-Latin1', 'Fon-UTF8', 'French_Francais-Latin1',
         'Frisian-Latin1', 'Friulian_Friulano-Latin1', 'Gagauz_Gagauzi-UTF8', 'Galician_Galego-Latin1',
         'Garifuna_Garifuna-Latin1', 'Ga-UTF8', 'German_Deutsch-Latin1', 'Gonja-UTF8', 'Greek_Ellinika-Greek',
         'Greek_Ellinika-UTF8', 'Greenlandic_Inuktikut-Latin1', 'Guarani-Latin1', 'Guen_Mina-UTF8',
         'Gujarati-UTF8', 'HaitianCreole_Kreyol-Latin1', 'HaitianCreole_Popular-Latin1', 'Hani-Latin1',
         'Hausa_Haoussa-Latin1', 'Hawaiian-UTF8', 'Hebrew_Ivrit-Hebrew', 'Hebrew_Ivrit-UTF8', 'Hiligaynon-Latin1',
         'Hindi-UFT8', 'Hindi_web-UFT8', 'Hmong_Miao_Northern-East-Guizhou-Latin1',
         'Hmong_Miao-Sichuan-Guizhou-Yunnan-Latin1', 'Hmong_Miao-SouthernEast-Guizhou-Latin1',
         'Hrvatski_Croatian-Latin2', 'Huasteco-Latin1', 'Huitoto_Murui-Latin1', 'Hungarian_Magyar-Latin1',
         'Hungarian_Magyar-Latin2', 'Hungarian_Magyar-Unicode', 'Hungarian_Magyar-UTF8', 'Ibibio_Efik-Latin1',
         'Icelandic_Yslenska-Latin1', 'Ido-Latin1', 'Igbo-UTF8', 'Iloko_Ilocano-Latin1', 'Indonesian-Latin1',
         'Interlingua-Latin1', 'Inuktikut_Greenlandic-Latin1', 'IrishGaelic_Gaeilge-Latin1', 'Italian_Italiano-Latin1',
         'Italian-Latin1', 'Japanese_Nihongo-EUC', 'Japanese_Nihongo-JIS', 'Japanese_Nihongo-SJIS',
         'Japanese_Nihongo-UTF8', 'Javanese-Latin1', 'Jola-Fogny_Diola-UTF8', 'Kabye-UTF8', 'Kannada-UTF8',
         'Kaonde-Latin1', 'Kapampangan-Latin1', 'Kasem-UTF8', 'Kazakh-Cyrillic', 'Kazakh-UTF8', 'Kiche_Quiche-Latin1',
         'Kicongo-Latin1', 'Kimbundu_Mbundu-Latin1', 'Kinyamwezi_Nyamwezi-Latin1', 'Kinyarwanda-Latin1', 'Kituba-Latin1',
         'Korean_Hankuko-UTF8', 'Kpelewo-UTF8', 'Krio-UTF8', 'Kurdish-UTF8', 'Lamnso_Lam-nso-UTF8', 'Lao-UTF8',
         'Latin_Latina-Latin1', 'Latin_Latina-v2-Latin1', 'Latvian-Latin1', 'Limba-UTF8', 'Lingala-Latin1',
         'Lithuanian_Lietuviskai-Baltic', 'Lozi-Latin1', 'Luba-Kasai_Tshiluba-Latin1', 'Luganda_Ganda-Latin1',
         'Lunda_Chokwe-lunda-Latin1', 'Luvale-Latin1', 'Luxembourgish_Letzebuergeusch-Latin1', 'Macedonian-UTF8',
         'Madurese-Latin1', 'Magahi-Agra', 'Magahi-UTF8', 'Makonde-Latin1', 'Malagasy-Latin1',
         'Malay_BahasaMelayu-Latin1', 'Maltese-UTF8', 'Mam-Latin1', 'Maninka-UTF8', 'Maori-Latin1',
         'Mapudungun_Mapuzgun-Latin1', 'Mapudungun_Mapuzgun-UTF8', 'Marathi-UTF8', 'Marshallese-Latin1',
         'Matses-Latin1', 'Mayan_Yucateco-Latin1', 'Mazahua_Jnatrjo-UTF8', 'Mazateco-Latin1', 'Mende-UTF8',
         'Mikmaq_Micmac-Mikmaq-Latin1', 'Minangkabau-Latin1', 'Miskito_Miskito-Latin1', 'Mixteco-Latin1',
         'Mongolian_Khalkha-Cyrillic', 'Mongolian_Khalkha-UTF8', 'Moore_More-UTF8', 'Nahuatl-Latin1',
         'Navaho_Dine-Navajo-Navaho-font', 'Ndebele-Latin1', 'Nepali-UTF8', 'Ngangela_Nyemba-Latin1',
         'NigerianPidginEnglish-Latin1', 'Nomatsiguenga-Latin1', 'NorthernSotho_Pedi-Sepedi-Latin1',
         'Norwegian-Latin1', 'Norwegian_Norsk-Bokmal-Latin1', 'Norwegian_Norsk-Nynorsk-Latin1', 'Nyanja_Chechewa-Latin1',
         'Nyanja_Chinyanja-Latin1', 'Nzema-UTF8', 'OccitanAuvergnat-Latin1', 'OccitanLanguedocien-Latin1',
         'Oromiffa_AfaanOromo-Latin1', 'Osetin_Ossetian-UTF8', 'Oshiwambo_Ndonga-Latin1', 'Otomi_Nahnu-Latin1',
         'Paez-Latin1', 'Palauan-Latin1', 'Peuhl-UTF8', 'Picard-Latin1', 'Pipil-Latin1', 'Polish-Latin2',
         'Polish_Polski-Latin2', 'Ponapean-Latin1', 'Portuguese_Portugues-Latin1', 'Pulaar-UTF8',
         'Punjabi_Panjabi-UTF8', 'Purhepecha-UTF8', 'Qechi_Kekchi-Latin1', 'Quechua-Latin1', 'Quichua-Latin1',
         'Rarotongan_MaoriCookIslands-Latin1', 'Rhaeto-Romance_Rumantsch-Latin1', 'Romanian-Latin2',
         'Romanian_Romana-Latin2', 'Romani-Latin1', 'Romani-UTF8', 'Rukonzo_Konjo-Latin1', 'Rundi_Kirundi-Latin1',
         'Runyankore-rukiga_Nkore-kiga-Latin1', 'Russian-Cyrillic', 'Russian_Russky-Cyrillic', 'Russian_Russky-UTF8',
         'Russian-UTF8', 'Sami_Lappish-UTF8', 'Sammarinese-Latin1', 'Samoan-Latin1', 'Sango_Sangho-Latin1',
         'Sanskrit-UTF8', 'Saraiki-UTF8', 'Sardinian-Latin1', 'ScottishGaelic_GaidhligAlbanach-Latin1',
         'Seereer-UTF8', 'Serbian_Srpski-Cyrillic', 'Serbian_Srpski-Latin2', 'Serbian_Srpski-UTF8',
         'Sharanahua-Latin1', 'Shipibo-Conibo-Latin1', 'Shona-Latin1', 'Sinhala-UTF8', 'Siswati-Latin1',
         'Slovak-Latin2', 'Slovak_Slovencina-Latin2', 'Slovenian_Slovenscina-Latin2', 'SolomonsPidgin_Pijin-Latin1',
         'Somali-Latin1', 'Soninke_Soninkanxaane-UTF8', 'Sorbian-Latin2', 'SouthernSotho_Sotho-Sesotho-Sutu-Sesutu-Latin1',
         'Spanish_Espanol-Latin1', 'Spanish-Latin1', 'Sukuma-Latin1', 'Sundanese-Latin1',
         'Sussu_Soussou-Sosso-Soso-Susu-UTF8', 'Swaheli-Latin1', 'Swahili_Kiswahili-Latin1', 'Swedish_Svenska-Latin1',
         'Tahitian-UTF8', 'Tamil-UTF8', 'Tenek_Huasteco-Latin1', 'Tetum-Latin1', 'Themne_Temne-UTF8',
         'Tigrinya_Tigrigna-VG2Main', 'Tiv-Latin1', 'Toba-UTF8', 'Tojol-abal-Latin1', 'TokPisin-Latin1',
         'Tonga-Latin1', 'Tongan_Tonga-Latin1', 'Totonaco-Latin1', 'Trukese_Chuuk-Latin1', 'Turkish_Turkce-Turkish',
         'Turkish_Turkce-UTF8', 'Tzeltal-Latin1', 'Tzotzil-Latin1', 'Uighur_Uyghur-Latin1', 'Uighur_Uyghur-UTF8',
         'Ukrainian-Cyrillic', 'Ukrainian-UTF8', 'Umbundu-Latin1', 'Urarina-Latin1', 'Uzbek-Latin1',
         'Vietnamese-ALRN-UTF8', 'Vietnamese-TCVN', 'Vietnamese-UTF8', 'Vietnamese-VIQR', 'Vietnamese-VPS',
         'Vlach-Latin1', 'Walloon_Wallon-Latin1', 'Wama-UTF8', 'Waray-Latin1', 'Wayuu-Latin1', 'Welsh_Cymraeg-Latin1',
         'WesternSotho_Tswana-Setswana-Latin1', 'Wolof-Latin1', 'Xhosa-Latin1', 'Yagua-Latin1', 'Yao-Latin1',
         'Yapese-Latin1', 'Yoruba-UTF8', 'Zapoteco-Latin1', 'Zapoteco-SanLucasQuiavini-Latin1', 'Zhuang-Latin1',
         'Zulu-Latin1']
items = list(documents)

def read_document(name='English-Latin1'):
    filename = find_corpus_file('udhr', name)
    return open(filename).read().split()

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def langs(names = documents):
    """
    Return a dictionary mapping languages to documents.  If a list
    of names is specified, then only those languages will be
    included.
    """
    if type(names) is str: names = (names,)
    return dict([ (file, read_document(file)) for file in names])

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import udhr
    
    print "English-Latin1"
    for word in udhr.read('English-Latin1')[:27]:
        print word,
    print
    
    print "Italian-Latin1"
    for word in udhr.read('Italian-Latin1')[:27]:
        print word,
    print    
    
    print "English-Latin1, Italian-Latin1"
    data = udhr.langs(names = ('English-Latin1', 'Italian-Latin1'))
    
    print data["English-Latin1"]
    print data["Italian-Latin1"]

if __name__ == '__main__':
    demo()
