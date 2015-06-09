from collections import Counter, defaultdict
import itertools
import csv
import matplotlib.pyplot as plt

from vader import SentimentIntensityAnalyzer
from nltk.corpus import tweets
from nltk.tokenize import wordpunct_tokenize

#tweets.fileids()
#tw_tokens = tweets.tokenized('tweets.20150430-223406.json')
texts = tweets.strings('tweets.20150430-223406.json')

keywords = {}
keywords['conservative'] = set(['cameron', 'david_cameron', 'davidcameron',
                                'dave', 'davecamm', 'osborne', 'portillo', 'pickles', 'tory', 'tories',
                                'torie', 'voteconservative', 'conservative', 'conservatives', 'bullingdon', 'telegraph'])
keywords['labour'] = set(['miliband', 'ed_miliband', 'edmiliband', 'edm',
                          'milliband', 'ed', 'uklabour', 'scottishlabour', 'labour', 'lab',
                          'edforchange', 'edforpm', 'milifandom', 'murphy'])
keywords['libdem'] = set(['clegg','libdem', 'libdems', 'dems', 'alexander'])
keywords['ukip'] = set(['farage', 'nigel_farage', 'nigel', 'askfarage',
                        'asknigelfarage', 'asknigelfar', 'ukip', 'davidcoburnukip'])
keywords['snp'] = set(['sturgeon', 'nicola_sturgeon', 'nicolasturgeon',
                       'nicola', 'salmond', 'snp', 'snpwin', 'votesnp', 'snpbecause', 'scotland',
                       'scotlands', 'scottish', 'indyref', 'independence', 'celebs4indy'])


def tweet_classify(text, keywords):
    toks = wordpunct_tokenize(text)
    toks_lower = [t.lower() for t in toks]
    labels = [k for k in keywords if keywords[k] & set(toks_lower)]
    return ' '.join(labels)


def full_labeled(texts, keywords, outfile=None):

    labeled_tweets = []
    sia = SentimentIntensityAnalyzer()

    for text in texts:
        labels = tweet_classify(text, keywords)
        sentiment = sia.polarity_scores(text)['compound']
        if len(labels) > 0:
            labeled_tweets.append([labels, text, sentiment])

    if outfile is not None:

        num = len(labeled_tweets)
        outfile = 'labeled_tweets.csv'

        with open(outfile, 'w', encoding= 'utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(labeled_tweets)
            print('Wrote {} lines to {}'.format(num, outfile))
    else:
        return labeled_tweets


outfile = 'labels_scores.csv'
#full_labeled(texts, keywords, outfile=outfile)
#scores = partial_labeled(texts, keywords)


infile = open('labeled_tweets.csv', encoding='utf8')
reader = csv.reader(infile)


def regularize(labeled_tweets, filtered=True):
    regular = []
    for row in labeled_tweets:
        labels = row[0].split()
        polarity_score = float(row[2])
        if polarity_score == 0.0:
            continue
        if filtered and len(labels) > 1:
            continue
        for label in labels:
            regular.append([label, polarity_score])
    return regular

def means(party_scores):
    pos_scores = defaultdict(list)
    neg_scores = defaultdict(list)
    for row in party_scores:
        party = row[0]
        sentiment = row[1]
        if sentiment > 0:
            pos_scores[party].append(sentiment)
        else:
            neg_scores[party].append(sentiment)
    parties = sorted(pos_scores.keys())
    pos_means = []
    neg_means = []
    for party in parties:
        pos = pos_scores[party]
        pos_means.append(sum(pos) / len(pos))
        neg = neg_scores[party]
        neg_means.append(sum(neg) / len(neg))
    return (parties, pos_means, neg_means)

regular = regularize(reader)
(parties, pos_means, neg_means) = means(regular)
print(parties)
print(pos_means)
print(neg_means)


def plot_graph(scores):
    pos_scores = []
    neg_scores = []

    for l in sorted(scores):
        pos_value = scores[l]['pos']
        mean_pos = sum(pos_value) / len(pos_value)
        pos_scores.append(mean_pos)

        neg_value = scores[l]['neg']
        mean_neg = sum(neg_value) / len(neg_value)
        neg_scores.append(mean_neg)

    fig = plt.figure()
    x = len(scores.keys())
    ax = plt.subplot(111)
    ax.bar(x, mean_pos, width= .5, color='r')
    ax.bar(x, mean_neg, width= .5, color='b')

    plt.show()


#plot_graph(scores)



#def vectorize(toks, feats, binary = True):

    #vector = [0 for f in feats]
    #selected = [feat for tok in toks for feat in feats if occurs_in(feat, tok)]
    #counts = Counter(selected)
    #for i in range(len(feats)):
    #feat = feats[i]
    #if feat in counts:
        #if binary:
        #vector[i] = 1
        #else:
        #vector[i] = counts[feat]

    #return vector


#vectors = [vectorize(twl, WORDLIST) for twl in tw_tokens]
#vectors = [v for v in vectors if sum(v) > 0]
#vectors.sort()
#unique = list(vectors for vectors, _ in itertools.groupby(vectors))
#print(len(unique))
#for u in unique[:10]:
    #print(u)



