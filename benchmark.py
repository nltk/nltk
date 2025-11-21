import json
import cProfile, pstats, io
from collections import defaultdict
import re
import ngram

import jieba
from nltk.tokenize import word_tokenize, sent_tokenize

_WORD_RE = re.compile(
    r"[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*"  # 带连字符或撇号的单词
    r"|"
    r"[^\w\s]"                             # 单个标点符号
)

def word_tokenize_re(text: str):
    return _WORD_RE.findall(text)

_SENT_RE = re.compile(r'[.!?]')

def sent_tokenize_re(text: str):
    return _SENT_RE.split(text)

def filter_text(text: str, lang = "en", use_re=True, use_aot=True):
    """
    根据通用网页数据清洗规则过滤文本

    Args:
        text_input: 待清洗的文本，可以是字符串或包含文本的字典
        lang (str): 文本语言类型，可选值为 'en'（英文）、'zh'（中文）、'other'（未切分语言如日语、泰语、越南语）

    Returns:
        dict: 包含清洗结果的字典
    """

    is_filtered = False
    discard_reason = []

    # 分句和分词
    if lang == 'en':
        # 英文分句和分词
        if use_re:
            sentences = sent_tokenize_re(text)
            words = word_tokenize_re(text)
        else:
            sentences = sent_tokenize(text)
            words = word_tokenize(text)

        word_num = len(words)
        char_num = len(text)
    elif lang == 'zh':
        # 中文分句（简单按。！？分句，实际应用中可以使用更复杂的分句方法）
        sentences = re.split(r'[。！？]', text)
        # 中文分词
        words = list(jieba.cut(text))
        word_num = len(words)
        char_num = len(text)
    else:
        # 未切分语言，按句子简单分割（实际应用中可能需要更合适的分句方法）
        sentences = text.split('\n')
        # 不进行分词，直接按字符处理
        words = list(text)
        word_num = len(words)
        char_num = len(text)

    # 计算重复句子和段落的比例
    unique_sentences = set(sentences)
    unique_paragraphs = set(text.split('\n'))
    sentence_duplicate_ratio = 1 - len(unique_sentences) / len(sentences) if sentences else 0
    paragraph_duplicate_ratio = 1 - len(unique_paragraphs) / len(text.split('\n')) if text.split('\n') else 0

    # 计算重复句子和段落的字符数比例
    sentence_char_count = sum(len(s) for s in sentences)
    unique_sentence_char_count = sum(len(s) for s in unique_sentences)
    sentence_char_duplicate_ratio = 1 - unique_sentence_char_count / sentence_char_count if sentence_char_count else 0

    paragraph_char_count = sum(len(p) for p in text.split('\n'))
    unique_paragraph_char_count = sum(len(p) for p in unique_paragraphs)
    paragraph_char_duplicate_ratio = 1 - unique_paragraph_char_count / paragraph_char_count if paragraph_char_count else 0

    # 计算高频 n-gram 和重复 n-gram 的比例
    if lang in ['en', 'zh']:
        def calculate_most_common_ngram(words, n):
            """计算指定n值的most common n-gram占比"""
            if len(words) < n:
                return 0

            n_gram_freq = defaultdict(int)
            for i in range(len(words) - n + 1):
                n_gram = tuple(words[i:i + n])
                n_gram_freq[n_gram] += 1

            if not n_gram_freq:
                return 0
            
            max_freq = max(n_gram_freq.values())
            most_common_key = [k for k, v in n_gram_freq.items() if v == max_freq][0]
            max_freq_chars = sum(len(word) for word in most_common_key) * max_freq
            
            text_total_chars = sum(len(word) for word in words)

            # print(max_freq)
            # print(max_freq / (len(words) - n + 1))
            # return max_freq / (len(words) - n + 1)
            

            return max_freq_chars/ text_total_chars

        def calculate_duplicated_ngram(words, n, lang):
            """计算指定n值的duplicated n-gram字符数占比"""
            
            if len(words) < n:
                return 0

            seen = set()
            duplicates = set()
            for i in range(len(words) - n + 1):
                n_gram = tuple(words[i:i + n])
                if n_gram in seen:
                    duplicates.add(n_gram)
                else:
                    seen.add(n_gram)

            if not duplicates:
                return 0

            # 计算重复n-gram的总字符数
            if lang == 'en':
                total_chars = sum(len(word) for gram in duplicates for word in gram)
            else:
                total_chars = sum(len(''.join(gram)) for gram in duplicates)

            # 计算文本总字符数
            text_total_chars = sum(len(word) for word in words)

            return total_chars / text_total_chars

        n_gram_results = {}
        # 计算most common n-gram (n=2,3,4)
        for n in range(2, 5):
            ratio = calculate_most_common_ngram(words, n)
            n_gram_results[f'most_common_{n}_gram_ratio'] = ratio
        
        # 计算duplicated n-gram (n=5~10)
        for n in range(5, 11):
            ratio = calculate_duplicated_ngram(words, n, lang)
            n_gram_results[f'duplicated_{n}_gram_ratio'] = ratio

    else:
        # 对于未切分语言，暂时不计算 n-gram 相关比例
        n_gram_results = {}

    # 重复移除规则
    if lang in ['en', 'zh']:
        # 英文和中文重复移除规则
        if sentence_duplicate_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'sentence_duplicate_ratio ({sentence_duplicate_ratio:.2f}) > 0.3')

        if sentence_char_duplicate_ratio > 0.2:
            is_filtered = True
            discard_reason.append(f'sentence_char_duplicate_ratio ({sentence_char_duplicate_ratio:.2f}) > 0.2')

        if paragraph_duplicate_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'paragraph_duplicate_ratio ({paragraph_duplicate_ratio:.2f}) > 0.3')

        if paragraph_char_duplicate_ratio > 0.2:
            is_filtered = True
            discard_reason.append(f'paragraph_char_duplicate_ratio ({paragraph_char_duplicate_ratio:.2f}) > 0.2')

        ngram_rules = [
            ("most_common_2_gram_ratio", 0.20, "most_common_2_gram_ratio"),
            ("most_common_3_gram_ratio", 0.18, "most_common_3_gram_ratio"),
            ("most_common_4_gram_ratio", 0.16, "most_common_4_gram_ratio"),
            ("duplicated_5_gram_ratio", 0.15, "duplicated_5_gram_ratio"),
            ("duplicated_6_gram_ratio", 0.14, "duplicated_6_gram_ratio"),
            ("duplicated_7_gram_ratio", 0.13, "duplicated_7_gram_ratio"),
            ("duplicated_8_gram_ratio", 0.12, "duplicated_8_gram_ratio"),
            ("duplicated_9_gram_ratio", 0.11, "duplicated_9_gram_ratio"),
            ("duplicated_10_gram_ratio", 0.10, "duplicated_10_gram_ratio"),
        ]

        for metric, threshold, reason_template in ngram_rules:
            value = n_gram_results.get(metric)
            if value is not None and value > threshold:
                is_filtered = True
                # 格式化提示信息，保留2位小数
                discard_reason.append(
                    f"{reason_template} ({value:.2f}) > {threshold}"
                )


    else:
        # 未切分语言重复移除规则
        if sentence_duplicate_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'sentence_duplicate_ratio ({sentence_duplicate_ratio:.2f}) > 0.3')

        if sentence_char_duplicate_ratio > 0.2:
            is_filtered = True
            discard_reason.append(f'sentence_char_duplicate_ratio ({sentence_char_duplicate_ratio:.2f}) > 0.2')

        if paragraph_duplicate_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'paragraph_duplicate_ratio ({paragraph_duplicate_ratio:.2f}) > 0.3')

        if paragraph_char_duplicate_ratio > 0.2:
            is_filtered = True
            discard_reason.append(f'paragraph_char_duplicate_ratio ({paragraph_char_duplicate_ratio:.2f}) > 0.2')

    # 文档级规则
    if lang == 'en':
        # 英文文档级规则
        if not (50 <= word_num <= 100000):
            is_filtered = True
            discard_reason.append(f'word_num ({word_num}) not in [50, 100000]')

        avg_word_length = sum(len(word) for word in words) / word_num if word_num else 0
        if not (3 <= avg_word_length <= 10):
            is_filtered = True
            discard_reason.append(f'avg_word_length ({avg_word_length:.2f}) not in [3, 10]')

        special_char_ratio = sum(1 for word in words if '#' in word or '...' in word) / word_num if word_num else 0
        if special_char_ratio > 0.1:
            is_filtered = True
            discard_reason.append(f'special_char_ratio ({special_char_ratio:.2f}) > 0.1')

        bullet_point_ratio = sum(
            1 for sentence in sentences if sentence.startswith('*') or sentence.startswith('-')) / len(
            sentences) if sentences else 0
        if bullet_point_ratio > 0.9:
            is_filtered = True
            discard_reason.append(f'bullet_point_ratio ({bullet_point_ratio:.2f}) > 0.9')

        ellipsis_ratio = sum(1 for sentence in sentences if sentence.endswith('...')) / len(
            sentences) if sentences else 0
        if ellipsis_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'ellipsis_ratio ({ellipsis_ratio:.2f}) > 0.3')
        words_non = re.split(r'[,.\s]+', text)
        # print(words_non)
        non_alpha_ratio = sum(1 for word in words_non if not any(c.isalpha() for c in word)) / len(words_non) if word_num else 0
        if non_alpha_ratio > 0.2:
            is_filtered = True
            discard_reason.append(f'non_alpha_ratio ({non_alpha_ratio:.2f}) > 0.2')

        # 英文停用词列表（可以根据实际需要扩展）
        stopwords = {'the', 'be', 'to', 'of', 'and', 'that', 'have', 'with'}
        stopword_count = sum(1 for word in words if word.lower() in stopwords)
        if stopword_count < 2:
            is_filtered = True
            discard_reason.append(f'stopword_count ({stopword_count}) < 2')

    elif lang == 'zh':
        # 中文文档级规则
        if char_num < 50:
            is_filtered = True
            discard_reason.append(f'char_num ({char_num}) < 50')

        special_char_ratio = sum(1 for word in words if '#' in word or '...' in word) / word_num if word_num else 0
        if special_char_ratio > 0.1:
            is_filtered = True
            discard_reason.append(f'special_char_ratio ({special_char_ratio:.2f}) > 0.1')

        bullet_point_ratio = sum(
            1 for sentence in sentences if sentence.startswith('*') or sentence.startswith('-')) / len(
            sentences) if sentences else 0
        if bullet_point_ratio > 0.9:
            is_filtered = True
            discard_reason.append(f'bullet_point_ratio ({bullet_point_ratio:.2f}) > 0.9')

        ellipsis_ratio = sum(1 for sentence in sentences if sentence.endswith('...')) / len(
            sentences) if sentences else 0
        if ellipsis_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'ellipsis_ratio ({ellipsis_ratio:.2f}) > 0.3')

        # 中文停用词列表（可以根据实际需要扩展）
        stopwords = {'的', '地', '得', '了', '和', '与', '呢', '吧', '啊'}
        stopword_count = sum(1 for word in words if word in stopwords)
        if stopword_count < 2:
            is_filtered = True
            discard_reason.append(f'stopword_count ({stopword_count}) < 2')

    else:
        # 未切分语言文档级规则
        if char_num < 50:
            is_filtered = True
            discard_reason.append(f'char_num ({char_num}) < 50')

        special_char_ratio = sum(1 for word in words if '#' in word or '...' in word) / word_num if word_num else 0
        if special_char_ratio > 0.1:
            is_filtered = True
            discard_reason.append(f'special_char_ratio ({special_char_ratio:.2f}) > 0.1')

        bullet_point_ratio = sum(
            1 for sentence in sentences if sentence.startswith('*') or sentence.startswith('-')) / len(
            sentences) if sentences else 0
        if bullet_point_ratio > 0.9:
            is_filtered = True
            discard_reason.append(f'bullet_point_ratio ({bullet_point_ratio:.2f}) > 0.9')

        ellipsis_ratio = sum(1 for sentence in sentences if sentence.endswith('...')) / len(
            sentences) if sentences else 0
        if ellipsis_ratio > 0.3:
            is_filtered = True
            discard_reason.append(f'ellipsis_ratio ({ellipsis_ratio:.2f}) > 0.3')

    # 句子级规则
    if lang == 'en':
        # 英文句子级规则
        filtered_word_count = 0
        cur = ""

        for sentence in sentences:
            if use_re:
                bl = False
                if sum(1 for c in sentence if c.isupper()) / len(sentence) > 0.6 if len(sentence) > 0 else 0:
                    filtered_word_count += len(word_tokenize_re(sentence))
                    bl = True

                if sentence.isdigit():
                    bl = True
                    filtered_word_count += len(word_tokenize_re(sentence))

                if re.match(r'^\d+\s+[a-zA-Z]+$', sentence):
                    bl = True
                    filtered_word_count += len(word_tokenize_re(sentence))

                if len(word_tokenize_re(sentence)) == 1:
                    bl = True
                    filtered_word_count += 1

                if re.match(r'^sign-in', sentence) or re.match(r'read more...$', sentence) or re.match(r'items in card',
                                                                                                    sentence):
                    bl = True
                    filtered_word_count += len(word_tokenize_re(sentence))
                # 如果该句子没有符合删除条件，则加入到 cur 中
                if not bl:
                    cur = cur + sentence
            else:
                bl = False
                if sum(1 for c in sentence if c.isupper()) / len(sentence) > 0.6 if len(sentence) > 0 else 0:
                    filtered_word_count += len(word_tokenize(sentence))
                    bl = True

                if sentence.isdigit():
                    bl = True
                    filtered_word_count += len(word_tokenize(sentence))

                if re.match(r'^\d+\s+[a-zA-Z]+$', sentence):
                    bl = True
                    filtered_word_count += len(word_tokenize(sentence))

                if len(word_tokenize(sentence)) == 1:
                    bl = True
                    filtered_word_count += 1

                if re.match(r'^sign-in', sentence) or re.match(r'read more...$', sentence) or re.match(r'items in card',
                                                                                                    sentence):
                    bl = True
                    filtered_word_count += len(word_tokenize(sentence))
                # 如果该句子没有符合删除条件，则加入到 cur 中
                if not bl:
                    cur = cur + sentence
        # 更新文本输入
        # if cur != text_input['text']:
        #     text_input['text'] = cur

        if filtered_word_count / word_num > 0.05 if word_num > 0 else 0:
            is_filtered = True
            discard_reason.append(f'filtered_sentence_ratio ({filtered_word_count / word_num:.2f}) > 0.05')

    # 记录过滤原因
    # result['filtered'] = is_filtered
    # result['discard_reason'] = discard_reason
    # if is_filtered:
    #     text_input['discard_reason'] = discard_reason

    return is_filtered


pr = cProfile.Profile()
pr.enable()

input_path = 'input_en.json'  # 替换为你的文件路径

sum_count = 0
count0 = 0
# count1 = 0
# count2 = 0

with open(input_path, 'r', encoding='utf-8') as infile:
    for line in infile:
        try:
            data = json.loads(line.strip())
            flag= filter_text(data.get("text"),lang="en", use_re=False, use_aot=True)
            # flag1 = filter_text(data.get("text"), lang="en", use_re=False)
            sum_count += 1
            if flag:
                count0 +=1
            # if flag1:
            #     count1 +=1    
            # if flag != flag1:
            #     count2 += 1
            if sum_count % 5000 == 0:
                print(f"计数：{sum_count}")
            if sum_count > 100000:
                break   
        except json.JSONDecodeError as e:
            print(f"跳过一行无效的 JSON：{e}")
            

print(f"filter count: {count0}, sum: {sum_count}")

pr.disable()
s = io.StringIO(); ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(10)
print(s.getvalue())