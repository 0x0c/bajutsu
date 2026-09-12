[English](BE-XXXX-cli-repl-inspect-actuate.md) · **日本語**

# BE-XXXX — 要素ツリーを閲覧し id で操作する対話シェル

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-cli-repl-inspect-actuate-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | オーサリング体験 |
<!-- /BE-METADATA -->

## はじめに

`bajutsu repl`は、起動中のターゲットに対して手動で操作する対話シェルです。操作者はまずアプリを
1回起動し、そのあとは1コマンドずつ入力します。`tree`は現在の画面の要素ツリーを読み取ります。
`tap <id>`はその要素の1つを操作します。操作者は毎回の結果を確かめてから、次のコマンドを決めます。
このシェルは、`record`(ゴール指向のAIオーサリング)と`crawl`(自律探索)の隣に位置し、両コマンドが
すでに使っている[`Driver`](../../docs/ja/glossary.md#driver-backend-actuator-platform)
インタフェースを通じてターゲットに到達する、3つ目の手段です。`record`や`crawl`と異なり、`repl`
は大規模言語モデル(LLM)に何も尋ねず、シナリオも書き出しません。`repl`は、`query()`と、各
[バックエンド](../../docs/ja/glossary.md#driver-backend-actuator-platform)がすでに実装している
操作メソッドを呼び出すだけの、薄いループにすぎません。そのため、XCUITest・adb・Playwrightは、
バックエンド固有のコードなしにこのシェルを手に入れます。

## 動機

[セレクタ](../../docs/ja/glossary.md#シナリオのオーサリング)がどの要素に解決されるかを知る作業は、
今日、その問い自体の重さに見合わないコストがかかります。操作者は、Xcode の Accessibility
Inspector やブラウザの開発者ツールで、ツリーを目で読むことができます。しかし、その読み取りは
バックエンド固有の手段に頼ります。しかも、シナリオのステップが実際に照合する、正規化
された`id`・`label`・`traits`フィールドは表示されません。Bajutsu内の代替手段は`record`か`crawl`
です。どちらもAI呼び出しを介してアプリを操作し、シナリオや画面マップという、それぞれ固有の成果物
向けに整形された出力を作ります。その場で1つの問いに答える手段ではありません。3つのどれも、「現在
の画面はどう見えていて、その中の1つのidを操作すると何が起きるか」という、直接的でバックエンドに
依存しない問いには答えません。

`repl`はこの問いに直接答えます。`tree`は現在の要素ツリーを表示します。`tap <id>`はその要素の1つを
操作します。もう一度`tree`を実行すれば、何が変わったかがわかります。AIの往復も、シナリオファイル
も、バックエンドごとのインスペクタを覚える手間も要りません。オーサリング中にセレクタが一致しない
事態はよくあります。idの誤記、別の要素による隠蔽、待機後にしか現れない要素などが原因です。今日、
この原因を突き止めるには、候補のシナリオステップを書いて実行し、事後にマニフェストが捕捉した
ツリーを読む必要があります。`repl`は、この一連の作業を、起動中のアプリに対して`tree`と`tap`を
打つだけに縮めます。実装後は、操作者が`bajutsu repl --target <name>`を起動して`tree`を実行し、
見えている要素のidを読みます。そのうち1つを`tap`すれば、画面の変化を手元だけで確かめられます。
この確認は数秒で終わり、runを実行してレポートを読むという一連の流れに取って代わります。

## 詳細設計

`bajutsu repl --target <name> [--udid <id>] [--backend <list>] [--erase/--no-erase] [--config
<path>]`は、アプリを起動します。起動には、`record`と`crawl`がすでに呼んでいる`launch_driver`
ヘルパー(`bajutsu/common/runner/launch.py`)をそのまま使います。そのため、ターゲットの解決、
デバイスの選択、バックエンドの選択は、この2つのコマンドと同じ挙動になります。起動すると、`repl`
は解決したバックエンドとターゲットを表示し、続けて`bajutsu>`というプロンプトを出します。

v1のコマンドは、id中心の小さな集合にとどめます。

| コマンド | 動作 |
|---|---|
| `tree [--json]` | `driver.query()`を呼び、`id`・`label`・`traits`・`value`・`frame`の表(または JSON)として表示する |
| `find <substring>` | 同じツリーのうち、`id`または`label`に`<substring>`を含む行だけに絞り込む |
| `tap <id>` | `driver.tap({"id": "<id>"})`を呼ぶ |
| `type <id> <text>` | `<id>`をタップしてフォーカスしてから、`driver.type_text("<text>")`を呼ぶ |
| `back` | `driver.back()`を呼ぶ |
| `screenshot [path]` | `driver.screenshot(path)`を呼ぶ。`path`省略時は自動で名前を付ける |
| `help` | 上記のコマンド一覧を表示する |
| `exit` / `quit` | シェルを終了する。アプリは終了させず、起動状態のまま残す |

ツリーを読む操作、あるいはツリーに対して解決するすべてのコマンドは、`run`がすでに使っている、settle
済みの読み取り経路をそのまま再利用します。read-lagバリア
([BE-0332](../../roadmaps/BE-0332-read-lag-barrier/BE-0332-read-lag-barrier-ja.md))は、`tap`の
直後に実行した`tree`が、操作前の古いスナップショットを読んでしまう事態を防ぎます。
`resolve_unique`がすでに持つ、「0件または複数件の一致は失敗させる」という契約は、`run`が出すのと
同じ`ElementNotFound`・`AmbiguousSelector`というメッセージで、そのコマンドを即座に失敗させます。
どちらの経路も、操作者の意図を推測しません(prime directive 2、決定性優先)。

`tap`と`type`は、要素を`id`だけで指定します。これは、`run`が受け付ける完全な
[セレクタ](../../docs/ja/glossary.md#シナリオのオーサリング)構文より、意図的に狭い範囲です。この
絞り込みには理由があります。v1をレビューしやすい小ささに保てる点と、シェルの実際の使い方に合って
いる点です。`tree`はすでに各要素の`label`と`traits`を表示するので、操作者はその行を読んで、id
を入力するだけで済みます。`id`を持たない要素も`tree`には表示されますが、v1の`repl`はそれを操作
できません。この隙間を埋めるのは`crawl`のvisionフォールバックの役目であり、`repl`はそれを行い
ません。visionを足すと、AI呼び出しを避けるために作ったツールに、AI呼び出しを呼び戻すことになる
からです。`tap`と`type`を残りのセレクタ構文(`label`・`labelMatches`・`index`)に広げる作業は、
シェル本体がリリースされたあとの、別スコープの自然な拡張です。

ジェスチャ(`swipe`・`scroll`・`pinch`・`rotate`)と、プラットフォーム固有の操作
(`set_picker_value`・`select_option`)は、v1の対象外とします。`tap`・`type_text`・`back`・
`screenshot`は、セレクタを確かめたり、手で1つの流れをたどったりするときに、操作者がまず使う操作
をひととおり満たします。残りの`Driver`のメソッドは、コマンド解析の形が固まったあとであれば、
素直に追加できます。すべてを一度に追加すると、この項目は、1回でレビューできる変更の範囲を
超えてしまいます。

## 検討した代替案

- **プラットフォーム固有のツール(Xcode の Accessibility Inspector、ブラウザの開発者ツール)で
  ツリーを読む。** 却下しました。各ツールはバックエンドごとに異なり、ツールを
  [アプリに依存させない](../../docs/ja/glossary.md#driver-backend-actuator-platform)という方針
  (prime directive 3)に反します。しかも、どのツールも、Bajutsuのセレクタが実際に照合する正規化
  された`id`・`label`・`traits`フィールドを表示しません。そこで読んだidが、`run`が解決するidと
  一致する保証はありません。
- **新しいコマンドの代わりに、`record`に「手動モード」フラグを足す。** 却下しました。`record`の
  ループは、スクリーンショットから操作を提案する`ClaudeAgent`を中心に組まれており、必ずシナリオ
  の書き出しで終わります。そこに人間が打つコマンドの経路を継ぎ足すと、AI駆動の経路と非AIの経路が
  1つのモジュールの中で絡み合います。`repl`は意図してシナリオを書き出さないツールなので、コマンド
  を分けたほうが両方とも読みやすく保てます。
- **最初から`tap`・`type`に完全なセレクタ(`label`・`labelMatches`・`index`)を受け付けさせる。**
  v1では見送り、id単独の指定にとどめました(詳細設計を参照)。この小さい範囲でも、この項目の動機
  となった問いにはすでに答えられます。しかも、コマンドライン上でのセレクタ構文の解析まで一度に
  決める変更より、1回でレビューできる変更として収まります。
- **標準入力やファイルからコマンド列を読む、非対話的なモード。** この項目では見送りました。対話
  シェル単体で、まずコマンドの集合を検証できます。バッチモードは、そのコマンド集合が固まった
  あとの、別スコープの拡張です。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] `bajutsu repl`コマンドの土台。`launch_driver`の再利用、`bajutsu>`プロンプトのループ、
  `help`・`exit`・`quit`。
- [ ] `tree`・`tree --json`・`find <substring>`。settle済みの読み取りとread-lagバリアの経路を
  再利用します。
- [ ] `tap <id>`・`type <id> <text>`。`run`と同じ形で`ElementNotFound`・`AmbiguousSelector`を
  表示します。
- [ ] `back`・`screenshot [path]`。
- [ ] `docs/cli.md`と`docs/ja/cli.md`のリファレンス節。

## 参考

- [`Driver`](../../docs/ja/glossary.md#driver-backend-actuator-platform)プロトコル —
  `bajutsu/common/drivers/base/driver.py`
- [`Selector`](../../docs/ja/glossary.md#シナリオのオーサリング) —
  `bajutsu/common/scenario/models/selector.py`
- `record`と`crawl` — `repl`が隣に位置する、既存の2つのTier 1オーサリング経路(`docs/cli.md`)
- [BE-0332 — read-lagバリア](../../roadmaps/BE-0332-read-lag-barrier/BE-0332-read-lag-barrier-ja.md)
