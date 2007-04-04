echo 'Zero R test'
python ../classifier/classify.py -f datasets/minigolf/weather
echo 'Zero R verify'
python ../classifier/classify.py -vf datasets/minigolf/weather
echo 'One R test'
python ../classifier/classify.py -a 1R -f datasets/minigolf/weather
echo 'One R verify'
python ../classifier/classify.py -a 1R -vf datasets/minigolf/weather
echo 'Decision Tree test'
python ../classifier/classify.py -a DT -f datasets/test_phones/phoney
echo 'Decision Tree verify'
python ../classifier/classify.py -a DT -vf datasets/minigolf/weather

