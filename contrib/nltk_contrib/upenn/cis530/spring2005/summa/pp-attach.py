#Brian Summa
#CIS530 Term Project
#
#For my term project, I chose to implement three PP-attachment algorithms to predict 
#the attachment of a preposition to either the head noun or verb in a sentence.  
#Specifically, a Naive Backed-off Algorithm, Collins's Backed-off Algorithm, 
#and a Backed-off algorithm of my own creation, which I called Pseudo-Biased.   
#My purpose was to implement and design functions in python that, after being trained,
#can reliable predict the attachment of a preposition.
#
#Instead of dealing with a normal corpus of text, To simply the process, the functions 
#take in data of the form [V,N1,PP,N2, N/V] where V and N1 are the head verb and noun 
#that we are trying to predict whether the preposition PP is attached to.  N2 is the 
#noun object of the prepositional phrase.  Finally, in each data element we have the 
#annotated proper attachment for testing our results and training. The data I used 
#for my module was obtained from ftp://ftp.cis.upenn.edu/pub/adwait/PPattachData/.  
#The data included, a training set, a test set, a development set, and file containing 
#bitstring conversion for all the words in the sets. 

#
#Please see the individual function for more detail.

class Backoff_predictor:
	#Initialize all class variables
	data = dict();
	bitstrings = dict();
	type = 'Naive';
	threshold = 1;
	bitstrings_flag = False;
	unify_flag = False;

	#A test to see if a character is the character representation of a  number
	def isNumber(self,s):
		try:
			value=int(s);
			return True;
		except ValueError:
			return False;

	#Attempt to alleviate some sparse data by accounting for numbers/dates.  Also stripped 's' and 
	#'e' off of the nouns and verb to try to account for plural forms.  As long as the stripping of a
	#final 'e', 's', or 'es' is consistant we should be ok.
	def unify_words(self, temp):
	#Account For Numbers,Dates
		if temp[1] != '':
			#if the first character is a number then it is changed to '_NUMBER_' unless it's 4 characters long
			#then it's considered a '_DATE_'
			if self.isNumber(temp[1][0]):
				if len(temp[1]) == 4:
					temp[1] = '_DATE_';
				else:
					temp[1] = '_NUMBER_';
			#Resolve the english 'word' form of numbers to '_NUMBER_'
			if (temp[1].lower() == 'billion' or temp[1].lower() == 'million' or temp[1].lower() == 'thousand' or temp[1].lower() == 'hundred' or
			temp[1].lower() == 'billions' or temp[1].lower() == 'millions' or temp[1].lower() == 'thousands' or temp[1].lower() == 'hundreds' or
			temp[1].lower() == 'ten' or temp[1].lower() == 'twenty' or temp[1].lower() == 'thirty' or temp[1].lower() == 'forty' or
			temp[1].lower() == 'fifty' or temp[1].lower() == 'sixty' or temp[1].lower() == 'seventy' or temp[1].lower() == 'eighty' or 
			temp[1].lower() == 'ninty' or temp[1].lower() == 'one' or temp[1].lower() == 'two' or temp[1].lower() == 'three' or
			temp[1].lower() == 'four' or temp[1].lower() == 'five' or temp[1].lower() == 'six' or temp[1].lower() == 'seven' or
			temp[1].lower() == 'eight' or temp[1].lower() == 'nine'):
				temp[1] = '_NUMBER_';
			#Resolve the 'word' form of dates to '_DATE_'
			if (temp[1].lower() == 'january' or temp[1].lower() == 'february' or temp[1].lower() == 'march' or temp[1].lower() == 'april' or
			temp[1].lower() == 'may' or temp[1].lower() == 'june' or temp[1].lower() == 'july' or temp[1].lower() == 'august' or
			temp[1].lower() == 'september' or temp[1].lower() == 'october' or temp[1].lower() == 'november' or temp[1].lower() == 'december' or
			temp[1].lower() == 'sunday' or temp[1].lower() == 'monday' or temp[1].lower() == 'tuesday' or temp[1].lower() == 'wednesday' or
			temp[1].lower() == 'thursday' or temp[1].lower() == 'friday' or temp[1].lower() == 'saturday'):
				temp[1] = '_DATE_';
			if(temp[1][0].isupper()):
				temp[1] = '_NAME_';
		#Same as above, but for the PP object noun
		if temp[3] != '':
			if self.isNumber(temp[3][0]):
				if len(temp[3]) == 4:
					temp[3] = '_DATE:';
				else:
					temp[3] = '_NUMBER_';
			if (temp[3].lower() == 'billion' or temp[3].lower() == 'million' or temp[3].lower() == 'thousand' or temp[3].lower() == 'hundred' or
			temp[3].lower() == 'billions' or temp[3].lower() == 'millions' or temp[3].lower() == 'thousands' or temp[3].lower() == 'hundreds' or
			temp[3].lower() == 'ten' or temp[3].lower() == 'twenty' or temp[3].lower() == 'thirty' or temp[3].lower() == 'forty' or
			temp[3].lower() == 'fifty' or temp[3].lower() == 'sixty' or temp[3].lower() == 'seventy' or temp[3].lower() == 'eighty' or 
			temp[3].lower() == 'ninty' or temp[3].lower() == 'one' or temp[3].lower() == 'two' or temp[3].lower() == 'three' or
			temp[3].lower() == 'four' or temp[3].lower() == 'five' or temp[3].lower() == 'six' or temp[3].lower() == 'seven' or
			temp[3].lower() == 'eight' or temp[3].lower() == 'nine'):
				temp[3] = '_NUMBER_';
			if (temp[3].lower() == 'january' or temp[3].lower() == 'february' or temp[3].lower() == 'march' or temp[3].lower() == 'april' or
			temp[3].lower() == 'may' or temp[3].lower() == 'june' or temp[3].lower() == 'july' or temp[3].lower() == 'august' or
			temp[3].lower() == 'september' or temp[3].lower() == 'october' or temp[3].lower() == 'november' or temp[3].lower() == 'december' or
			temp[3].lower() == 'sunday' or temp[3].lower() == 'monday' or temp[3].lower() == 'tuesday' or temp[3].lower() == 'wednesday' or
			temp[3].lower() == 'thursday' or temp[3].lower() == 'friday' or temp[3].lower() == 'saturday'):
				temp[3] = '_DATE_';
			#Test for proper name
			if(temp[3][0].isupper()):
				temp[3] = '_NAME_';
		#Strip ending 'e', 's', and 'es'  for PP object noun.
		#Doing this for N1 causes a decrease in accuracy, so it is left out.
		if temp[3] != '':
			if (len(temp[3])>1 and temp[3][len(temp[3])-1] == 's'):
				temp[3] = temp[3][:len(temp[3])-1];
			if (len(temp[3])>1 and temp[3][len(temp[3])-1] == 'e'):
				temp[3] = temp[3][:len(temp[3])-1];
		#Strip ending 'ing', 'ed', 's', 'e', and double letter endings (i.e. tt)
		#Again, as long as we are consistant, removing all double letter endings should not hurt us too badly.
		if temp[0] != '':
			#Verb lower case
			temp[0] == temp[0].lower();			
			if (len(temp[0])>2 and temp[0][len(temp[0])-3] == 'i' and temp[0][len(temp[0])-2] == 'n' and temp[0][len(temp[0])-1] == 'g' ):
				temp[0] = temp[0][:len(temp[0])-3];		
			if (len(temp[0])>1 and temp[0][len(temp[0])-2] == 'e' and temp[0][len(temp[0])-1] == 'd'):
				temp[0] = temp[0][:len(temp[0])-2];
			if (len(temp[0])>1 and temp[0][len(temp[0])-1] == 's'):
				temp[0] = temp[0][:len(temp[0])-1];
			if (len(temp[0])>2 and temp[0][len(temp[0])-1] == temp[0][len(temp[0])-2]):
				temp[0] = temp[0][:len(temp[0])-1];
			if (len(temp[0])>1 and temp[0][len(temp[0])-1] == 'e'):
				temp[0] = temp[0][:len(temp[0])-1];
		#Prepositions all lower case
		if temp[2] != '':
			temp[2] == temp[2].lower();
		return temp;

	#This element takes in an array [V,N1,PP,N2,'N' or 'V'] and trains our given predictor (Collins,Naive,Biased)
	def train_element(self, train_data):
		#If this predictor uses bitstrings, replace the training data words with their respective bitstrings
		if self.bitstrings_flag:
			for x in range(len(train_data)-1):
				if self.bitstrings.has_key(train_data[x]):
					train_data[x] = self.bitstrings[train_data[x]];
				else:
					train_data[x] = '00000000000000000000000000000000';
		#If this predictor uses my unify method, run it on the training data
		elif self.unify_flag:
			train_data = self.unify_words(train_data);
		#Increment the counts for Naive, Collins, and Baised
		if self.type == 'Naive' or self.type == 'Collins':
			if self.data.has_key((train_data[0], train_data[1], train_data[2], train_data[3],train_data[4])):
				self.data[(train_data[0], train_data[1], train_data[2], train_data[3],train_data[4])]+=1;
			else:
				self.data[(train_data[0], train_data[1], train_data[2], train_data[3],train_data[4])]=1;
			if self.data.has_key((train_data[0], train_data[1], train_data[2],train_data[4])):
				self.data[(train_data[0], train_data[1], train_data[2],train_data[4])]+=1;
			else:
				self.data[(train_data[0], train_data[1], train_data[2],train_data[4])]=1;		
			if self.data.has_key((train_data[0], train_data[2], train_data[3],train_data[4])):
				self.data[(train_data[0], train_data[2], train_data[3],train_data[4])]+=1;
			else:
				self.data[(train_data[0], train_data[2], train_data[3],train_data[4])]=1;	
			if self.data.has_key((train_data[1], train_data[2], train_data[3],train_data[4])):
				self.data[(train_data[1], train_data[2], train_data[3],train_data[4])]+=1;
			else:
				self.data[(train_data[1], train_data[2], train_data[3],train_data[4])]=1;	
			if self.data.has_key((train_data[0], train_data[2],train_data[4])):
				self.data[(train_data[0], train_data[2],train_data[4])]+=1;
			else:
				self.data[(train_data[0], train_data[2],train_data[4])]=1;
			if self.data.has_key((train_data[1], train_data[2],train_data[4])):
				self.data[(train_data[1], train_data[2],train_data[4])]+=1;
			else:
				self.data[(train_data[1], train_data[2],train_data[4])]=1;
			if self.data.has_key((train_data[2], train_data[3],train_data[4])):
				self.data[(train_data[2], train_data[3],train_data[4])]+=1;
			else:
				self.data[(train_data[2], train_data[3],train_data[4])]=1;
			if self.data.has_key((train_data[2], train_data[4])):
				self.data[(train_data[2], train_data[4])]+=1;
			else:
				self.data[(train_data[2], train_data[4])]=1;
			if self.type == 'Naive':
				if self.data.has_key((train_data[0], train_data[1], train_data[3],train_data[4])):
					self.data[(train_data[0], train_data[1], train_data[3],train_data[4])]+=1;
				else:
					self.data[(train_data[0], train_data[1], train_data[3],train_data[4])]=1;
				if self.data.has_key((train_data[0], train_data[1],train_data[4])):
					self.data[(train_data[0], train_data[1],train_data[4])]+=1;
				else:
					self.data[(train_data[0], train_data[1],train_data[4])]=1;
				if self.data.has_key((train_data[0], train_data[3],train_data[4])):
					self.data[(train_data[0], train_data[3],train_data[4])]+=1;
				else:
					self.data[(train_data[0], train_data[3],train_data[4])]=1;
				if self.data.has_key((train_data[1], train_data[3],train_data[4])):
					self.data[(train_data[1], train_data[3],train_data[4])]+=1;
				else:
					self.data[(train_data[1], train_data[3],train_data[4])]=1;
				if self.data.has_key((train_data[0], train_data[4])):
					self.data[(train_data[0],train_data[4])]+=1;
				else:
					self.data[(train_data[0],train_data[4])]=1;
				if self.data.has_key((train_data[1], train_data[4])):
					self.data[(train_data[1],train_data[4])]+=1;
				else:
					self.data[(train_data[1],train_data[4])]=1;
				if self.data.has_key((train_data[3], train_data[4])):
					self.data[(train_data[3],train_data[4])]+=1;
				else:
					self.data[(train_data[3],train_data[4])]=1;
		elif self.type == 'Biased':
			if self.data.has_key((train_data[0], train_data[2])):
				if (train_data[4] == 'N'):
					self.data[(train_data[0], train_data[2])]+=1;
				else:
					self.data[(train_data[0], train_data[2])]-=1;
			else:
				if (train_data[4] == 'N'):
					self.data[(train_data[0], train_data[2])]=1;
				else:
					self.data[(train_data[0], train_data[2])]=-1;
			if self.data.has_key((train_data[1], train_data[2])):
				if (train_data[4] == 'N'):
					self.data[(train_data[1], train_data[2])]+=1;
				else:
					self.data[(train_data[1], train_data[2])]-=1;
			else:
				if (train_data[4] == 'N'):
					self.data[(train_data[1], train_data[2])]=1;
				else:
					self.data[(train_data[1], train_data[2])]=-1;
			if self.data.has_key((train_data[2], train_data[3])):
				if (train_data[4] == 'N'):
					self.data[(train_data[2], train_data[3])]+=1;
				else:
					self.data[(train_data[2], train_data[3])]-=1;
			else:
				if (train_data[4] == 'N'):
					self.data[(train_data[2], train_data[3])]=1;
				else:
					self.data[(train_data[2], train_data[3])]=-1;
			if self.data.has_key((train_data[2])):
				if (train_data[4] == 'N'):
					self.data[(train_data[2])]+=1;
				else:
					self.data[(train_data[2])]-=1;
			else:
				if (train_data[4] == 'N'):
					self.data[(train_data[2])]=1;
				else:
					self.data[(train_data[2])]=-1;
	
	#Initialization for the Backoff predictor class.  Takes in the file name for the training data and optional input.
	#unify = True/False -> Set's the unifcation_flag on, which when data is trained or predicted, calls my unify function.
	#type = 'Collins'/'Naive'/'Biased' -> the type of predictor to create.
	#bitstrings = _filename_ -> the file that contains the bitstrings for out data
	def __init__(self, training_data, **keywords):
		if keywords.has_key('unify'):
			if isinstance(keywords['unify'],bool):
				self.unify_flag = keywords['unify'];
			else:
				raise Exception('Improper type given for unify: expected bool.');
		if keywords.has_key('type'):
			if keywords['type'] != 'Collins' and keywords['type'] != 'Naive' and keywords['type'] != 'Biased':
				raise Exception('Improper type given for the type of predictor: expected Collins, Naive, Biased.');
			else:
				self.type = keywords['type'];
		#Create out bitstrings dictionary
		if keywords.has_key('bitstrings'):
			if self.unify_flag:
				raise Exception('Cannot use both the unify structure and bitstrings.')
			if isinstance(keywords['bitstrings'],str):
				bitstrings = keywords['bitstrings'];
				self.bitstrings_flag = True;
				bitfile = open(bitstrings);
				bitline = bitfile.readline();
				while bitline != '':
					temp = (bitline.rstrip('\n')).split('\t');
					self.bitstrings[temp[0]]=temp[1];
					bitline = bitfile.readline();
				bitfile.close(); 
			else:
				raise Exception('Improper type given for bitstrings file: expected string.');
		#Create our data dictionary
		if isinstance(training_data,str):
			file=open(training_data);
			t= file.readline();
			self.data=dict();
			while t != '':
				temp = (t.rstrip('\n')).split(' ');
				temp.pop(0);
				self.train_element(temp);
				t= file.readline();
			file.close();
		else:
			raise Exception('Improper type given for input file: expected string.');

	#Given a data array [N1,V,PP,N2] predict either 'N' or 'V' attachment given our trained predictor
	def predict_element(self, test_array):
		#Since 'of' is always 'N' attached, we cheat and return 'N' always
		if(test_array[2] == 'of'):
			return 'N';
		#If we are using bitstrings, replace the test array with it's respective bitstrings.
		if self.bitstrings_flag:
			for x in range(len(test_array)):
				if self.bitstrings.has_key(test_array[x]):
					test_array[x] = self.bitstrings[test_array[x]];
				else:
					train_data[x] = '00000000000000000000000000000000';
		#Apply the unify function if desired.
		elif self.unify_flag:
			test_array = self.unify_words(test_array);
		#Apply the Collins backoff algorithm and Naive backoff algorithm to predict 'N' or 'V' attachment
		if self.type == 'Collins' or self.type == 'Naive':
			countN=0;
			countV=0;
			if(self.data.has_key((test_array[0], test_array[1], test_array[2], test_array[3], 'N'))):
				countN = self.data[(test_array[0], test_array[1], test_array[2], test_array[3], 'N')];
			if(self.data.has_key((test_array[0], test_array[1], test_array[2], test_array[3], 'V'))):
				countV = self.data[(test_array[0], test_array[1], test_array[2], test_array[3], 'V')];
			if((countN + countV) < self.threshold):
				countN=0;
				countV=0;
				if(self.data.has_key((test_array[0], test_array[1], test_array[2], 'N'))):
					countN += self.data[(test_array[0], test_array[1], test_array[2], 'N')];
				if(self.data.has_key((test_array[0], test_array[1], test_array[2], 'V'))):
					countV += self.data[(test_array[0], test_array[1], test_array[2], 'V')];
				if(self.data.has_key((test_array[0], test_array[2], test_array[3], 'N'))):
					countN += self.data[(test_array[0], test_array[2], test_array[3], 'N')];
				if(self.data.has_key((test_array[0], test_array[2], test_array[3], 'V'))):
					countV += self.data[(test_array[0], test_array[2], test_array[3], 'V')];
				if(self.data.has_key((test_array[1], test_array[2], test_array[3], 'N'))):
					countN += self.data[(test_array[1], test_array[2], test_array[3], 'N')];
				if(self.data.has_key((test_array[1], test_array[2], test_array[3], 'V'))):
					countV += self.data[(test_array[1], test_array[2], test_array[3], 'V')];
				if self.type == 'Naive':
					if(self.data.has_key((test_array[0], test_array[1], test_array[3], 'N'))):
						countN += self.data[(test_array[0], test_array[1], test_array[3], 'N')];
					if(self.data.has_key((test_array[0], test_array[1], test_array[3], 'V'))):
						countV += self.data[(test_array[0], test_array[1], test_array[3], 'V')];
				if((countN + countV) < self.threshold):
					countN=0;
					countV=0;
					if(self.data.has_key((test_array[0], test_array[2], 'N'))):
						countN += self.data[(test_array[0], test_array[2], 'N')];
					if(self.data.has_key((test_array[0], test_array[2], 'V'))):
						countV += self.data[(test_array[0], test_array[2], 'V')];
					if(self.data.has_key((test_array[1], test_array[2], 'N'))):
						countN += self.data[(test_array[1], test_array[2], 'N')];
					if(self.data.has_key((test_array[1], test_array[2], 'V'))):
						countV += self.data[(test_array[1], test_array[2], 'V')];		
					if(self.data.has_key((test_array[2], test_array[3], 'N'))):
						countN += self.data[(test_array[2], test_array[3], 'N')];
					if(self.data.has_key((test_array[2], test_array[3], 'V'))):
						countV += self.data[(test_array[2], test_array[3], 'V')];
					if self.type == 'Naive':
						if(self.data.has_key((test_array[0], test_array[1], 'N'))):
							countN += self.data[(test_array[0], test_array[1], 'N')];
						if(self.data.has_key((test_array[0], test_array[1], 'V'))):
							countV += self.data[(test_array[0], test_array[1], 'V')];
						if(self.data.has_key((test_array[1], test_array[3], 'N'))):
							countN += self.data[(test_array[1], test_array[3], 'N')];
						if(self.data.has_key((test_array[1], test_array[3], 'V'))):
							countV += self.data[(test_array[1], test_array[3], 'V')];		
						if(self.data.has_key((test_array[0], test_array[3], 'N'))):
							countN += self.data[(test_array[0], test_array[3], 'N')];
						if(self.data.has_key((test_array[0], test_array[3], 'V'))):
							countV += self.data[(test_array[0], test_array[3], 'V')];
					if((countN + countV) < self.threshold):
						countN=0;
						countV=0;
						if(self.data.has_key((test_array[2], 'N'))):
							countN += self.data[(test_array[2], 'N')];
						if(self.data.has_key((test_array[2], 'V'))):
							countN += self.data[(test_array[2], 'V')];
						if self.type == 'Naive':
							if(self.data.has_key((test_array[1], 'N'))):
								countN += self.data[(test_array[1], 'N')];
							if(self.data.has_key((test_array[1], 'V'))):
								countN += self.data[(test_array[1], 'V')];
							if(self.data.has_key((test_array[3], 'N'))):
								countN += self.data[(test_array[3], 'N')];
							if(self.data.has_key((test_array[3], 'V'))):
								countN += self.data[(test_array[3], 'V')];							
						if((countN + countV) < self.threshold):
							return('N');
						else:
							if float(countN)/(countN+countV)>0.5:
								return('N');
							else:
								return('V');
					else:
						if float(countN)/(countN+countV)>0.5:
							return('N');
						else:
							return('V');
				else:
					if float(countN)/(countN+countV)>0.5:
						return('N');
					else:
						return('V');
			else:
				if float(countN)/(countN+countV)>0.5:
					return('N');
				else:
					return('V');
		#Apply the Biased prediction algorithm
		elif self.type == 'Biased':
			count=0;
			if(self.data.has_key((test_array[0], test_array[2]))):
				count += self.data[(test_array[0], test_array[2])];
			if(self.data.has_key((test_array[1], test_array[2]))):
				count += self.data[(test_array[1], test_array[2])];
			if(self.data.has_key((test_array[2], test_array[3]))):
				count += self.data[(test_array[2], test_array[3])];
			if(abs(count) < self.threshold):
				count=0;
				if(self.data.has_key((test_array[2]))):
					count += self.data[(test_array[2])];
				if(abs(count) < self.threshold):
					return 'N';
				else:
					if count > 0:
						return('N');
					else:
						return('V');
			else:
				if count > 0:
					return('N');
				else:
					return('V');

	#Runs our trained predictor on a given test file. Takes in options:
	#count_threshold = INT -> The count threshold for our predictor
	#error_output = _filename_ -> Outputs errors to given filename
	#train = 'onright'/'onwrong'/'both'/'off' -> Realtime training of our data given the prediction correctness.
	def run_predictor(self, testfile, **keywords):
		data_backup = self.data.copy();
		#Set the count threshold for our predictor
		if keywords.has_key('count_threshold'):
			if isinstance(keywords['count_threshold'],int) and keywords['count_threshold']>0:
				self.threshold =  keywords['count_threshold'];
			else:
				raise Exception('Improper type given for count threshold: expected positive int.');
		#Open the test data file
		if isinstance(testfile,str):
			testdata = open(testfile);
			test_line = testdata.readline();
		else:
			raise Exception('Improper type given for test file: expected string.');
		#if we are outputing our errors, open the file.
		if keywords.has_key('error_output'):
			if isinstance(keywords['error_output'],str):
				output = open(keywords['error_output'], 'w');
			else:
				raise Exception('Improper type given for output file: expected string.');
		#Takes in the realtime training option
		if keywords.has_key('train'):
			if isinstance(keywords['train'],str):
				if keywords['train'] != 'onright' and keywords['train'] != 'onwrong' and keywords['train'] != 'both' and keywords['train'] != 'off':
					raise Exception('Improper input for training: must be onright, onwrong, both, or off');
			else:
				raise Exception('Improper type given for output file: expected string.');
		right = 0;
		total = 0;
		while test_line != '':
			total+=1;
			temp = (test_line.rstrip('\n')).split(' ');
			index = temp.pop(0);
			guess = self.predict_element([temp[0],temp[1],temp[2],temp[3]]);
			if guess == 'N':
				if(temp[4] == 'N'):
					right+=1;
					if keywords.has_key('train') and (keywords['train'] == 'onright' or keywords['train'] == 'both'):
						self.train_element([temp[0],temp[1],temp[2],temp[3],temp[4]]);
				else:
					if keywords.has_key('train') and (keywords['train'] == 'onwrong' or keywords['train'] == 'both'):
						self.train_element([temp[0],temp[1],temp[2],temp[3],temp[4]]);
					if keywords.has_key('error_output'):
						output.write(index + ' ' + temp[0] + ' ' + temp[1] + ' ' + temp[2] + ' ' + temp[3] + ' ' + temp[4] + '\n');
			else:	
				if(temp[4] == 'V'):
					right+=1;
					if keywords.has_key('train') and (keywords['train'] == 'onright' or keywords['train'] == 'both'):
						self.train_element([temp[0],temp[1],temp[2],temp[3],temp[4]]);
				else:
					if keywords.has_key('train') and (keywords['train'] == 'onwrong' or keywords['train'] == 'both'):
						self.train_element([temp[0],temp[1],temp[2],temp[3],temp[4]]);
					if keywords.has_key('error_output'):
						output.write(index + ' ' + temp[0] + ' ' + temp[1] + ' ' + temp[2] + ' ' + temp[3] + ' ' + temp[4] + '\n');
			test_line = testdata.readline();
		self.data = data_backup.copy();
		testdata.close();
		#Output results
		if keywords.has_key('error_output'):
			output.close();
		print ('-------------------');
		print ('Predictor: ' + self.type);
		print ('-------------------');
		print ('Options:')
		if self.bitstrings_flag:
			print ('Bitstrings = On');
		print ('\tBackoff Threshold = '+str(self.threshold));
		if self.unify_flag:
			print ('\tData unify = On');
		if keywords.has_key('train'):
			print('\tTraining = '+ keywords['train']);
		else:
			print('\tTraining = off');
		if keywords.has_key('error_output'):
			print('\tOutput file = '+ keywords['error_output']);
		print ('\tNumber Right: ' + str(right) + ' Percentage Correct: ' + str(float(right)/total*100)+ '\n');

#What's a better demo than running thre predictor on all option combination?
def demo():
	C= Backoff_predictor('training.txt', type='Biased', unify=True);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Biased', unify=True);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Biased', unify=True);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Biased', unify=True);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Biased', unify=False);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Biased', unify=False);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Biased', unify=False);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Biased', unify=False);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Biased', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Biased', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Biased', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Biased', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Naive', unify=True);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Naive', unify=True);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Naive', unify=True);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Naive', unify=True);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Naive', unify=False);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Naive', unify=False);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Naive', unify=False);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Naive', unify=False);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Naive', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Naive', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Naive', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Naive', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Collins', unify=True);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Collins', unify=True);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Collins', unify=True);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Collins', unify=True);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Collins', unify=False);
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Collins', unify=False);
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Collins', unify=False);
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Collins', unify=False);
	C.run_predictor('test.txt', train='off');
	C= Backoff_predictor('training.txt', type='Collins', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onright');
	C= Backoff_predictor('training.txt', type='Collins', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='onwrong');
	C= Backoff_predictor('training.txt', type='Collins', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='both');
	C= Backoff_predictor('training.txt', type='Collins', bitstrings='bitstrings.txt');
	C.run_predictor('test.txt', train='off');

#if __name__ == '__main__':
#	demo();
