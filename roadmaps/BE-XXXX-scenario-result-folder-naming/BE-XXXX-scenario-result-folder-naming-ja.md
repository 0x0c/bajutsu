[English](BE-XXXX-scenario-result-folder-naming.md) · **日本語**

# BE-XXXX — シナリオの結果ディレクトリ名を、由来するシナリオファイルにちなませる

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-scenario-result-folder-naming-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | コードベース品質・技術的負債 |
| 関連 | [BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract-ja.md) |
<!-- /BE-METADATA -->

## はじめに

`runs/<runId>/` の中では、シナリオごとの証拠が `sid` という名前のディレクトリに格納されます。
現在の `sid` は `f"{i:02d}-{scenario_slug(s.name)}"` という形式です。実行順のインデックスと、
シナリオ内部の `name:` フィールドをスラグ化した文字列を組み合わせています
（[`bajutsu/common/runner/pipeline.py:269`](../../bajutsu/common/runner/pipeline.py)）。

本項目は、このスラグ部分の由来を変えます。シナリオの `name:` フィールドではなく、シナリオを
実際に読み込んだファイルの stem を使うようにします。stem とは `.yaml` 拡張子を除いたファイル名
です。たとえば `sid` は `00-login-succeeds-with-a-valid-password` ではなく `00-login_flow` に
なります。連番プレフィックス `{i:02d}-` 自体は変更しません。

### やらないこと

- **トップレベルの run ディレクトリは変更しません。** `runs/<runId>/` は UTC タイムスタンプです。
  辞書順が時系列順に一致するという契約
  （[BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract-ja.md)）には、`latest_run()`、
  `serve` の run 一覧と crawl 一覧、`run/notify` の直前 run 照合が依存しています。ここには触れ
  ません。run ディレクトリ自体をシナリオファイルにちなんで改名する案には、複数シナリオや複数
  ファイルを実行する run に対して一貫した答えがありません。1つの `runs/<runId>/` は、その run が
  実行したすべてのシナリオの証拠をまとめて保持する場所であり、1シナリオ専用の場所ではないから
  です。
- **重複を避けるための新しいサフィックスカウンタは導入しません。** 既存の `{i:02d}-` インデックス
  プレフィックスが、同一 run 内での `sid` の一意性をすでに保証しています。同じファイル由来の名前
  を持つシナリオが2つ生じても衝突しません。stem が同じ複数ファイルの場合や、1つのファイルの
  `scenarios:` に複数シナリオがある場合でも同じです。詳細は「詳細設計」と「検討した代替案」に
  書きます。
- **由来ファイルがわからない `Scenario` は、これまでどおりの挙動を保ちます。** ファイルローダーを
  経由せず、メモリ上で直接組み立てられたシナリオもあります。そのようなシナリオでは、
  `scenario_slug(s.name)` によるフォールバックを引き続き使います。テストのフィクスチャなどが
  該当し、本項目の影響を受けません。
- **クロスブラウザマトリクスの階層構造は変更しません。** `--browsers` が作る `<engine>/<sid>/` と
  いう階層はそのままです。変わるのは `sid` 自体の組み立て方だけです。
- **`_matrix()` に既存する、シナリオ名をキーにした衝突は扱いません。**
  `bajutsu/common/report/manifest.py:78-91` は `--browsers` のマトリクス集計をシナリオ名で
  キー化しています。同一エンジン内に同名シナリオが複数あると、片方のマトリクスセルがもう片方を
  上書きします。これは本項目とは別の既存課題です。

## 動機

現在の `sid` のスラグ部分は、シナリオを読み込んだファイルではなく、シナリオ内部の `name:`
フィールドに由来します。`name:` は自由記述であり、ファイル自体の名前と一致するとは限りません。
たとえば `login_flow.yaml` に書かれたシナリオが `name: "Login succeeds with a valid password"` を
持つとします。このとき `sid` のスラグは `00-login-succeeds-with-a-valid-password` になります。

この状態で特定のシナリオの結果を探すには、`manifest.json` を開く必要があります。その
`scenario` フィールドと、操作者が実際に念頭に置いているファイルとを照合しなければなりません。
`login_flow.yaml` から直接その証拠ディレクトリへたどり着く方法はないからです。

この不便さが本項目の動機です。複数のシナリオ結果の中から目的のシナリオの結果だけを探し出す作業
は、必要以上に手間がかかります。シナリオを書きながら、あるいは CI(Continuous Integration、継続的
インテグレーション)の失敗を追いながら、同じシナリオファイルを繰り返し実行する場面では特にそう
です。`sid` のスラグをシナリオ自身のファイルに由来させれば、操作者はすでに知っているファイル名
から証拠ディレクトリへ直接たどり着けます。`manifest.json` を経由する必要はありません。

## 詳細設計

1. **`Scenario.source_stem`（新規）**。
   [`Scenario`](../../bajutsu/common/scenario/models/scenario/scenario.py) に、読み込み時にのみ
   設定されるプライベート属性を追加します(`_source_stem: str | None = PrivateAttr(default=None)`)。
   これを公開する読み取り専用プロパティ `source_stem` も追加します。通常のフィールドではなく
   `PrivateAttr` を選ぶ理由は、これがローダーが解析後に埋める由来情報だからです。シナリオ自身の
   YAML が宣言する値では決してありません。`model_dump()` には
   一切現れてはなりません。現れると、
   `record` や `audit`、将来のシナリオ編集機能が書き出すシナリオファイルに、読み込み時だけの詳細
   がスキーマの一部として紛れ込んでしまいます。
2. **2つのローダーが、この属性を設定します。** ファイルからシナリオを読み込むデバイスフリーな
   ローダーは2つあります。どちらも、最終的な `list[Scenario]` に対して `source_stem` を設定
   します。設定するのは、返す直前です。`expand_data` による CSV（Comma Separated Values、
   カンマ区切り値）の行ごとの複製が、すでに終わったあとに設定します。データ駆動で展開された
   シナリオのどの行も、同じ由来ファイルの stem を持つことになります。
   - [`bajutsu/run/cli.py:161-200`](../../bajutsu/run/cli.py) の `_expand_file()`。`run` 自身が
     持つ、setup を前置きするローダーです。
   - [`bajutsu/common/scenario/load_expanded.py:63-89`](../../bajutsu/common/scenario/load_expanded.py)
     の `load_expanded_scenarios()`。`audit`、`trace --explain`、`coverage`、serve Web UI の
     カバレッジビューが共有します。`load_scenarios_dir()` 経由で、スイート全体を読む他の
     デバイスフリーな読み手にも及びます。
3. **`sid` 組み立てが、この属性をフォールバック付きで読みます。**
   [`bajutsu/common/runner/pipeline.py:269`](../../bajutsu/common/runner/pipeline.py) と、
   クロスブラウザマトリクスの `_cancelled_pass` にある `:1173` の2箇所を書き換えます。
   `sid = f"{i:02d}-{scenario_slug(s.name)}"` を
   `sid = f"{i:02d}-{s.source_stem or scenario_slug(s.name)}"` に変更します。ソースの stem は
   そのまま使い、追加の正規化はしません(理由は「検討した代替案」を参照)。シナリオファイル自身の
   名前は、すでにファイルシステム上安全なパスの1セグメントです。`scenario_slug()` の英数字・
   ハイフン正規化をかけると `login_flow` が `login-flow` になり、ファイル名と一致しなくなって
   しまいます。`{i:02d}-` プレフィックスは今日のままです。新たなカウンタを設けなくても、`sid` は
   同一 run 内で一意であり続けます。
4. **ドキュメント。** [`docs/reporting.md`](../../docs/reporting.md) /
   [`docs/ja/reporting.md`](../../docs/ja/reporting.md) の「出力レイアウト」節は、現状 `runId` の
   フォーマットしか説明していません(`docs/reporting.md:30-32`)。ここに `sid` の由来を明記する行を
   追加します。由来ファイルの stem を使うこと、由来ファイルがわからない場合はシナリオの `name:`
   フィールドを使うことの両方を書きます。
5. **テスト。**
   - `tests/runner/test_pipeline.py`: ファイルから読み込んだシナリオの `sid` が由来ファイルの
     stem を使うことを確認します。`source_stem` を設定しない形で直接組み立てた `Scenario` は、
     これまでどおり `scenario_slug(s.name)` による `sid` になることも確認します。
   - ユニット2の2つのローダーそれぞれについて、読み込んだファイルの stem と `source_stem` が
     一致することを確認するテストを追加します。データ駆動展開のケースも含めます。展開後のどの
     行も同じ stem を持つことを確認します。
   - `source_stem` が `Scenario.model_dump()` の出力に一切現れないことを確認するテストを追加
     します。

## 検討した代替案

| 代替案 | 採らなかった理由 |
|---|---|
| トップレベルの run ディレクトリ(`runs/<runId>/`)自体をシナリオファイルにちなんで改名する | [BE-0200](../BE-0200-run-id-contract/BE-0200-run-id-contract-ja.md) が確立した契約を壊します。辞書順が時系列順に一致するという契約です。この契約には `latest_run()`、`serve` の run 一覧・crawl 一覧、`run/notify` の直前 run 照合が依存しており、代わる仕組みが別途必要になります。加えて、複数のシナリオや複数のシナリオファイルを実行する run に対して一貫した答えがありません。1つの `runs/<runId>/` ディレクトリが保持するすべてのシナリオに、それぞれ1つの名前が必要になってしまうからです。 |
| `{i:02d}-` インデックスプレフィックスを廃止し、一意性を重複サフィックスカウンタに委ねる | プレフィックスは、追加のコストなしに run 内で `sid` をすでに一意にしています。プレフィックスを残せば、ディレクトリ一覧を見ただけで実行順もわかります。純粋な重複カウンタ(`login_flow`、`login_flow_2`、…)にすると、複数シナリオを含む1ファイルの2番目以降のシナリオを、名前だけで区別しにくくなります。由来ファイルがわからない場合のフォールバックである `scenario_slug(s.name)` には、この問題がありません。 |
| ファイルの stem を、既存の `scenario_slug()` で正規化する | `login_flow.yaml` が `login-flow` になり、ファイル名と一致しなくなります。これでは `sid` をファイルにちなんで名付ける狙いそのものが崩れます。シナリオファイルの名前は、すでにファイルシステム上安全なパスの1セグメントです。追加の正規化は不要です。 |
| `Scenario` に stem を持たせる代わりに、`list[Scenario]` と並行して由来 stem の `list[str]` を呼び出し元に引き回す | `run_all` / `run_and_report` / `run_matrix_and_report` とその呼び出し元が対象です。今日 `list[Scenario]` を持ち回るすべての呼び出し箇所に影響が及びます。`bajutsu/run/cli.py`、`bajutsu/analysis/cli/audit.py`、pipeline のテスト群が該当します。この情報は常にシナリオ自身と一緒に運ばれるものです。`Scenario` に、読み込みの際にだけ使うフィールドを1つ持たせるほうが、変更を2つのローダーと1つの読み取り箇所だけに閉じ込められます。 |

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解(作業の単位ごとに1つ)に対応し、ログには変更内容と時期(古い順)を PR へのリンクと
> ともに記録します。

- [ ] 未着手。

## 参考

- [BE-0200 — run id のフォーマットを 1 つの名前付き契約にする](../BE-0200-run-id-contract/BE-0200-run-id-contract-ja.md)
- [`bajutsu/common/scenario/models/scenario/scenario.py`](../../bajutsu/common/scenario/models/scenario/scenario.py)
- [`bajutsu/common/scenario/load_expanded.py`](../../bajutsu/common/scenario/load_expanded.py)
- [`bajutsu/run/cli.py`](../../bajutsu/run/cli.py)
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)
- [`docs/reporting.md`](../../docs/reporting.md)
