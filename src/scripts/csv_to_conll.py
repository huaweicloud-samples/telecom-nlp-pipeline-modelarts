#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV(Text,Type) → CoNLL 格式转换器

本仓库的实体识别 Notebook 使用 CSV 标注格式（Text,Type 两列），
华为云侧改用 ModelArts Notebook + transformers 微调 BERT-NER，
BERT-NER 需要 CoNLL 格式（每行 token<TAB>label，句子间空行）。

本脚本把 CSV 实体列表转换为 BERT-NER 训练所需的 CoNLL 标注数据：
- 输入：entity_list.csv（Text,Type，如 "iPhone X,DEVICE"）
- 输出：train.conll（token 级标注，B/I/O 序列）

用法：
    python3 csv_to_conll.py \
        --entity-list ../../data/entity_list.csv \
        --corpus ../../data/raw_txt.csv \
        --output ./train.conll \
        --entity-type DEVICE

说明：corpus 用于提供含实体的句子上下文；若 corpus 未标注，
将用 entity-list 自身生成最小训练样本（每个实体名作为一句）。
实际生产请使用带标注的语料。
"""

import argparse
import csv
import re


def load_entities(entity_list_path: str) -> list[tuple[str, str]]:
    """读取 CSV(Text,Type)，返回 [(text, type), ...]"""
    entities = []
    with open(entity_list_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("Text", "").strip()
            etype = row.get("Type", "ENTITY").strip()
            if text:
                entities.append((text, etype))
    return entities


def tokenize_with_entities(text: str, entities: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    对句子做 token 级标注：命中的实体名标注为 B-<TYPE>/I-<TYPE>，其余为 O。
    简化实现：按空白分词，最长实体优先匹配。
    """
    tokens = text.split()
    labels = ["O"] * len(tokens)
    used = [False] * len(tokens)

    # 按实体文本长度降序，贪心匹配
    for ent_text, etype in sorted(entities, key=lambda e: -len(e[0].split())):
        ent_tokens = ent_text.split()
        n = len(ent_tokens)
        for i in range(len(tokens) - n + 1):
            if used[i]:
                continue
            if [t.lower() for t in tokens[i:i + n]] == [t.lower() for t in ent_tokens]:
                labels[i] = f"B-{etype}"
                for j in range(1, n):
                    labels[i + j] = f"I-{etype}"
                    used[i + j] = True
                used[i] = True
                break
    return list(zip(tokens, labels))


def main() -> None:
    parser = argparse.ArgumentParser(description="CSV(Text,Type) -> CoNLL 转换")
    parser.add_argument("--entity-list", required=True, help="entity_list.csv 路径")
    parser.add_argument("--corpus", default=None, help="语料文件（每行一句，可含实体）")
    parser.add_argument("--output", required=True, help="输出 CoNLL 文件路径")
    parser.add_argument("--entity-type", default="ENTITY", help="实体类型名（默认 ENTITY）")
    args = parser.parse_args()

    entities = load_entities(args.entity_list)
    print(f"[INFO] 加载实体 {len(entities)} 条: {[e for e, _ in entities[:5]]}...")

    sentences: list[str] = []
    if args.corpus:
        with open(args.corpus, encoding="utf-8") as f:
            sentences = [line.strip() for line in f if line.strip()]
    else:
        # 兜底：每个实体名作为一句（最少训练样本）
        sentences = [e for e, _ in entities]

    with open(args.output, "w", encoding="utf-8") as out:
        for sent in sentences:
            tagged = tokenize_with_entities(sent, entities)
            for token, label in tagged:
                out.write(f"{token}\t{label}\n")
            out.write("\n")

    print(f"[OK] 已生成 CoNLL 标注数据: {args.output}（{len(sentences)} 句）")


if __name__ == "__main__":
    main()
