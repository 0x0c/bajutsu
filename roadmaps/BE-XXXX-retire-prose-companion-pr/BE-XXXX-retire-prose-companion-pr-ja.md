[English](BE-XXXX-retire-prose-companion-pr.md) · **日本語**

# BE-XXXX — companion PR による文言修正の仕組みを廃止し、元の pull request で対処する

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-retire-prose-companion-pr-ja.md) |
| 提案者 | [@handle](https://github.com/handle) |
| 状態 | **実装済み** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | コントリビューターワークフロー |
| 関連 | [BE-0343](../BE-0343-prose-companion-pr/BE-0343-prose-companion-pr-ja.md)、[BE-0203](../BE-0203-claude-code-pr-review/BE-0203-claude-code-pr-review-ja.md) |
<!-- /BE-METADATA -->

## はじめに

Bajutsuの自動レビュー（BE-0203）は、言い回しだけを扱うレンズを2つ持っています。1つは日本語の文章
品質です。もう1つは英語の`docs/*.md`とロードマップ本文の言い回し品質です。BE-0343は、この2つの
レンズが出す指摘に`(non-blocking, prose)`という印を付け、専用の`prose-companion`ジョブを追加しま
した。このジョブは、指摘自身が持つ`suggestion`ブロックを`prose-fix/pr-<N>`ブランチへ機械的に適用
し、貢献者自身のブランチに対する小さなpull requestを開きます。これにより、言い回しの修正が貢献者
自身のpull requestのCI一式を再実行させることはありませんでした。本項目は、このジョブと、その裏に
あるスクリプト（`scripts/prose_companion_pr.py`）、そのテストを廃止します。2つのレンズは、これま
でどおり本物の違反を指摘し続けます。修正が機械的に決まる場合は、これまでどおり`suggestion`ブロッ
クも添えます。変わるのは印と届け方だけです。指摘には、ほかのすべての指摘と同じ、素の
`(non-blocking)`という印を付けます。修正は、その指摘を出したpull request自体への通常のpushとして
届きます。貢献者がほかのレビューコメントに答えるときと同じやり方です。

## 動機

BE-0343が解決しようとした問題は1つでした。言い回しだけの指摘を直そうとして同じpull requestへpush
すると、挙動に影響のない変更のためにpull request全体のCI一式が再実行されてしまう、という問題です。
companion pull requestは、この修正を別の小さなブランチで届けることで、そのコストを避けました。元
のpull requestが開いたままの間もレビューできる形でした。

この利点には、当時の提案もCI一式の節約と引き換えに認めていた継続的なコストが伴っていました。貢献
者自身のブランチへの書き込み権限を持つ、権限の強い自動化アカウントです。独自の信頼境界と
no-op経路を持つジョブです。言い回しの指摘が現れたときだけ実行されるスクリプトです。そして、貢献者
が自分の取り組んでいるpull requestとは別に、気づいてレビューしてマージしなければならない、もう1つ
のpull requestです。companion pull requestのレビューが無償で済むことはありません。提案された
テキストの適用そのものはワンクリックでも、レビューという作業そのものは残ります。

避けようとしていたCI一式のコストと比べると、この標準装備の仕組み（権限の強いアカウント、追加の
ジョブ、スクリプト、そして貢献者が別途追い続けなければならないpull request）のほうが重いコスト
です。本項目はこれを取り除き、より単純な原則に戻します。言い回しだけの指摘も、ほかのレビューコメ
ントと同じで、通常のpushで直すという原則です。この変更が定着したかどうかは、言い回しの指摘のあと
に新しい`prose-fix/pr-<N>`ブランチやpull requestが現れなくなり、代わりに貢献者自身のpull request
へのpushとして修正が届くかで確かめられます。

## 詳細設計

### 変更点

- [`.github/claude-review-prompt.md`](../../.github/claude-review-prompt.md)から、「言い回しだけの
  指摘には`(non-blocking, prose)`という印を付ける」という箇条書きと、`(non-blocking, prose)`という
  印そのものを削除します。どちらのレンズの指摘にも、素の`(non-blocking)`という印を付け、修正が機
  械的に決まる場合は`suggestion`ブロックも添えます。ほかのすべての指摘と同じ扱いです。「文章表現
  にまつわる規範」の節は、2つのレンズの基準（明確で名指しできる違反と、具体的な書き換え）はその
  まま残します。ただし、その根拠から「修正が無償である」という理由は外れます。基準が残る理由は、
  `suggestion`ブロックがすでに書き換えを一行の適用に変えていることと、この2つのレンズが
  [`CLAUDE.md`](../../CLAUDE.md)がすでに求めているバイリンガルドキュメントと`document-writing`の
  house conventionに対する、レビューの唯一の自動チェックであることです。
- [`.github/workflows/claude-review.yml`](../../.github/workflows/claude-review.yml)から
  `prose-companion`ジョブをまるごと削除します。`review`ジョブ（BE-0203。
  [BE-0347](../BE-0347-bounded-ci-review-cycle/BE-0347-bounded-ci-review-cycle-ja.md)により
  openとreopen、`@claude review`に絞られています）には手を入れません。
- `scripts/prose_companion_pr.py`と`tests/test_prose_companion_pr.py`を削除します。
- `tests/test_claude_review_workflow.py`から、`prose-companion`ジョブに関するアサーションと、
  モジュールのdocstringにあるその言及を削除します。残すのは、`review`ジョブ自身のトリガー配線を
  説明する部分だけです。
- [`.apm/skills/claude-review/SKILL.md`](../../.apm/skills/claude-review/SKILL.md)から、印を付けて
  投稿する手順（手順3の適用範囲の注記と、手順5の投稿フォーマット）を削除し、`make skills`でデプ
  ロイ先の`.claude/skills/claude-review/SKILL.md`を同期します。
- [`CLAUDE.md`](../../CLAUDE.md)から「言い回しだけの指摘はcompanion PRとして届く」という箇条書き
  を削除します。[`docs/ai-development.md`](../../docs/ai-development.md)と、その対訳である
  [`docs/ja/ai-development.md`](../../docs/ja/ai-development.md)からは、「文章表現だけの指摘に対
  するcompanion PR（BE-0343）」の節を削除し、自動レビューの説明のすぐそばに短い段落を置き換えま
  す。言い回しだけの指摘も、ほかの指摘と同じく、同じpull requestへの通常のpushで直すという内容
  です。

### 変わらない点

- `.github/claude-review-prompt.md`にある、2つのレンズの判定範囲と基準です。
- `review`ジョブ自体と、BE-0347が定めるその実行タイミングです。
- `roadmaps/BE-0343-prose-companion-pr/`は`実装済み`のままです。実際に実装され、出荷された記録だ
  からです。本項目のidが割り当てられた時点で`Superseded by`のリンクを追加します。本項目が
  `BE-XXXX`という仮の識別子のままである間は、そのidが存在しないため、このリンク付けは後回しにし
  ます（進捗の節に記録します）。本項目自身の`実装 PR`欄を、pull requestができてから埋めるのと同
  じ扱いです。

### すでに開いている3件のcompanion pull request

執筆時点で、companion pull requestが3件開いたままです。#1978、#1980、#1982で、それぞれ元になっ
たpull requestがまだ開いています。ジョブを削除しても、これらには影響しません。それぞれ、ほかの
小さなpull requestと同じようにレビューしてマージできますし、元のpull requestがもう必要としてい
なければ閉じることもできます。本項目がマージされたあとは、新しいcompanion pull requestは開かれ
ません。

## 検討した代替案

- **仕組みは残し、発動条件だけをさらに絞る（たとえば`@claude prose-pr`というコメントでのオンデ
  マンド実行）案。** BE-0343自身の提案は、オンデマンドの発動条件をすでに退けています。手作業の
  手順をまた持ち込んでしまうからです。自動発動の条件をここで同じように絞っても、標準装備の仕組
  みはそのまま残ります。本項目が取り除こうとしているコストは、何も減りません。
- **`(non-blocking, prose)`という印だけを外し、ジョブ自体は休眠させたまま残す案。** どの指摘も
  たどり着かないジョブは、生きたGitHub Appのアカウントと、通し続けなければならない独自のテスト
  一式を抱えたまま残る、死んだコードです。削除する手間は残す手間と変わらず、あとの読み手に説明
  するものも残りません。
- **companion PRによる届け方だけでなく、2つのレンズ自体を丸ごと削除する案。** 2つのレンズが下す
  判定そのものの価値が下がったわけではありません。修正を2つ目のpull requestで届ける方法が、割
  に合わなくなっただけです。レンズまで削除すると、[`CLAUDE.md`](../../CLAUDE.md)がいまも求めて
  いるhouse convention（バイリンガルドキュメントと`document-writing`）に対するレビューのカバレ
  ッジが、気づかないうちに下がってしまいます。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [x] `.github/claude-review-prompt.md`から`(non-blocking, prose)`という印を削除し、「文章表現
  にまつわる規範」の根拠を書き直す
- [x] `.github/workflows/claude-review.yml`から`prose-companion`ジョブを削除する
- [x] `scripts/prose_companion_pr.py`と`tests/test_prose_companion_pr.py`を削除し、
  `tests/test_claude_review_workflow.py`を整理する
- [x] `.apm/skills/claude-review/SKILL.md`から印を付けて投稿する手順を削除し、`make skills`で
  `.claude/skills/claude-review/SKILL.md`を同期する
- [x] `CLAUDE.md`の箇条書きと、`docs/ai-development.md` / `docs/ja/ai-development.md`の該当節を
  更新する
- [ ] 本項目のidが割り当てられた時点で、`roadmaps/BE-0343-prose-companion-pr/`に相互リンクとなる
  `Superseded by`を追加する（後回し。「変わらない点」を参照）

### ログ

- 提案と同じpull requestで、まるごと出荷しました
  （[`propose-and-build`](../../.apm/skills/propose-and-build/SKILL.md)）。当時すでに開いていた
  3件のcompanion pull request（#1978、#1980、#1982）は、閉じずに、独立してマージできる通常の
  pull requestとして残しました。

## 参考

[BE-0343](../BE-0343-prose-companion-pr/BE-0343-prose-companion-pr-ja.md)（本項目が廃止する仕組
み）、[BE-0203](../BE-0203-claude-code-pr-review/BE-0203-claude-code-pr-review-ja.md)（2つの文章
表現レンズがどちらも属する自動レビュー）、
[BE-0347](../BE-0347-bounded-ci-review-cycle/BE-0347-bounded-ci-review-cycle-ja.md)（`review`
ジョブが保つ発動条件の絞り込み）、`document-writing`・`english-document-writing`・
`japanese-document-writing`の各スキル（2つの文章表現レンズが従う規範）。
