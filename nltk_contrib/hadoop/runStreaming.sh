streamer="/usr/local/share/hadoop/contrib/streaming/hadoop-*-streaming.jar"

hadoop dfs -rmr $4
hadoop jar $streamer -mapper $1 -reducer $2 -input $3/* -output $4 -file $1 -file $2 -jobconf mapred.job.name="$5" -jobconf io.sort.mb=250 -jobconf mapred.task.timeout=600000 -jobconf mapred.reduce.tasks=5 -jobconf mapred.tasktracker.map.tasks.maximum=1