[English](BE-XXXX-scenario-slug-length-cap.md) · **日本語**

# BE-XXXX — シナリオの証跡ディレクトリ名のスラグ長に上限を設ける

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-scenario-slug-length-cap-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | コードベース品質・技術的負債 |
| 関連 | [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)、[BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md) |
<!-- /BE-METADATA -->

## はじめに

Bajutsu は各シナリオの[証跡](../../docs/ja/glossary.md#証跡-capturepolicy-trace-triage)を
`runs/<runId>/<sid>/` に書き込みます。`sid` は、実行順を示す2桁のインデックスと、
[`scenario_slug()`](../../bajutsu/common/orchestrator/types/_functions.py) が作るスラグを
組み合わせた名前です。`scenario_slug()` はシナリオの `name` フィールドを `[0-9a-z-]` の文字
だけに削りますが、長さには上限を設けません。`name` が長いシナリオでは、スラグも際限なく長く
なります。本項目は、`scenario_slug()` の出力に固定の長さ上限を追加します。上限を超えたスラグは、
際限なく伸びる代わりに切り詰められます。シナリオの `name` がどれだけ長くても、証跡ディレクトリの
名前は安全な長さに収まります。

### やらないこと

- **トップレベルの run ディレクトリは変更しません。** `runs/<runId>/` は UTC タイムスタンプで、
  本項目が触れるのは、その下にネストされたシナリオごとのスラグだけです。
- **`Scenario.name` 自体は切り詰めません。** `manifest.json` の `scenario` フィールド、
  `report.html`、serve の run ピッカー向けに行サフィックスを照合する `declared_name()`
  ([`bajutsu/common/scenario/expand.py:117`](../../bajutsu/common/scenario/expand.py)) など、
  `name` を読む他のすべての箇所は、これまでどおり全文を読み続けます。切り詰めるのは、そこから
  導かれるファイルシステム用のスラグだけです。
- **新しい重複回避カウンタは導入しません。** run が書き込むすべての `sid` は `{i:02d}-`
  インデックスプレフィックスを持ち、切り詰め後も含めて、同一 run 内での一意性を保証しています。
  このプレフィックスをそのまま残す理由は、
  [BE-0417](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)
  と同じです。一方、プレフィックスを持たないむき出しのスラグを作るフォールバックが2箇所あります。
  `run_scenario` の直接呼び出しで `scenario_id` が渡されないときの `scenario_slug(scenario.name)`
  ([`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py))と、
  レポートのマトリクスで `sid` を持たない結果に使う `scenario_slug(r.scenario)`
  ([`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py))です。
  どちらも、切り詰め後は今日と違って衝突する可能性があります。しかし、run が実際にたどる経路には
  どちらも乗りません。`pipeline.py:782` は常に `scenario_id=sid` を渡し、`pipeline.py:820` は
  `result.sid = sid` を書き込むからです。本項目はこの2箇所を変更しません。
- **BE-0417 自身の改名は変更しません。** BE-0417 は別の、まだ実装されていない項目です。ファイルから
  読み込んだシナリオのスラグの由来を、`name` ではなく由来ファイルの stem(拡張子を除いたファイル名)
  に変える提案です。新しい `sanitize_source_stem()` 関数を導入します。本項目は `scenario_slug()`
  が今日すでに作っているスラグの長さを制限するだけで、その由来をどちらにするかには立場を取りません。
  BE-0417 が実装される際、`sanitize_source_stem()` にも同じ上限を持たせるかどうかは、その項目の
  実装者が決めることです。

## 動機

[データ駆動シナリオ](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md)は、
CSV(Comma Separated Values、カンマ区切り値)の行ごとに1つの生成済みシナリオを実行します。
`_row_name()`([`bajutsu/common/scenario/expand.py:102`](../../bajutsu/common/scenario/expand.py))
は、各行の `name` を組み立てるとき、列をすべて `key=value` の形で連結します。

```
{scenario_name} [row {i}: k1=v1, k2=v2, ...]
```

列数の多い行や、値が長い列を持つ行では、`name` が長くなりすぎます。`scenario_slug()` は
それをそのまま巨大な `sid` に変換するため、その名前のディレクトリを作る段階で run が失敗します。

操作者がこの問題に行き当たるのは、同じシナリオを複数のパラメータの組み合わせで実行するときです。
これはデータ駆動シナリオが存在する理由そのものの使い方です。しかも run が壊れるのは、シナリオ
自身のロジックとは無関係な箇所です。

`scenario_slug()` の出力を制限すれば、この問題を1箇所だけで解決できます。`sid` を組み立てる
呼び出し箇所は、すべて次の1つの関数を経由しています。

- [`bajutsu/common/runner/pipeline.py:270`](../../bajutsu/common/runner/pipeline.py) と `:1239`
- [`bajutsu/common/report/manifest.py:127`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py:645`](../../bajutsu/common/orchestrator/loop/_functions.py)

この1つの関数を直すだけで、4箇所すべてに効果が及びます。データ駆動のケースを特別扱いする必要は
ありません。

先頭を残す切り詰め方には、受け入れる結果が1つあります。シナリオ自身の `name` だけで
`_MAX_SLUG_LENGTH` に近づいていると、同一 run の複数行が同じスラグになりえます。
`_row_name()` が付け足す行を区別する `key=value` の部分が、切り詰めの先に落ちるからです。
それでも `{i:02d}-` インデックスプレフィックスがディレクトリを区別します。「やらないこと」の
プレフィックスなしフォールバック2箇所で頼っているのと同じ保証です。犠牲になるのは、書き込みの
成否ではなく、操作者がスラグのどの文字を目にするかだけです。

本項目が実装されれば、CSV の行が長い値や多数の列を持つデータ駆動シナリオも、最後まで実行を終え、
証跡ディレクトリを書き込めます。現状では、同じシナリオは証跡ディレクトリを作成する時点で失敗
します。

## 詳細設計

1. **`scenario_slug()` 内部への長さ上限の追加。**
   [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
   の、この関数のそばに `_MAX_SLUG_LENGTH = 60` を追加します。既存の正規表現が英数字以外の
   連続を `-` にまとめ、結果を strip して小文字化したあと、その文字列を `_MAX_SLUG_LENGTH` 文字
   に切り詰め、続けて `.rstrip("-")` を呼びます。切り詰めが残したハイフンを落とすためです。
   その結果が空になる場合は `"scenario"` にフォールバックします。記号だけの名前に対して、この
   関数がすでに返しているフォールバックと同じです。この関数は入力をすでに `[0-9a-z-]` に削って
   いるため、文字数で切り詰めても、マルチバイト文字の境界を気にする必要はありません。出力の
   どの文字も1バイトだからです。`_MAX_SLUG_LENGTH = 60` は、本プロジェクトが考慮すべき
   ファイルシステムの上限を、どれも十分に下回ります。ext4 / APFS / NTFS の255バイト、暗号化
   ホームディレクトリ(eCryptfs)のおおよそ143バイトのいずれと比べても余裕があり、それでいて
   ディレクトリ一覧で一目で読める短さを保っています。今日すでに61文字以上のスラグを持つ
   シナリオでは、証跡ディレクトリの名前が変わります。シナリオ自体は、これまでどおり実行できます。
2. **他の呼び出し箇所は変更しません。** `scenario_slug()` は、`sid` を組み立てる4箇所の呼び出し
   箇所すべてが共有する、唯一の関数です(「動機」参照)。そのため、どの呼び出し箇所にも触れずに、
   上限をすべての箇所へ反映できます。
3. **ドキュメント。** [`docs/reporting.md`](../../docs/reporting.md) /
   [`docs/ja/reporting.md`](../../docs/ja/reporting.md) の、既存の `runId` / `stepId` の説明の
   そばに、短い段落を追加します。`sid` の由来(実行順インデックスと、名前由来のスラグ)と、新しい
   上限を明記します。
4. **テスト。**
   - `scenario_slug()` のユニットテストを追加します。`_MAX_SLUG_LENGTH` を超える長さの名前が、
     末尾にハイフンを残さない形で切り詰められることを確認します。
   - 報告された事例を再現するユニットテストを追加します。CSV の行が長い値や複数列の値を持つ
     データ駆動シナリオの `sid` が、上限内に収まることを確認します。
   - 切り詰め後に衝突するスラグの2行でも、既存の `{i:02d}-` インデックスプレフィックスによって、
     別々のディレクトリに収まることを確認するテストを追加します。

## 検討した代替案

| 代替案 | 採らなかった理由 |
|---|---|
| 上限を超えるスラグを持つシナリオを拒否する。run 履歴ラベルに対する [BE-0404](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer-ja.md) の「切り詰めず拒否する」規則(`MAX_LABEL_LENGTH`、`bajutsu/common/report/manifest.py:13`)にならう案 | run 履歴ラベルは、操作者が入力し、そのまま保たれることを期待するテキストです。だからこそ拒否すれば、操作者に判断を返せます。一方 `sid` のスラグは、誰も直接書いていない、派生的なファイルシステム id です。データ駆動シナリオでは行ごとの CSV の値に由来し、操作者が行単位で制御できるとは限りません。1つの長いパラメータ値のために run 全体を拒否すれば、シナリオファイル全体が止まります。読める形に切り詰めたスラグなら、それを止めずに済みます。 |
| スラグを切り詰める代わりに、固定長のダイジェストへハッシュ化する | ダイジェストは元の名前の情報を一切残しません。`scenario_slug()` がシナリオからディレクトリ名を導く理由、つまり操作者が結果を見ただけで見分けられるようにするという狙いそのものが崩れます。切り詰めであれば、名前の先頭部分という見分けの手がかりが残ります。 |
| `scenario_slug()` の手前で、`Scenario.name` 自体を切り詰める | `name` は `manifest.json` の `scenario` フィールド、`report.html`、serve の run ピッカー向けの `declared_name()` の行サフィックス照合にも使われます。そこで切り詰めれば、これらの読み手が必要とする情報が失われます。`sid` だけが、純粋にファイルシステム用の識別子です。本項目が上限を設けるのは `sid` だけである理由です。 |
| 上限をターゲットごとに設定可能にする | この上限が守るのはファイルシステムへの書き込みであり、アプリの挙動ではありません。app-agnostic という prime directive 3 の境界は、アプリごとに変わる違いを設定に置くためのものです。対象アプリが何であっても変わらないファイルシステムの定数を置く場所ではありません。 |
| 行を区別する接尾辞を残し、シナリオ名自身の先頭側を切り詰めるか、先頭と末尾の両方を残す(中間だけを落とす)案 | データ駆動シナリオでも通常のシナリオでも、操作者が一目で見分けるのはシナリオ自身の名前です。`_row_name()` が付け足す `key=value` の接尾辞が役立つのはデータ駆動の場合だけで、その場合でも `{i:02d}-` インデックスプレフィックスがすでに実行順で行を区別します。先頭を残す案では、名前ではなく接尾辞のほうを犠牲にします。先頭と末尾を両方残す案は接尾辞を取り戻せますが、切り出しが2箇所になり、テストの組み合わせが増え、スラグが一目で1つの連続した名前には読めなくなります。 |

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解(作業の単位ごとに1つ)に対応し、ログには変更内容と時期(古い順)を PR へのリンクと
> ともに記録します。

- [ ] 未着手。

## 参考

- [BE-0417 — シナリオの結果ディレクトリ名を、読み込み元のシナリオファイルにちなんだ名前にする](../BE-0417-scenario-result-folder-naming/BE-0417-scenario-result-folder-naming-ja.md)
- [BE-0031 — データ駆動シナリオ](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md)
- [BE-0404 — project 階層を org と target に畳む](../BE-0404-collapse-project-layer/BE-0404-collapse-project-layer-ja.md)
- [`bajutsu/common/orchestrator/types/_functions.py`](../../bajutsu/common/orchestrator/types/_functions.py)
- [`bajutsu/common/scenario/expand.py`](../../bajutsu/common/scenario/expand.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`bajutsu/common/report/manifest.py`](../../bajutsu/common/report/manifest.py)
- [`bajutsu/common/orchestrator/loop/_functions.py`](../../bajutsu/common/orchestrator/loop/_functions.py)
- [`docs/reporting.md`](../../docs/reporting.md)
