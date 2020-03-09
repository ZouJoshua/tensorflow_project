#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Joshua
@Time    : 2/27/20 4:08 PM
@File    : dataset_loader.py
@Desc    : 

"""

import os
import json
import jieba
from string import punctuation


import torch
import tqdm
import random
import re
from sklearn.utils import shuffle
from torch.utils.data import Dataset

from setting import DATA_PATH

class FasttextDataset(object):

    """
    处理成fasttext 训练文本
    """
    def __init__(self, corpus_path, single_char=False):
        self.corpus_path = corpus_path
        self.mapper_tag = {
            '财经': 'Finance',
            '彩票': 'Lottery',
            '房产': 'Property',
            '股票': 'Shares',
            '家居': 'Furnishing',
            '教育': 'Education',
            '科技': 'Technology',
            '社会': 'Sociology',
            '时尚': 'Fashion',
            '时政': 'Affairs',
            '体育': 'Sports',
            '星座': 'Constellation',
            '游戏': 'Game',
            '娱乐': 'Entertainment'
        }
        self.ori_file_names = ["thuc_news.train.txt", "thuc_news.eval.txt", "thuc_news.test.txt"]
        self.name_mark = ""
        self.single_char = single_char
        if self.single_char:
            self.name_mark = "single_char."

        self.generate_file()

    def is_chinese(self, uchar):
        """判断一个unicode是否是汉字"""
        if (uchar >= u'\u4e00') and (uchar <= u'\u9fa5'):
            return True
        else:
            return False

    @property
    def punc_list(self):
        add_punc = '，。、【 】 “”：；（）《》‘’{}？！⑦()、%^>℃：”“^-——=&#@￥\n「」…『』\u3000'
        return punctuation + add_punc


    def clean_zh_text(self, text):
        seg_list = jieba.cut(text, cut_all=False)
        no_punc = [w for w in seg_list if w not in self.punc_list]
        if no_punc:
            clean_text = " ".join(no_punc)
        else:
            clean_text = None
        return clean_text

    def split_text_by_single_char(self, text):
        # print("splitting chinese char")
        new_line = ""
        none_chinese = ""
        for char in text:
            if self.is_chinese(char) is False:
                if char in self.punc_list:
                    continue
                none_chinese += char
            else:
                if none_chinese:
                   char = none_chinese + " " + char
                   none_chinese = ""
                char += " "
                new_line += char
        return new_line.strip()



    def get_corpus_file(self, ori_file):
        file_name = os.path.split(ori_file)[1]
        ft_file_name = file_name.replace("thuc_news.", self.name_mark)
        file = os.path.join(self.corpus_path, ft_file_name)
        if os.path.exists(ori_file):
            print("Getting corpus from file {}".format(file_name))
            if not os.path.exists(file):
                with open(ori_file, "r", encoding="utf-8") as f, \
                        open(file, "w", encoding='utf-8') as wf:
                    _lines = f.readlines()
                    if self.single_char:
                        self.write_file_by_single_char(_lines, wf)
                    else:
                        self.write_file_by_participle(_lines, wf)
            else:
                print("File {} exists".format(file))
        else:
            raise FileNotFoundError

    def write_file_by_participle(self, lines, file_handler):
        for _line in lines:
            line = json.loads(_line.strip())
            cat = line["label"]
            text = line["text"]
            tokens = self.clean_zh_text(text)
            if tokens:
                ft_line = "__label__{} ".format(cat) + tokens
                file_handler.write(ft_line + "\n")
                file_handler.flush()

    def write_file_by_single_char(self, lines, file_handler):
        for _line in lines:
            line = json.loads(_line.strip())
            cat = line["label"]
            text = line["text"]
            tokens = self.split_text_by_single_char(text)
            if tokens:
                ft_line = "__label__{} ".format(cat) + tokens
                file_handler.write(ft_line + "\n")
                file_handler.flush()


    def generate_file(self):
        for name in self.ori_file_names:
            ori_file = os.path.join(self.corpus_path, name)
            self.get_corpus_file(ori_file)





class BertTFDataset(object):
    pass

class BertTorchDataset(Dataset):

    def __init__(self, corpus_path, word2idx_path, label2idx_path, max_seq_len, data_regularization=False):

        self.data_regularization = data_regularization
        # self.word2idx_path = word2idx_path
        # define max length
        self.max_seq_len = max_seq_len
        # directory of corpus dataset
        self.corpus_path = corpus_path
        # define special symbols
        self.pad_index = 0
        self.unk_index = 1
        self.cls_index = 2
        self.sep_index = 3
        self.mask_index = 4
        self.num_index = 5

        # 加载字典
        with open(word2idx_path, "r", encoding="utf-8") as f:
            self.word2idx = json.load(f)

        with open(label2idx_path, "r", encoding="utf-8") as f:
            self.label2idx = json.load(f)

        # 加载语料
        with open(corpus_path, "r", encoding="utf-8") as f:
            # 将数据集全部加载到内存
            self.lines = [eval(line) for line in tqdm.tqdm(f, desc="Loading Dataset")]
            # 打乱顺序
            self.lines = shuffle(self.lines)
            # 获取数据长度(条数)
            self.corpus_lines = len(self.lines)

    def __len__(self):
        return self.corpus_lines

    def __getitem__(self, item):
        # 得到tokenize之后的文本和与之对应的分类
        text, label = self.get_text_and_label(item)

        if self.data_regularization:
            # 数据正则, 有10%的几率再次分句
            if random.random() < 0.1:
                split_spans = [i.span() for i in re.finditer("，|；|。|？|!", text)]
                if len(split_spans) != 0:
                    span_idx = random.randint(0, len(split_spans) - 1)
                    cut_position = split_spans[span_idx][1]
                    if random.random() < 0.5:
                        if len(text) - cut_position > 2:
                            text = text[cut_position:]
                        else:
                            text = text[:cut_position]
                    else:
                        if cut_position > 2:
                            text = text[:cut_position]
                        else:
                            text = text[cut_position:]


        text_input = self.tokenize_char(text)


        # 添加#CLS#和#SEP#特殊token
        text_input = [self.cls_index] + text_input + [self.sep_index]
        # 如果序列的长度超过self.max_seq_len限定的长度, 则截断
        text_input = text_input[:self.max_seq_len]

        output = {"text_input": torch.tensor(text_input),
                  "label": torch.tensor([label])}
        return output

    def get_text_and_label(self, item):
        # 获取文本和标记
        text = self.lines[item]["text"]
        label = self.lines[item]["label"]
        return text, label

    def tokenize_char(self, text):
        return [self.word2idx.get(char, self.unk_index) for char in text]


def main():
    corpus_dir = os.path.join(DATA_PATH, "corpus", "thuc_news")
    # FasttextDataset(corpus_dir, single_char=False)
    FasttextDataset(corpus_dir, single_char=True)

if __name__ == '__main__':
    main()