CORPORA := ../../data/corpora
BROWN = $(CORPORA)/brown

# copy the Brown corpus to the HDFS file system
hdfs:
	hadoop dfs -mkdir brown
	hadoop dfs -copyFromLocal $(BROWN) brown