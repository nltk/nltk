/* This file is part of the implementation of the Dynamic Neuaral Network
   for speech recognition.

   Copyright (C) 1998 Lin Zhong<lzhong@princeton.edu>
                      Runsheng Liu <lrs-dee@tsinghua.edu.cn>
                      Circuits & Systems Group
                      Dept. of Electronic Engineering
                      Tsinghua University, Beijing
   Copyright (C) 2004 Lin Zhong <lzhong@princeton.edu>
                      Computer Engineering Group
                      Dept. of Electrical Engineering
                      Princeton University

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software. In case the
software is used in a publication, please cite
Lin Zhong, Yuanyuan Shi and Runsheng Liu,
"A Dynamic Neural Network for Syllable Recognition",
in Proc. Intl. Joint Conf. Neural Networks, Washington D.C., 1999.


THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
*/
#ifndef SPEECHPROC_H
#define SPEECHPROC_H

#define MaxFrameWidth  256
#define MaxFrameNum 256

typedef class featureParam 
{
public:
	unsigned int Cepstrum_order;
	
	unsigned int frameStep;
	unsigned int frameWidth;
	
	featureParam(void){
		frameStep = 100; 
		frameWidth = 256;
		Cepstrum_order = 12;
		return;
	}
} featureParam;
class TrainNN;
typedef class SpeechProc  
{
	friend class TrainNN;
protected:
	featureParam *featureParameters;

	unsigned int	frameNum;

	//Extracted features
	/* First dimension: frame num */
	/* Second dimension: features */
	float **features;

public:
	unsigned int GetFrameNum(void) const {return frameNum;}
	SpeechProc(featureParam &fParam);
	virtual ~SpeechProc();

	
	short *ReadWav(char fileName[], unsigned int &voiceLength);
	/* return the pointer to the array of features */
	/* frameNum is also set.			       */
	float ** FeatureExtract(short *voice, unsigned int voiceL);
	void ReleaseFeatures(void);

	int SaveFeatures(FILE *fp);

} SpeechProc;

#endif
