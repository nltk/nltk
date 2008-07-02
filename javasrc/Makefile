
JAVAC=/usr/local/jdk1.5.0/bin/javac

JAVA_SRC = $(shell find org -name '*.java')

MALLET_HOME = /usr/local/mallet-0.4
CLASSPATH = .:$(MALLET_HOME)/class/:$(MALLET_HOME)/lib/mallet-deps.jar

javac:
	$(JAVAC) -cp "$(CLASSPATH)" $(JAVA_SRC)

clean:
	rm -f `find org -name '*.class'`
