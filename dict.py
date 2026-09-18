#!/usr/bin/env python3

import argparse
import os
from dataclasses import dataclass
from enum import Enum

import opencc
import pandas as pd


CHINESE_PUNCTUATION = "、，。？！；：「」『』（）《》〈〉【】—…"

T2NEW = opencc.OpenCC("t2gov/t2gov/t2new.json")
T2GOV = opencc.OpenCC("t2gov/t2gov/t2gov.json")
ZH_DICT = pd.read_excel("dict.xlsx", sheet_name="字典表")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("ipt", help="輸入文件")
    parser.add_argument("--ref", required=True, help="記錄文件")
    parser.add_argument("-o", "--opt", dest="opt", required=True, help="輸出文件")
    parser.add_argument(
        "--check",
        action="store_true",
        help="核對 ref 中記錄的讀音，無效時重新查詢並覆蓋",
    )
    return parser.parse_args()


def print_explain(explain: str) -> None:
    if "1" not in explain:
        print("  {}".format(explain))
        return
    j = 0
    offset = 0
    while offset < len(explain):
        index = explain.find(str(j + 1), offset)
        if index == -1:
            print("  {}. {}".format(j, explain[offset:]))
            break
        if index > offset:
            print("  {}. {}".format(j, explain[offset:index]))
        offset = index + len(str(j + 1))
        j += 1


class QueryType(Enum):
    CHAR = 1
    CHAR_WITH_PRON = 2
    REPLACE = 3


@dataclass
class QueryResult:
    ty: QueryType
    character: str
    pron: str | None = None


def lookup(character: str) -> pd.DataFrame:
    char_new = T2NEW.convert(character)
    char_gov = T2GOV.convert(character)
    result = ZH_DICT.query(
        "字 == @character or 字 == @char_new or 字 == @char_gov", inplace=False
    )
    return result[result["音"].notna()]


def readings(result: pd.DataFrame) -> list[str]:
    return [str(pron) for pron in result["音"].tolist()]


def print_entries(result: pd.DataFrame) -> None:
    for i in range(len(result)):
        row = result.iloc[i]
        print("{}) {} {}".format(i + 1, row["字"], row["音"]))
        explain = row["釋義"]
        if not pd.isna(explain):
            print(" 釋義:")
            print_explain(explain)
        explain = row["注釋"]
        if not pd.isna(explain):
            print(" 注釋:")
            print_explain(explain)


def choose_reading(count: int) -> int | None:
    while True:
        choice = input("請選擇讀音 (0=替換字): ").strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= count:
            return int(choice) - 1
        print("請輸入 0 到 {} 之間的數字".format(count))


def query(character: str) -> QueryResult:
    print("========= 字: {}".format(character))
    result = lookup(character)
    options = readings(result)
    if not options:
        return QueryResult(QueryType.CHAR, character)
    if len(options) == 1:
        return QueryResult(QueryType.CHAR_WITH_PRON, character, options[0])
    print_entries(result)
    index = choose_reading(len(options))
    if index is None:
        return QueryResult(QueryType.REPLACE, character)
    return QueryResult(QueryType.CHAR_WITH_PRON, character, options[index])


def resolve_interactively(character: str) -> QueryResult:
    target = character
    while True:
        result = query(target)
        if result.ty is QueryType.CHAR_WITH_PRON:
            return result
        target = input("請輸入替換字: ")
        if target == "":
            return QueryResult(QueryType.CHAR, character)


def recorded_pron(entry: str | None) -> str | None:
    if entry is None:
        return None
    parts = entry.rstrip("\r\n").split("\t")
    if len(parts) < 2:
        return None
    return parts[1]


def is_valid_reading(character: str, pron: str) -> bool:
    return pron in readings(lookup(character))


def ruby(character: str, pron: str) -> str:
    return "\\iparuby{{{}}}{{{}}}".format(character, pron)


def process_character(
    character: str, entry: str | None, check: bool
) -> tuple[str, str | None]:
    pron = recorded_pron(entry)
    if pron is not None:
        if (
            not check
            or character in CHINESE_PUNCTUATION
            or is_valid_reading(character, pron)
        ):
            print("========= 字: {}".format(character))
            return ruby(character, pron), None
        print("讀音「{}」不在字典中，重新查詢".format(pron))
    elif character in CHINESE_PUNCTUATION:
        return character, character

    result = resolve_interactively(character)
    if result.ty is QueryType.CHAR_WITH_PRON:
        return ruby(character, result.pron), "{}\t{}".format(character, result.pron)
    return character, character


def read_ref(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="") as ref:
        return ref.readlines()


def ref_eol(lines: list[str]) -> str:
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return os.linesep


def write_ref(path: str, lines: list[str]) -> None:
    with open(path, "w", newline="") as ref:
        ref.writelines(lines)


def run(
    ipt_path: str, opt_path: str, ref_lines: list[str], check: bool, eol: str
) -> None:
    index = 0
    with open(ipt_path, "r") as ipt, open(opt_path, "w") as opt:
        in_sqr_bracket = 0
        while True:
            character = ipt.read(1)
            if not character:
                break
            if character == "[":
                in_sqr_bracket += 1
                opt.write(character)
                continue
            if character == "]":
                in_sqr_bracket -= 1
                opt.write(character)
                continue
            if in_sqr_bracket > 0 or character.isascii():
                opt.write(character)
                continue

            if index < len(ref_lines):
                entry = ref_lines[index]
                if entry[:1] != character:
                    raise ValueError(
                        "ref 第 {} 行是「{}」，與輸入的「{}」不符".format(
                            index + 1, entry[:1], character
                        )
                    )
            else:
                entry = None
            index += 1

            output, new_entry = process_character(character, entry, check)
            opt.write(output)
            if new_entry is not None:
                if index <= len(ref_lines):
                    ref_lines[index - 1] = new_entry + eol
                else:
                    ref_lines.append(new_entry + eol)


def main() -> None:
    args = parse_args()
    ref_lines = read_ref(args.ref)
    eol = ref_eol(ref_lines)
    try:
        run(args.ipt, args.opt, ref_lines, args.check, eol)
    finally:
        write_ref(args.ref, ref_lines)


if __name__ == "__main__":
    main()
