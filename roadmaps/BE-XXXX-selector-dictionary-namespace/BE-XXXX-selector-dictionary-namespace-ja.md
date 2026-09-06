[English](BE-XXXX-selector-dictionary-namespace.md) · **日本語**

# BE-XXXX — 名前付きセレクタ辞書 — 要素を一度定義し、どこからでも参照する

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-selector-dictionary-namespace-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | シナリオ記述機能 |
| 関連 | [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md)、[BE-0023](../BE-0023-self-healing-guards/BE-0023-self-healing-guards-ja.md)、[BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment-ja.md)、[BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md)、[BE-0261](../BE-0261-serve-author-yaml-roundtrip/BE-0261-serve-author-yaml-roundtrip-ja.md)、[BE-0050](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md)、[BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis-ja.md) |
<!-- /BE-METADATA -->

## はじめに

シナリオは、使うたびにセレクタを書き写すことで要素を指しています。`components`
（`bajutsu/common/scenario/models/scenario.py:294`）は*ステップの並び*を括り出しますし、
`${params.*}` は任意の文字列フィールドへ代入されます。しかしどちらも*セレクタ*に名前を与えません。
この項目は、名前付きセレクタの辞書を追加します。component とまったく同じく読み込み時に展開する
ので、ランナーもすべての静的解析も解決済みのセレクタを見るだけで、新しい概念を覚えません。

## 動機

showcase のスイートでは、識別子 `search.field` が 9 ファイルにまたがって 25 回、`log.submit` が
13 回書かれています。そのすべてが同じ事実 —「これが検索欄である」— の写しであり、アプリケーション
側で識別子の名前が変わったら、25 か所を一斉に直さないとスイートは中途半端に壊れます。

これは面倒というだけではありません。このリポジトリがすでに作った仕組みを台無しにします。`triage`
の決定的な自己修復は `renameId` の修正案を出し、`apply_fix`（`bajutsu/triage/heuristic.py:170`）は
識別子をトークン単位で置き換えます。ところが `_apply_fix`（`bajutsu/triage/cli.py:292`）が読み、
書き換え、書き戻すのは**1 ファイル** — 失敗したシナリオだけです。9 ファイルに散った識別子は、
そのうち 1 つだけが直ります。リネームは正しく、そして不完全で、その不完全さは次の実行が別の場所で
失敗するまで見えません。

この穴は狭いので、正確に述べる価値があります。読者が「文法はもう対応しているのでは」と考えるのも
もっともだからです。実際、あと一歩です。`_interp_steps`（`bajutsu/common/scenario/expand.py:17`）は
`model_dump` の往復で束縛を代入するので、`${params.x}` はセレクタへ **id の文字列**を運べます。
運べないのは**セレクタ** — `traits` や `within` や `index` を持つマッピング — です。つまり今日
共有できる名前は最も単純な場合に限られ、しかも使うたびに component で包む必要があり、著者が式を
書きたかった場所にステップを強います。

これが入れば、showcase のスイートで読者自身が確かめられます。検索欄は一度だけ定義され、25 か所は
その名前を参照し、リネームは定義を持つ 1 ファイルの 1 行の編集になって、`triage --write` がそれを
完了できます。`bajutsu coverage` が報告する識別子は今までと同じです。展開が、それが見るより先に
起きるからです。

## 詳細設計

### 辞書と、その置き場所

名前から既存の `Selector` へのマッピングを持つファイルです。

```yaml
# selectors/search.yaml
field: { id: search.field }
count: { id: search.count }
firstRow: { id: stable.row.1 }
```

シナリオファイルは、`schema` や `description` と並ぶファイルレベルのキーでこれを参照します。

```yaml
schema: 1
selectors: [selectors/search.yaml, selectors/log.yaml]
scenarios: [...]
```

参照は `contained_ref`（`bajutsu/common/scenario/load_expanded.py:21`）で解決するパスなので、辞書は
スイートのルートの外へ届きません。
[BE-0174](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment-ja.md) が
`use:` と `dataFile:` のために確立した封じ込めを、導き直さずに再利用します。名前は
`<ファイル名の語幹>.<キー>` なので、上の例は `search.field` と `search.count` を定義します。2 つの
辞書が黙って衝突することはなく、1 ファイル内のキーの重複は読み込みエラーです。

### 参照と、なぜ何とも併合しないのか

`Selector` にフィールドを 1 つ足します。

```yaml
tap: { ref: search.field }
```

`ref` は**他のすべてのセレクタフィールドと排他**です。`{ ref: search.field, index: 2 }` は絞り込み
ではなく読み込みエラーです。理由は 2 つ目の prime directive、決定性です。併合を許すなら、名前付きセレクタがすでに
`index: 0` を持っていたときにどうなるかの規則が要り、ありうるどの規則（使用側が勝つ、定義側が勝つ、
エラー）も、著者が使用箇所ごとに覚えておかなければならない規則になります。絞り込みは辞書の中で
別の名前を持つことにします。そこなら一度書かれ、全員がそれを読みます。これは `_non_empty`
（`bajutsu/common/scenario/models/selector.py:39`）の意味も保ちます。セレクタは、ちょうど 1 つの
`ref` を持つか、条件を最低 1 つ持つかのどちらかです。

未知の名前は、その名前と探した辞書を挙げる読み込みエラーです。辞書の項目自体が `ref` である場合は
拒否します。1 段だけで連鎖はなし、つまり名前は必ず 1 行を読めばセレクタに解決します。

### 読み込み時に展開するので、下流は何も変わらない

解決は、ファイルのステップがモデルに入る場所で走ります。その場所は 1 つではなく 2 つです。
`expand_components`（`bajutsu/common/scenario/expand.py:29`）は component のステップを受け取りません。
受け取るのは `resolve` のコールバックで、展開しながら component のファイルを遅延して読み込みます
（`bajutsu/common/scenario/load_expanded.py:84`）。ですから、その前に置いたパスは component の
ステップを一度も見ませんし、component の中に書かれた `ref` は手つかずで残ってしまいます。

そこで解決は読み込みに寄せます。シナリオファイル自身のステップは `expand_components` が走る前に
解決し、各 component のステップはその component が読まれるときに `resolve` のコールバックの中で
解決します。どちらも `${params.*}` の束縛が代入されるより前なので、束縛がソースに書かれていない
名前をでっち上げることはできませんし、展開のあとに `ref` は 1 つも残りません。

端末を使わない読み手はすべて `load_expanded_scenarios`
（`bajutsu/common/scenario/load_expanded.py:63`）を通るので、`audit`、`coverage`、`impact`、
`trace --explain`、`codegen`、そして serve の Web UI のカバレッジ表示は、これまでどおり解決済みの
`Selector` を読み続けます。どれもこの概念を覚える必要がなく、どの出力も変わりません。`run` は
setup を前置する独自のローダーを持ち続け、そこにも同じパスが入ります。

### `serve` のエディタだけは教える必要がある

BE-0261 の Author エディタは、選んだセレクタをステップへ書き込むときに、そのステップのブロックを
再直列化します（`bajutsu/common/scenario/edit.py`）。セレクタが `ref` であるステップにこれを当てると、
名前がリテラルのセレクタに置き換わります。抽象を黙って元に戻すわけで、これはまさに
[BE-0023](../BE-0023-self-healing-guards/BE-0023-self-healing-guards-ja.md) が捕まえようとしている
「静かに甘くする」たぐいの変化です。エディタは代わりに書き込みを拒否して理由を述べ、辞書の項目を
更新することを提案しなければなりません。これは独立した作業単位であり、下流の利用者が変わる唯一の
場所です。

### スキーマのバージョン

ファイルレベルのキーが増えるということは、古い Bajutsu が新しいファイルを読む場面が生じるという
ことです。`ScenarioFile.schema_version`（`bajutsu/common/scenario/models/scenario.py:314`）は
[BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md) がまさに
そのために作った仕組みで、バージョンの門番はフィールドの検証より先に走ります。`selectors:` を使う
ファイルは上がったバージョンを宣言するので、古い読み手は分かりにくい「余分なフィールド」の
エラーではなく、バージョンについてのメッセージで拒否します。

### この項目がやらないこと

セレクタが解決しやすくなるわけではありません。名前で参照された脆いセレクタは、同じ脆いセレクタ
です。`audit` は解決済みの形を採点するので、点も変わりません。価値は、脆さが**1 か所**にまとまる
ことにあります。改善が 25 か所ではなく 1 か所の編集になります。読者に期待を持たせるより、そう
はっきり書くべきです。

### 作業分解（MECE）

1. **辞書ファイルとそのモデル** — 名前から `Selector` へのマッピングを定め、キーの重複を拒否し、
   `<語幹>.<キー>` の命名を決めます。
2. **`selectors:` のファイルレベルキー** — `contained_ref` で解決し、スキーマを繰り上げます。
3. **`Selector.ref`** と排他のバリデータを作り、未知の名前と連鎖した項目に読み込みエラーを
   返します。
4. **解決のパス** — シナリオファイル自身のステップは component の展開より前に、component の
   ステップは `resolve` のコールバックの中で解決します。端末を使わないローダーと `run` のローダーの
   両方に入れます。
5. **Author エディタの拒否**とそのメッセージを実装します。
6. **showcase スイートの移行** — 繰り返された識別子を辞書へ移します。この項目の検証可能な帰結でも
   あります。
7. **ドキュメント** — 文法リファレンスとシナリオのガイドを、それぞれの日本語版とあわせて書きます。

### prime directive との整合性

- **run の経路にモデルを置きません。** 展開はテキスト上の決定的な処理で、実行ループより前に
  起きます。
- **決定性**です。`ref` は何とも併合しないので、名前はちょうど 1 つのセレクタに解決し、覚えるべき
  優先規則がありません。解決と曖昧性の扱いも変わりません。ランナーが見るのは今日と同じ `Selector`
  です。
- **アプリ非依存**です。辞書はシナリオスイートのファイルなので、アプリケーションごとの識別子は
  スイートがすでに置いている場所に留まり、ツール側へは移りません。

## 検討した代替案

- **component を 1 つのセレクタにも使えるよう拡張する。** 却下します。component はステップの
  並びなので、この方法でセレクタに名前を付けると、著者が式を書きたかった場所にステップを強います。
  さらに `expect` ブロックの中で使うセレクタには、ステップでは届きません。入れ子にもなり、使用の
  たびに `use:` が生まれ、その展開を `audit` と `coverage` が見通す必要が出ます。直接参照に比べて
  得るものがありません。
- **`ref` に兄弟フィールドとの併合を許し、絞り込みとして使えるようにする。** 本当に便利ですし、
  著者が最初に求めるのはこれでしょう。ひとまず却下します。優先規則が必要になり、どの規則を選んでも、
  どの要素が指されるかを予測するために著者が使用箇所ごとに頭に置き続けるものになります。辞書の
  項目 1 つを節約するために、読むたびに永久に払う決定性の代償です。
- **辞書を target の config に置く。** 却下します。識別子は実行の設定ではなくスイートに属します。
  また `audit`／`coverage`／`impact` は config を解決せずにシナリオを読み込むので、シナリオを読む
  ために config への依存を生やすことになります。シナリオファイルが単体で読めるという性質も失われ
  ます。その性質こそ、スイートをテキストとしてレビューできる根拠です。
- **リポジトリ全体の規約と lint の規則（「同じ id を N 回より多く繰り返さない」）。** 却下します。
  重複を報告するだけで、共有された事実を置く場所を提供しないので、満たす方法が抑制コメントしか
  ありません。lint はこの項目の*後*なら価値があります。指摘の指す先ができるからです。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] 辞書ファイル、そのモデル、命名の規則。
- [ ] `selectors:` のファイルレベルキーとスキーマの繰り上げ。
- [ ] `Selector.ref`、排他のバリデータ、読み込みエラー。
- [ ] 両方のローダー、両方の入口での解決のパス。
- [ ] Author エディタの拒否。
- [ ] showcase スイートの移行。
- [ ] 両言語のドキュメント。

構築の途中で決めるべき論点です。

- `triage` の `renameId` が、失敗したシナリオではなく辞書ファイルを書き換えるべきかどうか。識別子が
  1 か所に住むようになれば小さな変更で済み、自己修復を「正しい」だけでなく「完全」にするのは
  これです。
- 辞書をスイートをまたいで共有してよいかどうか。今の封じ込めはそれを禁じており、そのために封じ込めを
  緩めるのは、この項目だけで決めるには大きすぎる判断です。
- `audit` が名前付きセレクタの安定度を、解決済みの形だけでなく名前についても報告すべきかどうか。
  そうすればレポートはマッピングを繰り返さず `search.field (stable)` と読めます。
- `record` が、選んだ要素にすでに名前があるとき参照を出力すべきかどうか。現時点の立場は「出さない」
  です。`record` はリテラルを書き、後の工程で括り出します。

## 参考

- [BE-0033 — シナリオ変数 + 軽い制御フロー](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md)
  — id の文字列は運べるがセレクタは運べない、代入の層。
- [BE-0174 — シナリオの component／data 参照をスイートのルート内に封じ込める](../BE-0174-scenario-ref-path-containment/BE-0174-scenario-ref-path-containment-ja.md)
  — `selectors:` の参照が再利用する封じ込めの規則。
- [BE-0119 — バージョン間の読み込みに備えてシナリオスキーマにバージョンを持たせる](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md)
  — 新しいファイルレベルのキーを古い読み手にとって安全にする仕組み。
- [BE-0261 — Author の YAML 編集を serializer で往復させる](../BE-0261-serve-author-yaml-roundtrip/BE-0261-serve-author-yaml-roundtrip-ja.md)
  — 参照をリテラルで上書きすることを拒否しなければならないエディタ。
- [BE-0023 — 「テストを甘くする」防止策](../BE-0023-self-healing-guards/BE-0023-self-healing-guards-ja.md)
  — その静かな置き換えが、なぜ見張るに値する失敗の形なのか。
- [BE-0050 — E2E カバレッジマップ](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md) と
  [BE-0321 — テスト影響分析（変更から影響を受けるステップの特定）](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis-ja.md)
  — 展開がそれらより先に走るため、変わらずに済む 2 つの識別子の読み手。
- `bajutsu/common/scenario/models/scenario.py:294`（`Component`）、`:314`（`schema_version`）、
  `bajutsu/common/scenario/models/selector.py:39`（`_non_empty`）、
  `bajutsu/common/scenario/expand.py:17`（`_interp_steps`）、`:29`（`expand_components` の
  `resolve` コールバック）、`bajutsu/common/scenario/load_expanded.py:21`（`contained_ref`）、
  `:63`、`:84`、
  `bajutsu/triage/heuristic.py:170` と `bajutsu/triage/cli.py:292`（ファイル単位のリネーム）。
