streamer="/usr/local/hadoop/contrib/streaming/hadoop-*-streaming.jar"
hadoop="/usr/local/hadoop/bin/hadoop"

$hadoop dfs -rmr output-1
$hadoop jar $streamer -mapper name_mapper1.py -reducer /bin/cat -input name -output output-1 -file name_mapper1.py 

$hadoop dfs -rmr output-2
$hadoop jar $streamer -mapper swap_mapper.py -reducer value_aggregater.py -input output-1 -output output-2 -file swap_mapper.py -file value_aggregater.py 

$hadoop dfs -rmr output-final
$hadoop jar $streamer -mapper name_mapper2.py -reducer similiar_name_reducer.py -input output-2 -output output-final -file name_mapper2.py -file similiar_name_reducer.py
