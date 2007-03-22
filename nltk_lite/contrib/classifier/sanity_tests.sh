echo 'Zero R test'
python nltk_lite_contrib/classify.py -f datasets/minigolf/weather
echo 'Zero R verify'
python nltk_lite_contrib/classify.py -vf datasets/minigolf/weather
echo 'One R test'
python nltk_lite_contrib/classify.py -a 1R -f datasets/minigolf/weather
echo 'One R verify'
python nltk_lite_contrib/classify.py -a 1R -vf datasets/minigolf/weather

