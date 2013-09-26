from words import *
words = read_words('corpus/telephone.txt')
counts = count_words(words)
print_freq(counts)




from words import *
words = read_words('corpus/rural.txt')
counts = count_pairs(words)
print_freq(counts)




