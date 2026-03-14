#!/usr/bin/env python3

import argparse

psr = argparse.ArgumentParser()
psr.add_argument("ipt")
psr.add_argument("--ref")
psr.add_argument("-o,--opt", dest="opt")
args = psr.parse_args()

import pandas as pd
import os

zh_dict = pd.read_excel("dict.xlsx", sheet_name="字典表")


def print_explain(explain):
    if "1" in explain:
        j = 0
        offset = 0
        while offset < len(explain):
            index = str.find(explain, "{}".format(j + 1), offset)
            if index == -1:
                print("  {}. {}".format(j, explain[offset:]))
                break
            else:
                if index > offset:
                    print("  {}. {}".format(j, explain[offset:index]))
                offset = index + len(str(j + 1))
                j += 1
    else:
        print("  {}".format(explain))


def query(character):
    result = zh_dict.query("字 == @character", inplace=False)
    print("========= 字: {}".format(character))
    if result.empty:
        return character, None
    elif len(result) == 1:
        return character, result["音"].values[0]
    else:
        for i in range(len(result)):
            row = result.iloc[i]
            print("{}) {}".format(i + 1, row["音"]))
            explain = row["釋義"]
            if not pd.isna(explain):
                print(" 釋義:")
                print_explain(explain)
            explain = row["注釋"]
            if not pd.isna(explain):
                print(" 注釋:")
                print_explain(explain)
        index = int(input("請選擇讀音: ")) - 1
        if index < 0 or index >= len(result):
            return None
        return character, result["音"].values[index]


chinese_punctuation = "、，。？！；：「」『』（）《》〈〉【】—…"

if not os.path.exists(args.ref):
    with open(args.ref, "w") as ref:
        pass

with open(args.ipt, "r") as ipt, open(args.ref, "r+") as ref, open(
    args.opt, "w"
) as opt:
    while True:
        character = ipt.read(1)
        if not character:
            break
        if character.isascii():
            opt.write(character)
            continue
        line = ref.readline()
        if line is not None and line != "":
            assert character == line[0]
            print("========= 字: {}".format(character))
            line = line.split("\t")
            if len(line) < 2:
                opt.write(character)
            else:
                ipa = line[1].rstrip("\n")
                opt.write("\\iparuby{{{}}}{{{}}}".format(character, ipa))
            continue

        q_ch = character
        while True:
            result = query(q_ch)
            if result is not None:
                _, ipa = result
                if ipa is None:
                    if character in chinese_punctuation:
                        opt.write(character)
                        ref.write(character)
                        ref.write("\n")
                        break
                    q_ch = input("請輸入替換字: ")
                    if q_ch == "":
                        opt.write(character)
                        ref.write(character)
                        ref.write("\n")
                        break
                else:
                    ipa = str(ipa)
                    opt.write("\\iparuby{{{}}}{{{}}}".format(character, ipa))
                    ref.write(character)
                    ref.write("\t")
                    ref.write(ipa)
                    ref.write("\n")
                    break
            else:
                q_ch = input("請輸入替換字: ")
                if q_ch == "":
                    opt.write(character)
                    ref.write(character)
                    ref.write("\n")
                    break
