FESTIVAL = .
EXTRALIB = 

INCPATH = -I$(FESTIVAL)/speech_tools/include -I$(FESTIVAL)/festival/src/include
LIBPATH = -L$(FESTIVAL)/speech_tools/lib -L$(FESTIVAL)/festival/src/lib

SRC = tts.cc
OBJ = tts.o
EXE = ttsmodule.so
LIB = -lFestival -lestools -leststring -lestbase -lsocket -lnsl -lcurses $(EXTRALIB)

CC = g++
CCFLAGS = -Wno-deprecated

$(EXE):	$(OBJ)
	$(CC) $(CCFLAGS) $(LIBPATH) -shared -o $(EXE) $(OBJ) $(LIB)

$(OBJ): $(SRC)
	$(CC) $(CCFLAGS) $(INCPATH) -c -fPIC -o $(OBJ) $(SRC)

