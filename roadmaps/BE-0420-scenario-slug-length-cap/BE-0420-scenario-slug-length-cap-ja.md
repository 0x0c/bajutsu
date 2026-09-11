[English](BE-0420-scenario-slug-length-cap.md) · **日本語**

# BE-0420 — シナリオの証跡ディレクトリ名のスラグ長に上限を設ける

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-0420](BE-0420-scenario-slug-length-cap-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **実装済み** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0420") |
| 実装 PR | [#1995](https://github.com/bajutsu-e2e/bajutsu/pull/1995) |
| トピック | コードベース品質・技術的負債 |
| 関連 | [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)、[BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md) |
<!-- /BE-METADATA -->

## はじめに

Bajutsu は各シナリオの[証跡](../../docs/ja/glossary.md#証跡-capturepolicy-trace-triage)を
`runs/<runId>/<sid>/` に書き込みます。`_evidence_sid()`
([`bajutsu/common/runner/pipeline.py:82`](../../bajutsu/common/runner/pipeline.py)) が、実行順を
示す2桁のインデックスと、2種類のスラグのどちらか一方を組み合わせて `sid` を作ります。ファイルから
読み込んだシナリオでは `sanitize_source_stem(s.source_stem)` を使います。これは由来ファイル自身の
stem から、安全でない文字を置き換えたものです
([BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)、
**実装済み**)。由来ファイルがわからないシナリオは `scenario_slug(s.name)` にフォールバックします。
どちらの関数も、長さには上限を設けません。由来ファイルの stem が長い場合も、シナリオの `name` が
長い場合も、`sid` は際限なく長くなり、証跡ディレクトリの書き込みに失敗します。

本項目は、両方の関数に固定の長さ上限を追加します。`sanitize_source_stem()` は Unicode の文字を
そのまま残すため、上限は UTF-8 のバイト数で数えます。`scenario_slug()` は入力を先に ASCII へ削る
ため、この関数では文字数とバイト数が一致します。どちらの場合も、上限を超えたスラグは際限なく
伸びる代わりに切り詰められます。`sid` は、何に由来していても安全な長さに収まります。

### やらないこと

- **トップレベルの run ディレクトリ(`runs/<runId>/`、UTC タイムスタンプ)は変更しません。** 本項目
  が触れるのは、その下にネストされた2つのスラグだけです。
- **`Scenario.name` と `Scenario.source_stem` は切り詰めません。** `name` は
  `manifest.json` の `scenario` フィールド、`report.html`、serve の run ピッカー向けに行サフィックス
  を照合する `declared_name()`
  ([`bajutsu/common/scenario/expand.py:117`](../../bajutsu/common/scenario/expand.py))にも
  使われます。`source_stem` の読み手は今日、`_evidence_sid()` 自身の1箇所だけです。それでも
  本項目が上限を設けるのは、そこから導かれるスラグだけです。`source_stem` というフィールド自体は
  対象外です。こうしておけば、将来 `source_stem` を読む2番目の箇所ができても、気づかないうちに
  切り詰め済みの値を受け取ることがありません。
- **新しい重複回避カウンタは導入しません。** `_evidence_sid()` が作るすべての `sid` は
  `{i:02d}-` インデックスプレフィックスを持ち、切り詰め後も含めて、同一 run 内での一意性を
  保証しています。一方、プレフィックスを持たないむき出しのスラグを作るフォールバックが2箇所あり、
  切り詰め後は今日と違って衝突する可能性があります。

  - `scenario_slug(scenario.name)`:`run_scenario` の直接呼び出しで `scenario_id` が渡されない場合
    ([`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py))
  - `scenario_slug(r.scenario)`:レポートのマトリクスで `sid` を持たない結果に使う場合
    ([`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py))

  どちらも、`run` コマンド自身が実際にたどる経路には乗りません。`pipeline.py:796` は常に
  `scenario_id=sid` を渡し、`pipeline.py:1253` は `_evidence_sid()` 自身を通じて `sid` を組み立てる
  からです。本項目はこの2箇所を変更しません。`scenario_slug()` に上限を設けるだけで、この2箇所が
  作る値も短くなります。
- **`record` 自身のファイル命名は変更しません。** 保存名を明示しないで記録したシナリオは、
  記録セッションの自然言語ゴールにフォールバックします
  (`scenario_out_name()`、[`bajutsu/serve/helpers.py:454`](../../bajutsu/serve/helpers.py))。この
  関数にも長さ上限はありません。本項目が上限を設けるのは、長いファイル名が生みうる証跡ディレクトリ
  のスラグであって、ファイル名自体ではありません。長い `*.yaml` ファイル名は、ディスク上で読める
  ままであり、それ自体は何も妨げません。それが生む証跡ディレクトリのほうが、実行のたびに実際の
  ファイルシステムの上限と競合します。

## 動機

[BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)
は、本項目が最初に報告された失敗を、すでに解消しています。BE-0417 が入る前は、
[データ駆動シナリオ](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md)の
CSV展開後の各行が、自分自身の `key=value` というパラメータ文字列を `name` に持っていました。
列数の多い行や値が長い行では、`scenario_slug(s.name)` の出力が巨大な `sid` になりえました。今は
両方のローダーが、展開後のすべての行に `source_stem` を刻みます。

- [`bajutsu/run/cli.py:201`](../../bajutsu/run/cli.py)
- [`bajutsu/common/scenario/load_expanded.py:91`](../../bajutsu/common/scenario/load_expanded.py)

1つのファイルに由来する行は、今ではすべて、そのファイル自身の短い stem を共有します。
`_evidence_sid()` は、データ駆動シナリオに対してはもう `scenario_slug()` に到達しません。

同じ種類の失敗は、どちらのスラグ関数も上限を持たない2つの経路には、今も残っています。1つ目は
長い由来ファイルです。`record` 自身の自動命名は、操作者が `--out` と明示的な名前のどちらも
与えない場合、記録セッションの自然言語ゴールにフォールバックします(「やらないこと」参照)。冗長な
ゴール——「保存済みのカードでログインし、注文の合計と確認メールを確認する」——は、まさにその長さの
`*.yaml` ファイルを生みます。そのファイルを後から実行するたびに、同じ長さの証跡ディレクトリを
作ろうとします。

2つ目の経路は、ファイルローダーの外で直接組み立てられたシナリオです。「やらないこと」に挙げた
プレフィックスなしのフォールバック2箇所が、これに当たります。加えて、ファイルから読み込む代わりに
`Scenario` を自分で組み立てる `run_scenario()` の呼び出し元も当てはまります。例えば
[`demos/showcase/record/generate_from_nl.py`](../../demos/showcase/record/generate_from_nl.py)
です。これらはどれも、上限のない `scenario_slug(s.name)` にフォールバックします。

両方の関数に上限を設ければ、この2つの経路を、それぞれの唯一の定義箇所で塞げます。ここは
`_evidence_sid()` とプレフィックスなしの2つのフォールバックが、すでに共有している一点です。
本項目が実装されれば、由来ファイルが長い、あるいは由来ファイルがわからずシナリオ自身の `name`
が長いシナリオも、最後まで実行を終え、証跡ディレクトリを書き込めます。

## 詳細設計

1. **共有のバイト安全な切り詰めヘルパー。** `_MAX_SLUG_BYTES = 60` と、非公開の
   `_cap_bytes(slug: str) -> str` を、`scenario_slug()` と `sanitize_source_stem()` のそばに追加
   します。場所は
   [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
   です。`_cap_bytes` はまず `slug` を UTF-8 にエンコードします。それが `_MAX_SLUG_BYTES` を
   超える場合、エンコード後のバイト列をその上限で切り詰め、`errors="ignore"` を付けてデコードし
   ます。これにより、切れ端になった末尾の文字は例外を出さずに落ちます。1つのヘルパー、1つの上限が
   両方の関数に効きます。`scenario_slug()` の出力は ASCII だけなので、バイト単位の切り詰めは
   文字単位の切り詰めとまったく同じです。既存の `.strip("-").lower()` の順序にも影響しません。
2. **`scenario_slug()` は最後にこれを呼びます。** 既存の正規表現が、まず英数字以外の連続を `-`
   にまとめ、結果を strip して小文字化します。次に、その文字列を `_cap_bytes` に通し、続けて
   `.rstrip("-")` を呼びます。切り詰めが残したハイフンを落とすためです。その結果が空になる場合は
   `"scenario"` にフォールバックします。記号だけの名前に対して、この関数がすでに返している
   フォールバックと同じです。
3. **`sanitize_source_stem()` は最後にこれを呼びます。** 既存の `re.sub(r"[^\w.-]", "_", stem)`
   が、まず安全でない文字をすべて置き換えます。次に、その結果を `_cap_bytes` に通します。追加の
   フォールバックは不要です。エンコード後の最小の文字は1バイトなので、60バイトという上限が空文字列
   を生むのは、入力自体がすでに空だった場合に限られます。`re.sub` は、空でない `stem` からそれを
   生み出せません。由来ファイルの stem が空になることはなく、`*.yaml` ファイルに対する `Path.stem`
   は常に1文字以上を返すからです。
4. **呼び出し箇所の変更はありません。** `_evidence_sid()` の2つの分岐も、「やらないこと」に挙げた
   プレフィックスなしの2箇所も、すべて `scenario_slug()` か `sanitize_source_stem()` を直接呼んで
   います。上限は、どの呼び出し箇所にも触れずに、そのすべてに届きます。
5. **ドキュメント。** [`docs/reporting.md`](../../docs/reporting.md) /
   [`docs/ja/reporting.md`](../../docs/ja/reporting.md) の、既存の `runId` / `stepId` の説明の
   そばに、短い段落を追加します。`sid` が由来しうる2つの由来と、共有の上限を明記します。
6. **テスト。**
   - `scenario_slug()` のユニットテストを追加します。上限を超える長さの名前が、末尾にハイフンを
     残さない形で切り詰められることを確認します。
   - `sanitize_source_stem()` のユニットテストを追加します。上限を超える長さの ASCII の stem が、
     60バイトに切り詰められることを確認します。
   - `sanitize_source_stem()` のユニットテストをもう1件追加します。`決済フロー` の繰り返しなど、
     マルチバイト文字からなる上限超えの stem が、60バイト以下の、妥当な UTF-8 として返ることを
     確認します。文字の途中で切れていないことも確認します。
   - `record` を `--out` なしで使う事例を再現するユニットテストを追加します。長い自然言語ゴールが
     `scenario_out_name()` と `sanitize_source_stem()` を経て、上限内の `sid` になることを
     確認します。
   - 切り詰め後にスラグが衝突しても、既存の `{i:02d}-` インデックスプレフィックスによって、
     別々のディレクトリに収まることを確認するテストを追加します。

## 検討した代替案

| 代替案 | 採らなかった理由 |
|---|---|
| 上限を超えるスラグを持つシナリオを拒否する。run 履歴ラベルに対する [BE-0404](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer-ja.md) の「切り詰めず拒否する」規則(`MAX_LABEL_LENGTH`、`bajutsu/common/report/manifest.py:13`)にならう案 | run 履歴ラベルは、操作者が入力し、そのまま保たれることを期待するテキストです。だからこそ拒否すれば、操作者に判断を返せます。一方 `sid` のスラグは、誰も直接書いていない、派生的なファイルシステム id です。長い自然言語ゴールを記録する操作者は、ファイル名を選んでいるのではなく、フローを説明しているだけです。その説明のために run 全体を拒否すれば、シナリオ全体が止まります。読める形に切り詰めたスラグなら、それを止めずに済みます。 |
| スラグを切り詰める代わりに、固定長のダイジェストへハッシュ化する | ダイジェストは元の名前や由来ファイルの stem の情報を一切残しません。両方の関数がシナリオからディレクトリ名を導く理由、つまり操作者が結果を見ただけで見分けられるようにするという狙いそのものが崩れます。切り詰めであれば、見分けの手がかりとなる先頭部分が残ります。 |
| スラグ関数が動く前に、`Scenario.name` や `Scenario.source_stem` 自体を切り詰める | `name` は `manifest.json` の `scenario` フィールド、`report.html`、`declared_name()` の行サフィックス照合にも使われます。`source_stem` の読み手は今日1箇所だけですが、フィールド自体を切り詰めれば、将来の2番目の読み手に気づかないまま短縮済みの値を渡してしまいます。`sid` だけが、純粋にファイルシステム用の識別子です。本項目が上限を設けるのは `sid` だけである理由です。 |
| 上限をターゲットごとに設定可能にする | この上限が守るのはファイルシステムへの書き込みであり、アプリの挙動ではありません。app-agnostic という prime directive 3 の境界は、アプリごとに変わる違いを設定に置くためのものです。対象アプリが何であっても変わらないファイルシステムの定数を置く場所ではありません。 |
| 行を区別する接尾辞を残し、シナリオ名自身の先頭側を切り詰めるか、先頭と末尾の両方を残す(中間だけを落とす)案 | この案は、データ駆動の通常のケース(「動機」参照)ではもう `scenario_slug()` に届かなくなった接尾辞と引き換えになります。そうしたシナリオの行は、今ではどれも1つの由来ファイルの stem を共有し、上限のあるなしにかかわらず、`{i:02d}-` インデックスだけで区別されているからです。本項目が実際に対応する2つの経路——長いファイル名、長いメモリ内 `name`——では、操作者が一目で見分けるのは先頭側です。先頭と末尾を両方残す案は、そのどちらかをわずかに多く残せますが、切り出しが2箇所になり、テストの組み合わせが増え、スラグが一目で1つの連続した名前には読めなくなります。 |
| `scenario_out_name()`(`record` 自身のファイル命名)のほうに、あるいはそれに加えて、上限を設ける | `--out` なしの `record` セッションが生むケースしか直りません。同じくらい長い名前を持つ、手で作成したファイルは、`sanitize_source_stem()` を素通りして同じ失敗に達します。2つのスラグ関数のほうに上限を設ければ、記録済み、手作成、メモリ内組み立てのどの経路でも、由来ファイルの名前の付き方によらず、1つの定義だけで `sid` に届くすべてを守れます。 |

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解(作業の単位ごとに1つ)に対応し、ログには変更内容と時期(古い順)を PR へのリンクと
> ともに記録します。

- [x] 作業単位 1——`bajutsu/common/orchestrator/types/_functions.py` の `scenario_slug()` と
  `sanitize_source_stem()` の隣に、`_MAX_SLUG_BYTES = 60` とプライベートな `_cap_bytes()`
  ヘルパーを追加しました。文字列を UTF-8 に符号化し、上限を超えた場合だけ符号化後のバイト列を
  上限まで切り出します。復号時に `errors="ignore"` を指定しているので、切断面にかかった文字は
  例外を送出せずに捨てられます。
- [x] 作業単位 2——`scenario_slug()` は、小文字化とハイフンへの畳み込みを終えた結果を
  `_cap_bytes()` に通し、続けて `.rstrip("-")` で切断面に残りうる区切り文字を落とします。記号
  だけの名前に対する既存の `"scenario"` フォールバックは、これまでどおり働きます。
- [x] 作業単位 3——`sanitize_source_stem()` は、`re.sub()` の結果を `_cap_bytes()` に通します。
  追加のフォールバックは不要です。UTF-8 の最長の文字は4バイトで、上限を大きく下回ります。
  空でない語幹であれば、少なくとも先頭の1文字は必ず切断面より手前に残ります。
- [x] 作業単位 4——設計どおり、呼び出し側は1箇所も変更していません。`_evidence_sid()` の2つの
  分岐は、いずれも上限付きの2つの関数のどちらかを直接呼んでいます。素のフォールバック2箇所
  （`loop/_functions.py:645` と `report/manifest.py:127`）も同じです。そのため、定義1箇所への
  変更だけで上限がすべてに行き渡ります。
- [x] 作業単位 5——`docs/reporting.md` と `docs/ja/reporting.md` の、既存の `runId` / `sid` /
  `stepId` を説明する箇所に段落を1つ追加しました。共通の上限、文字数ではなくバイト数で数える
  理由、そして `Scenario.name` 自体は切り詰めないことを説明しています。
- [x] 作業単位 6——`tests/runner/test_pipeline.py` の、BE-0417 の既存のスラグのテストの隣に、
  ユニットテストを7つ追加しました。設計が挙げた5つより2つ多くなっています。1つは、区切り文字が
  切断面に残るケースを、長い名前のテストの2つ目のアサーションではなく独立したテストにしたためで
  す。回帰したときに、どの性質が壊れたのかがテスト名でわかります。もう1つは、作業単位 3 の主張の
  うちどのテストも押さえていなかった点を、セルフレビューで見つけて追加したものです。7つの内訳は
  次のとおりです。
  - 末尾にハイフンが残らない ASCII のスラグ
  - 切断面が区切り文字に当たるケース
  - 上限で切り詰めた ASCII の語幹
  - 上限が文字の内側に落ちるマルチバイトの語幹
  - 語幹の先頭1文字は必ず残ること（作業単位 3 でフォールバックを省いた根拠）
  - `scenario_out_name()` を経由する `record` の `--out` なしの経路
  - 切り詰めた結果スラグが衝突しても、`{i:02d}-` の接頭辞によって `sid` が区別されること

ログ：

- [#1995](https://github.com/bajutsu-e2e/bajutsu/pull/1995)——作業単位すべて（6つ）を実装し、本項目
  を完了しました。2つのスラグ関数の隣に `_MAX_SLUG_BYTES = 60` と非公開の `_cap_bytes()` を
  追加しました。`scenario_slug()` と `sanitize_source_stem()` は、それぞれ最後にこれを呼びます。
  由来ファイル名が長い場合も、メモリ上の `name` が長い場合も、ファイルシステムが受け付けない
  `sid` はもう生まれません。呼び出し箇所は1つも変更していません。
  セルフレビューで、当初の記述の誤りを2点訂正しました。1点目は、`scenario_slug` の docstring と
  `reporting.md` の両言語版が、すべての `sid` が実行順の接頭辞を持つと書いていた点です。本項目
  自身の「やらないこと」が、プレフィックスなしのフォールバック2箇所についてこれを否定しています。
  2点目は、`sanitize_source_stem()` で空文字列へのフォールバックを省いた根拠です。UTF-8 の最小の
  文字が1バイトであることを挙げていましたが、根拠となるのは最長が4バイトであることです。どの
  テストも押さえていなかったこの不変条件を、7つ目のテストで固定しました。

## 参考

- [BE-0417 — シナリオの結果ディレクトリ名を、読み込み元のシナリオファイルにちなんだ名前にする](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)(実装済み、[#1977](https://github.com/bajutsu-e2e/bajutsu/pull/1977))
- [BE-0031 — データ駆動シナリオ](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md)
- [BE-0404 — project 階層を org と target に畳む](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer-ja.md)
- [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`bajutsu/common/report/manifest.py`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py`](../../bajutsu/common/orchestrator/loop/_functions.py)
- [`bajutsu/serve/helpers.py`](../../bajutsu/serve/helpers.py)
- [`docs/reporting.md`](../../docs/reporting.md)
