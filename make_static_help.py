# -*- coding: utf-8 -*-
"""
パンセノート ヘルプ 静的HTML（全文テキスト版）生成スクリプト

使い方:
  このスクリプトを、ヘルプのリポジトリ直下（index.html がある場所）に置いて実行する。
    python make_static_help.py
  data/branch.json と data/leaf.json を読み、同じ場所に all.html を書き出す。
  （data/ が無い場合は、スクリプトと同じフォルダの branch.json / leaf.json を読む）

  Excel でヘルプを更新して JSON を作り直したら、このスクリプトを1回実行し、
  all.html も一緒に GitHub Desktop でアップロードする。
"""
import json
import os
import re
import sys
from html import escape

BASE = os.path.dirname(os.path.abspath(__file__))


def find_data_file(name):
    for cand in (os.path.join(BASE, "data", name), os.path.join(BASE, name),
                 os.path.join(os.getcwd(), "data", name), os.path.join(os.getcwd(), name)):
        if os.path.exists(cand):
            return cand
    return None


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


URL_RE = re.compile(r"https?://[^\s<>\"']+")


def render_body(text):
    """本文テキストを段落HTMLにする。空行で段落区切り、URLはリンク化する。"""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks, cur = [], []
    for line in text.split("\n"):
        if line.strip() == "":
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    out = []
    for block in blocks:
        lines = []
        for line in block:
            esc = escape(line)
            esc = URL_RE.sub(lambda m: '<a href="{0}">{0}</a>'.format(m.group(0)), esc)
            lines.append(esc)
        out.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n".join(out)


def main():
    branch_path = find_data_file("branch.json")
    leaf_path = find_data_file("leaf.json")
    if not branch_path or not leaf_path:
        print("branch.json / leaf.json が見つかりません。data フォルダを確認してください。")
        sys.exit(1)
    branch_rows = load_json(branch_path)
    leaf_rows = load_json(leaf_path)
    leaves = {row["leaf_id"]: row for row in leaf_rows}

    # branch_id ごとに、ファイルに書かれた順序のまま子要素を保持する
    children = {}
    branch_title = {}
    for row in branch_rows:
        bid = row.get("branch_id")
        children.setdefault(bid, []).append(row)
        if bid not in branch_title and (row.get("branch_title") or "").strip():
            branch_title[bid] = row["branch_title"].strip()

    used_anchor = {}
    toc = []          # (depth, text, anchor)
    body_parts = []
    leaf_count = 0

    def anchor_for(base_id):
        n = used_anchor.get(base_id, 0) + 1
        used_anchor[base_id] = n
        return base_id if n == 1 else "%s-%d" % (base_id, n)

    def walk(branch_id, depth, path):
        nonlocal leaf_count
        for row in children.get(branch_id, []):
            ctype = (row.get("child_type") or "").upper()
            cid = row.get("child_id")
            if ctype == "LEAF":
                leaf = leaves.get(cid)
                if leaf is None:
                    continue
                title = (leaf.get("leaf_title") or row.get("display_title") or cid).strip()
                anchor = anchor_for(cid)
                toc.append((depth, title, anchor))
                cls = ' class="warning"' if (row.get("body_format") or "").lower() == "warning" else ""
                body_parts.append(
                    '<section id="%s"%s>\n<h%d>%s</h%d>\n%s\n</section>'
                    % (anchor, cls, min(depth + 2, 6), escape(title), min(depth + 2, 6),
                       render_body(leaf.get("body"))))
                leaf_count += 1
            elif ctype == "BRANCH":
                title = (branch_title.get(cid) or row.get("display_title") or cid).strip()
                anchor = anchor_for(cid)
                toc.append((depth, title, anchor))
                bcls = "branch warning" if (row.get("body_format") or "").lower() == "warning" else "branch"
                body_parts.append('<h%d id="%s" class="%s">%s</h%d>'
                                  % (min(depth + 2, 6), anchor, bcls, escape(title), min(depth + 2, 6)))
                if cid in path:
                    body_parts.append("<p>（この項目の内容は、上記の同名の項目をご覧ください）</p>")
                else:
                    walk(cid, depth + 1, path | {cid})

    walk("ROOT", 0, {"ROOT"})

    toc_html = "\n".join(
        '<li class="toc-d%d"><a href="#%s">%s</a></li>' % (min(d, 3), a, escape(t))
        for d, t, a in toc)

    html = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>パンセノート 取扱説明書・ヘルプ（全文テキスト版）</title>
<meta name="description" content="パンセノートの取扱説明書・ヘルプの全文テキスト版です。使い方、音声検索、音声登録、データ保存、ライセンス認証、よくある質問の全文を掲載しています。">
<style>
body { font-family: sans-serif; line-height: 1.8; margin: 2em auto; max-width: 50em; padding: 0 1em; color: #222; }
h1 { font-size: 1.5em; } h2 { font-size: 1.3em; border-bottom: 2px solid #42A89B; padding-bottom: .2em; margin-top: 1.6em; }
h3 { font-size: 1.15em; margin-top: 1.4em; } h4, h5, h6 { font-size: 1.05em; margin-top: 1.2em; }
nav ul { list-style: none; padding-left: 0; } nav li { margin: .15em 0; }
nav .toc-d1 { margin-left: 1.2em; } nav .toc-d2 { margin-left: 2.4em; } nav .toc-d3 { margin-left: 3.6em; }
section.warning { background: #FFF7E0; border: 1px solid #E0C060; border-radius: 6px; padding: .5em 1em; }
.note { color: #555; font-size: .9em; }
</style>
</head>
<body>
<header>
<h1>パンセノート 取扱説明書・ヘルプ（全文テキスト版）</h1>
<p class="note">このページは、ヘルプの全文をそのまま文章として掲載したページです。検索つきの通常のヘルプは <a href="./index.html">こちら</a> です。</p>
</header>
<nav>
<h2>目次</h2>
<ul>
%s
</ul>
</nav>
<main>
%s
</main>
<footer>
<p class="note">このページは branch.json / leaf.json から自動生成されています（make_static_help.py）。内容を直すときは、元のExcelとJSONを直してから生成し直してください。</p>
</footer>
</body>
</html>
""" % (toc_html, "\n".join(body_parts))

    out_path = os.path.join(BASE, "all.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成しました: %s（記事 %d 件）" % (out_path, leaf_count))


if __name__ == "__main__":
    main()
