#!/usr/bin/python
# -*- coding: utf8 -*-

from nltk.tree import *

# construct NE tree
group = ParentedTree('グループ名', ['スポーツチーム名'])
polorg = ParentedTree('政治的組織名', ['政府組織名', '政党名', '公共機関名'])
org = ParentedTree('組織名', [polorg, group, '企業名', '企業グループ名', 
'軍隊名', '協会名', '取引所名', '民族名', '国籍名'])

person = ParentedTree('人名', ['姓名', '男性名', '女性名'])

gpe = ParentedTree('ＧＰＥ',['市区町村名', '郡名', '都道府県州名', '国名'])
geological = ParentedTree('地形名',['陸上地形名','河川湖沼名', '海洋名'])
astral = ParentedTree('天体名',['恒星名', '惑星名'])
address = ParentedTree('アドレス', ['郵便住所', '電話番号', '電子メイル', 
'ＵＲＬ'])
location = ParentedTree('地名', [gpe, '地域名', geological, astral, address])

station = ParentedTree('駅名',['空港名', '電車駅名', '港名', '停車場名'])
goe = ParentedTree('ＧＯＥ', ['学校名', '美術博物館名', '娯楽施設', '神社寺名', 
station])
line = ParentedTree('路線',['電車路線名', '道路名', '航路', 'トンネル名', 
'橋名'])
facility = ParentedTree('施設名', [goe, line, '公園名', '記念碑名'])

vehicle = ParentedTree('乗り物名',['車名', '列車名', '飛行機名', '宇宙船名',
'船名'])
art = ParentedTree('芸術名', ['絵画名', 'テレビ番組名', '映画名', '公演名',
'音楽名'])
printing = ParentedTree('出版物名', ['書籍名', '新聞名', '雑誌名'])
product = ParentedTree('製品名',[vehicle, '医薬品名', '武器名', '株名', 
'通貨名', '賞名', '理論名', '規則名', 'サービス名', 'キャラクター名', 
'方式制度名', '運動行為名', '計画名', '学問名', 'クラス名', '競技名', '罪名', 
art, printing])
event = ParentedTree('イベント名',['大会名', '会議名', '自然現象名', '戦争名',
'自然災害名', '犯罪名'])
title = ParentedTree('称号名',['地位名'])
name = ParentedTree('名前', [person,org, location, facility, product, '病気名',
event, title, '言語名', '宗教名'])

natural = ParentedTree('自然物名', ['動物名', '植物名', '物質名'])

time = ParentedTree('時間',['時刻表現', '日付表現', '時代表現'])
period = ParentedTree('期間',['時刻期間', '日数期間', '週期間', '月期間',
'年期間'])
timetop = ParentedTree('時間表現', [time, period])

measure = ParentedTree('寸法表現', ['長さ', '面積', '体積', '重量', '速度',
'密度', '温度', 'カロリー', '震度'])
nloc = ParentedTree('場所数',['国数'])
count = ParentedTree('個数',['人数', '組織数', nloc, '施設数', '製品数',
'イベント数', '動物数', '植物数', '物質数'])
number = ParentedTree('数値表現',['金額表現', '株指標', 'ポイント', '割合表現',
'倍数表現', '頻度表現', '順位表現','年齢', measure, count])

ner = ParentedTree('TOP', [name, natural, '色', timetop, number])

# lookup table to convert common center words to their canonical type from the
# ner tree (such as program -> TV program)
lookup = {}
lookup['チーム名'] = 'スポーツチーム名'
lookup['番組名'] = 'テレビ番組名'
lookup['党名'] = '政党名'
lookup['議院名'] = '政府組織名'
lookup['ポジション名'] = '地位名'
lookup['スポーツ名'] = '競技名'
lookup['部署名'] = '組織名'
lookup['会社名'] = '企業名'
lookup['身長'] = '長さ'

# function for searching the ner tree and returning the _parent_ of the item if
# found
def search_tree(tree, item):
	"""
	Returns the parent of the item
	"""
	for child in tree:
		if isinstance(child, Tree):
			if child.node == item:
				return child.parent()
			else:
				a = search_tree(child, item)
				if isinstance(a, Tree):
					return a
		else:
			if child == item:
				return tree

# returns the list of parents of an item back up the tree, including the item,
# but excluding TOP
def parents(tree, item):
	"""
	Returns a list of direct parents of item
	"""
	p = ''
	parentlist = []

	while p != tree.node:
		parentlist.append(item)
		t = search_tree(tree, item)
		if isinstance(t, Tree):
			p = t.node
			item = p
		else:
			raise ValueError, 'item %s does not exist in tree' % item

	
	return parentlist
