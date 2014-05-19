__author__ = 'Directorli'
import svmlight

class SVM():
    def __init__(self):

        self._modeldic = {}

    #return a list of all feature
    def featurelist(self,untrainset):
        dickeylist=[]
        for tup in untrainset:
            dic = tup[0]
            for key in dic.keys():
                haskey = 0
                for exkey in dickeylist:
                    if exkey == key:
                        haskey = 1
                if haskey == 0:
                    dickeylist.append(key)
        return dickeylist



    def lablelist(self,untrainset):
        dickeylist=[]
        for tup in untrainset:
            haskey = 0
            for exkey in dickeylist:
                if tup[1] == exkey :
                    haskey =1
            if haskey == 0:
                dickeylist.append(tup[1])
        return dickeylist



    #change feature of  untrain format to svmlight format
    def changeformat(self,untrainset,lable):
        fullsample=[]
        featurelist = self._featurelist
        for eachsample in untrainset:
            dic = eachsample[0]
            svmfeature = []
            for key in dic.keys():
                for num in range(len(featurelist)):
                    if key == featurelist[num]:
                        break
                if type(dic[key])==int or type(dic[key])==float:
                    afeature = (num+1,dic[key])
                    svmfeature.append(afeature)
            if lable == eachsample[1]:
                asvmsample=(1,svmfeature)
            else:
                asvmsample=(-1,svmfeature)
            fullsample.append(asvmsample)
        return fullsample

    def train(self,untrainset):
        self._lablelist = self.lablelist(untrainset)
        self._featurelist = self.featurelist(untrainset)
        modeldic = {}
        for onelable in self._lablelist:
            trainset = self.changeformat(untrainset,onelable)
            modeldic[onelable]=svmlight.learn(trainset ,type='classification', verbosity=0)
        self._modeldic=modeldic

        return self


    def changetestformat(self,untestset):
        svmtestset = []
        for onedic in untestset:
            onetestsample = []
            for onefeature in onedic.keys():
                for num in range(len(self._featurelist)):
                    # print "if onefeature == self._featurelist[num]:",(onefeature,onedic[onefeature]),self._featurelist
                    if onefeature == self._featurelist[num]:
                        break
                if type(onedic[onefeature])==int or type(onedic[onefeature])==float:
                    onetestsample.append((num+1,onedic[onefeature]))
            svmtestset.append((0,onetestsample))
        return svmtestset





    def batch_classify(self,untestset):
        prediclist = []
        modeldic = self._modeldic
        testset = self.changetestformat(untestset)
        for testsample in testset:
            maxpredict = -100
            prelable = ""
            for onelable in modeldic.keys():
                onepre = svmlight.classify(modeldic[onelable],[testsample])
                # print onepre,onelable,
                if onepre > maxpredict:
                    maxpredict = onepre
                    prelable = onelable
            # print prelable
            prediclist.append(prelable)
        return prediclist

SVM=SVM()

def demo():
    from nltk.classify.util import names_demo
    classifier = names_demo(SVM.train)


if __name__ == '__main__':
    demo()
