/* This file is part of the implementation of the Dynamic Neuaral Network
   for speech recognition.

   Copyright (C) 1998 Husheng Li <hushengl@princeton.edu>
		      Liang Gu
		      Jifeng Geng
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
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <assert.h>
#include "SpeechProc.h"

typedef struct MOD{
        float Re;
        float Im;
} MOD;

#define SEVER 0x7FFF       //to unify voice samples

static float C1[256];
static float C2[256];
static int FFT_DIT(MOD *input, int length);
static void MFCC_EXTRACT(short *voiceFrame, unsigned int frameWidth, unsigned int Cepstrum_order, float *C);
static float *wc;
static float *h;
SpeechProc::SpeechProc(featureParam &fParam)
{
	featureParameters= &fParam;
	frameNum = 0;
  	unsigned int i; 
	
 	for(i=0; i<256; i++){
      		C1[i] =   cos(i * 2 * M_PI/ 256);
      		C2[i] = - sin(i * 2 * M_PI/ 256);
    	}

	wc = new float [featureParameters->Cepstrum_order];
	assert( wc );
	for(i=0; i<featureParameters->Cepstrum_order; i++) {
		wc[i] = 1.0 / float(featureParameters->Cepstrum_order) + \
		sin(M_PI * (float)(i+1) / (float)featureParameters->Cepstrum_order) / 2.0;
	}
	h = new float[MaxFrameWidth];
	assert(h);
    	for(i=0; i<MaxFrameWidth; i++) {
        	h[i] = 0.54 - 0.46 * cos(M_PI * 2 * i / (MaxFrameWidth-1));
	}
	return;
}

SpeechProc::~SpeechProc() {
	if(wc) delete[] wc;
	if(h) delete[] h;
	return;
}
void SpeechProc::ReleaseFeatures(void) {
	if(features){
		for(unsigned int i = 0; i<frameNum; i++) {
			if(features[i])
				delete[] features[i];
		}
		delete[] features;
	}
	return;
}
short *SpeechProc::ReadWav(char fileName[], unsigned int &voiceLength) {
	FILE *fp;
	unsigned int numRead;

	if((fp=fopen(fileName, "rb"))==NULL) {
//		fprintf(stderr, "in File %s line %d: Cannot open %s\n", __FILE__, __LINE__, fileName);
        return NULL;
	}
	fseek(fp, 40, SEEK_SET);
	numRead = fread(&voiceLength , sizeof(long), 1, fp);
	voiceLength = voiceLength>>1;
	assert(numRead==1);
	assert(voiceLength>0);
	short *voice= new short[voiceLength];
	assert(voice);
	numRead = fread(voice, sizeof(short),voiceLength, fp);
	if(numRead!=voiceLength){
		fprintf(stderr, "read %d voice %d\n", numRead, voiceLength);
		fprintf(stderr, "in File %s line %d: wav read wrong\n", __FILE__, __LINE__);
        delete[] voice;
        return NULL;
	}
	fclose(fp);
	return voice;
}

float ** SpeechProc::FeatureExtract(short *voice, unsigned voiceL)
{
	unsigned int		i,  k;
	float		*u;
	float		**cc;
	float **f;	
	unsigned int	length;

	unsigned int voiceLength = voiceL;

	voiceLength--;	
	
	u = new float [featureParameters->Cepstrum_order];
	assert( u );

	frameNum = (voiceLength - (featureParameters->frameWidth - featureParameters->frameStep)) / featureParameters->frameStep;
	length = frameNum;
	// c is Speech Feature, cc is temperary buffer
	cc = new float *[frameNum];
	assert( cc );

	for(i=0; i<frameNum; i++) {
		cc[i] = new float [featureParameters->Cepstrum_order];
		assert( cc[i] );
	}

	//now length=frameNum-4
	f = new float *[length];
	assert( f );

	for(i=0; i<length; i++) {
		f[i] = new float [featureParameters->Cepstrum_order];
		assert( f[i] );
	}

	for(i=0; i<frameNum; i++) {
           	MFCC_EXTRACT(&voice[i*featureParameters->frameStep], featureParameters->frameWidth, \
					featureParameters->Cepstrum_order, cc[i]);
		for(k=0; k<featureParameters->Cepstrum_order; k++)
 				cc[i][k] *= wc[k];
	}
	for(i=0; i<length; i++){
		for(k=0; k<featureParameters->Cepstrum_order; k++)
		 	f[i][k] = cc[i][k];
	}
	
	
	for(i=0; i<frameNum; i++) {
		delete[] cc[i];
	}
	delete[] cc;

	delete[] u;
	features = f;
	frameNum = length;
	return f;
}

void MFCC_EXTRACT(short *voiceFrame, unsigned int frameWidth, unsigned int Cepstrum_order, float *C)
{
    unsigned int   j,p;
    unsigned int   nBankNum = 26;
    unsigned int   *frequencyBanks;

     float temp;
     float *Mel_f;
     float *f;
     float *Sw;
     short *s = voiceFrame;

     MOD input[256];

     frequencyBanks  = new unsigned int [nBankNum+1];       assert(frequencyBanks);
     Mel_f = new float [nBankNum];      assert(Mel_f); 
     f     = new float [frameWidth];  assert(f);
     Sw	   = new float [frameWidth];   assert(Sw);

     frequencyBanks[0]  = 0;
     frequencyBanks[1]  = 2;
     frequencyBanks[2]  = 4;
     frequencyBanks[3]  = 6;
     frequencyBanks[4]  = 8;
     frequencyBanks[5]  = 10;
     frequencyBanks[6]  = 12;
     frequencyBanks[7]  = 14;
     frequencyBanks[8]  = 16;
     frequencyBanks[9]  = 18;
     frequencyBanks[10] = 20;
     frequencyBanks[11] = 22;
     frequencyBanks[12] = 24;
     frequencyBanks[13] = 26;
     frequencyBanks[14] = 29;
     frequencyBanks[15] = 33;
     frequencyBanks[16] = 36;
     frequencyBanks[17] = 41;
     frequencyBanks[18] = 47;
     frequencyBanks[19] = 53;
     frequencyBanks[20] = 61;
     frequencyBanks[21] = 70;
     frequencyBanks[22] = 81;
     frequencyBanks[23] = 94;
     frequencyBanks[24] = 110;
     frequencyBanks[25] = 128;
	
     for(j=0; j<frameWidth; j++)
     {
   	   Sw[j] = ((float)s[j+1] - (float)s[j] * 0.95) / float(SEVER);
       	   input[j].Re = Sw[j] * h[j];
	   input[j].Im = 0.0;
     }
     FFT_DIT(input,frameWidth);
     for(j=0;j<frameWidth;j++)
     	f[j] = input[j].Re * input[j].Re + input[j].Im * input[j].Im;

     for(p=0; p<nBankNum-2; p++) {
       temp = 0;
       for(j=frequencyBanks[p]+1; j<=frequencyBanks[p+1]; j++)
	     temp += f[j] * (float)(j-frequencyBanks[p]) / (float)(frequencyBanks[p+1]-frequencyBanks[p]);
       for(j=frequencyBanks[p+1]+1; j<frequencyBanks[p+2];j++)
	     temp += f[j] * (float)(frequencyBanks[p+2]-j) /(float)(frequencyBanks[p+2]-frequencyBanks[p+1]);
       Mel_f[p] = log(temp);
     }

     for(p=0; p<Cepstrum_order;p++)
     {
       temp = 0;
       for(j=0; j<nBankNum-2; j++)
         temp += Mel_f[j] * cos(M_PI / (nBankNum-2) * (p + 1) * (j + 0.5));
         C[p] = temp;
     }

     delete[]   Sw;
     delete[]   frequencyBanks;
     delete[]   Mel_f;
     delete[]   f;
}

int FFT_DIT(MOD *input, int length)
{
  int      m, n;
  int      k;
  int      i, j, l;
  int      nv2;
  int      le, le1;
  int      ip;
  int      w, u;
  float   t;
  float   tr, ti;
  MOD      *W;
  
  W = new MOD [length];
  for(i=0; i<length; i++) {
     W[i].Re =   C1[i]; W[i].Im = - C2[i];
  }

// Calculate m.
  n = 1; m = 0;
  while (n < length) {
     n = n<<1; m++;
  }

// Reverse.
  if (n != length){
    return(-1);
  } else {
     nv2 = n>>1; j = 0;
     for (i=0; i<n-1; i++) {
       if (i<j) {
	  t = input[i].Re;
	  input[i].Re = input[j].Re;
	  input[j].Re = t;
	  t = input[i].Im;
	  input[i].Im = input[j].Im;
	  input[j].Im = t;
	}
       k = nv2;
       while (j>=k) {
	  j -= k; k = k>>1;
       }
       j += k;
     }

     // FFT

     for (le=1,l=1; l<=m; l++) {
	le = le<<1;
	le1 = le>>1;
	u = 0;
	w = length/(le1<<1);
	for (j=0; j<le1; j++,u+=w)
	 for (i=j; i<n; i+=le) {
	    ip  = i + le1;
	    tr = input[ip].Re * W[u].Re - input[ip].Im * W[u].Im;
	    ti = input[ip].Re * W[u].Im + input[ip].Im * W[u].Re;
	    input[ip].Re = (input[i].Re - tr)/2;
	    input[ip].Im = (input[i].Im - ti)/2;
	    input[i].Re  = (input[i].Re + tr)/2;
	    input[i].Im  = (input[i].Im + ti)/2;
	  }
      }
  }

  delete[] W;

  return(0);
}

int SpeechProc::SaveFeatures(FILE *fp) {
	unsigned int i, j;
/*	if((fp=fopen(fileName, "w"))==NULL) {
		fprintf(stderr, "in File %s line %d: Fail to create file %s\n", __FILE__, __LINE__, fileName);
	} */
	fprintf(fp, "%5d\t%5d\n", frameNum, featureParameters->Cepstrum_order);
	for(i = 0;i<frameNum;i++) {
		for(j= 0; j<featureParameters->Cepstrum_order;j++) {
			fprintf(fp,"%1.2f ", features[i][j]);
		}
		fprintf(fp,"\n");
	}
//	fclose(fp);
	return 1;
}
