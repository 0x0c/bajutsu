[English](BE-XXXX-ios-notification-banner-swipe-dismiss.md) · **日本語**

# BE-XXXX — 実行を妨げる iOS の通知バナーをリアクティブにスワイプで消す

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-ios-notification-banner-swipe-dismiss-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | プラットフォーム対応 |
| 関連 | [BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config-ja.md)、[BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers-ja.md)、[BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling-ja.md)、[BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy-ja.md)、[BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts-ja.md) |
<!-- /BE-METADATA -->

## はじめに

Bajutsu はすでに、2種類の iOS の割り込み画面をモデルに頼らず処理できます。アプリ自身のアクセシビリ
ティツリーから見える割り込み画面は、`interrupts` フィールドの条件と復帰手順の組で処理します
（[BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers-ja.md)）。
ツリーから見えないオペレーティングシステムのアラートは、SpringBoard へのネイティブな照会とプロンプト
ごとのポリシーで処理します
（[BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling-ja.md)、
[BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy-ja.md)、
[BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts-ja.md)）。
どちらの経路も届かない第三の割り込みがあります。アプリをフォアグラウンドで実行している間にプッシュ
通知やローカル通知が届くと、iOS は実行中の画面の上に**通知バナー**を表示します。本提案は、この通知バナーの
存在を検出するネイティブな照会と、スワイプで消すアクションを追加し、BE-0315 がシステムアラート向けに
確立したリアクティブガードの形に組み込みます。これにより、ステップのタップはシナリオが宣言していない
バナーではなく、シナリオが名指しした要素に届きます。

## 動機

通知バナーは実行中のどの時点でも現れ得て、ステップがこれからタップしようとしている要素の真上に
重なることがあります。実際の実行では、通知バナーにシナリオが確認を置ける決まったきっかけはありません。
プッシュ通知の到着はサーバー側に依存し、アプリ自身がスケジュールするローカル通知であっても、どの
ステップの直後かではなく実時刻を基準に届きます。そのためタップ先がたまたま通知バナーの枠と重なっていると、
ステップは意図した要素ではなく通知バナーをタップしてしまうか、重なりが生じた瞬間に XCUITest 自身の
ヒットテストが選んだ要素に対して解決されてしまいます。実行のレポートには通知バナーが現れたという記録が
一切残らないため、この不具合は単なる不安定な失敗として読めてしまいます。

このギャップは偶然ではなく、構造に由来します。通知バナーを描画しているのは、テスト対象のアプリの外側の
プロセスです。これは BE-0315 の動機が SpringBoard のアラートについて測定したのと同じ、プロセスの境界
です。そのため `interrupts` フィールドの条件、つまりアプリ自身のツリーに対してのみ評価される条件には、
判定する相手がありません。さらに、通知バナーにはボタンがありません。BE-0315 がシステムアラート向けに
組んだ決定論的な dismiss は、label でボタンを解決して押しますが、実機で通知バナーを消す操作はタップ
ではなく上方向へのスワイプです。タップしてしまうと通知の送信元アプリが開き、実行中のシナリオから
画面ごと離れてしまいます。本提案に必要なジェスチャーは Bajutsu にすでにあります。`swipe`
（[`docs/scenarios.md`](../../docs/scenarios.md) に方向指定形式と座標指定形式の両方が記載済み）です。
ただし、通知バナーがどこにあるか、いつそれを使うべきかを知っている既存の仕組みはありません。

本提案が実現したかどうかは、後から読む人が次の方法で確かめられます。タップの直前に `push` ステップで
通知バナーを発生させ、通知バナーの実測された枠がそのタップ先とあらかじめ重なるように組み立てた
シナリオを実行します。本提案の前は、そのタップの成否は当てになりません。XCUITest が解決する瞬間に
2つの枠がどう重なっているか次第だからです。本提案の後は、タップが発火する前にガードが通知バナーを消し、
タップはタップ先に届きます。

## 詳細設計

### Unit 1 — 実機で通知バナーのアクセシビリティ上の見え方を測定する

driver のメソッドを追加する前に、起動済みの Simulator 上で、フォアグラウンドの通知バナーが実際に
XCUITest からどう見えるかを測定します。対象は、既存のシステムアラートの作業がすでにカバーしている
iOS バージョン（18.6、26.3、26.4、26.5）です。次の4点が、以降のすべての Unit の設計を左右します。
1つ目は、通知バナーをどのプロセスの要素ツリーが公開しているか（システムアラートと同じく SpringBoard
なのか、別のプロセスなのか）です。2つ目は、通知バナーがどのような枠や識別子を提供するか、そもそも
提供するかです。3つ目は、タップ先が通知バナーの枠の下にある通常の `tap`/`type` ステップが、BE-0399
がシステムアラートについて測定したのと同じ XCUITest 自身の interruption monitor の扱いをすでに
受けているか、それともヒットテストが割り込みを一切発生させずに重なりを静かに解決してしまうかです。
4つ目は、3つ目で monitor が呼ばれると分かった場合に限り、その handler の内側で発行したスワイプを
handler が返る前に XCUITest が「解消した」と確認できるかどうかです。BE-0399 自身の動機は、monitor が
解消を確認できないまま割り込みを引き受けるとどうなるかを測定済みです。XCUITest は以降のあらゆる操作の
たびにその monitor を再度呼び出し、測定したすべての試行でランナーが落ちるまでループしました。
この Unit はコードを生み出しません。この測定が、Unit 4 に残っている設計上の疑問に決着をつけます。

### Unit 2 — 決定論的な存在照会

通知バナーが現在表示されているかどうか、表示されている場合は Unit 3 のスワイプに必要な画面上の枠を
返す driver のメソッドを追加します。これは BE-0315 の `system_alert_labels()` と同じ形です。事実を
報告するだけで何も判定しない、薄い非ブロッキングの読み取りです。このメソッドは、BE-0315 の照会を
`HANDLE_SYSTEM_ALERT` が制限しているのと同じように、専用の capability token の背後に置きます。
最初に対応するのは iOS の XCUITest バックエンドだけで、capability を持たないバックエンドはエラー
ではなく不在を返します。通知バナーが同時に2つ以上表示されている場合は、`resolve_unique` /
`AmbiguousSelector` の規約（prime directive 2）に従って照会をちょうど1件に絞り込みます。複数件が
マッチしたときは、たまたま先に返ったバナーをスワイプするのではなく、明確に失敗します。

### Unit 3 — 決定論的なスワイプによる dismiss アクション

通知バナーをスワイプで消す driver のアクションを追加します。固定の画面座標ではなく Unit 2 が返す枠を
基準にするため、デバイスのサイズが変わってもジェスチャーが成立します。方向は、実機で人が通知バナーを
消す操作と同じ上方向、画面の上端へ向かうスワイプです。このアクションは、`swipe` の既存の driver 実装が
すでに持つ座標計算をそのまま再利用し、新しいジェスチャーのプリミティブは追加しません。Unit 2 がすでに
存在照会をバナー1件以下に絞り込んでいるため、このアクションは常に受け取った1つの枠だけを消し、
複数のバナーから選ぶことはありません。

### Unit 4 — リアクティブな組み込み

config とシナリオの双方で設定できるスイッチが、Unit 2 の存在照会を BE-0315 が SpringBoard の照会に
対してすでに確立した上限付き間隔でポーリングするガードを有効にし、通知バナーを見つけた瞬間に Unit 3
のアクションで消します。ガードがどちらの経路を取るかは、Unit 1 の4つ目の測定が決めます。ただし、
この2つの経路は同じ重みを持ちません。無条件で選んでよいのは一方だけです。handler の内側で発行した
スワイプを handler が
返る前に XCUITest が解消済みと確認できると Unit 1 が確かめた場合に限り、ガードはその monitor 経由で
応答します。これは BE-0399 の monitor が割り込んでくるアラートに応答する形と同じです。それ以外の
すべての場合、つまり Unit 1 がその確認を取れなかった場合も含め、ガードは代わりに各アクションステップ
自身の操作の直前にポーリングして消す方式を使います。この代替方式には、認めた上での制約が残ります。
ポーリングとタップ自体の発行のあいだの隙間で通知バナーが届けば、タップは依然として妨げられ得ます。
そのため本項目は「タップが必ず届く」とは主張せず、「今よりずっと確実に届く」とだけ主張します。この
残存する隙間を埋めることは、本項目を止めずにフォローアップへ切り出します。どちらの経路でも、その
dismiss は割り込まれたステップの `AlertEvent` に記録します。これは BE-0399 が drain した label を
そこに畳み込むのと同じ扱いで、通知バナーの dismiss を黙ったままにしません。ガードは、Unit 2 と
Unit 3 が driver 呼び出しをその背後に置く capability を backend が公開しているときにだけ有効になります。
持たない backend ではスイッチは何もせず、今の挙動のまま変わりません。このスイッチは、
`systemAlertHandling` がすでに確立している config からシナリオへ、さらにフラグで上書きできる優先順位
（[BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config-ja.md)）に従います。

### Unit 5 — showcase の fixture と実機検証

タップ対象の直前に `push` ステップ（[`docs/scenarios.md`](../../docs/scenarios.md)、`simctl push`）
で通知バナーを発生させ、通知バナーの到着をタイミング頼みではなくステップの境界に固定した showcase
シナリオを追加し、タップがそのタップ先に届くことをアサートします。実機の通知バナーに対するネイティブ
なスワイプは、Simulator を使わないゲートでは証明できません。driver のメソッドを実装する Unit は、
このシナリオを起動済みの Simulator 上で実行しなければなりません。

### Unit 6 — ドキュメント

[`docs/scenarios.md`](../../docs/scenarios.md) とその `docs/ja/` 対訳に、新しいスイッチを `interrupts`
や `systemAlertHandling` と並べて記載し、どの仕組みを使うべきかという BE-0314 が
すでに持っている比較を拡張します。

### Unit 7 — テスト

新しいスイッチのスキーマの parse/validate、ポーリングのたびに存在照会の返り値が入れ替わる fake driver、
ステップ自身の操作より前にガードが通知バナーを消すこと、その dismiss がステップの `AlertEvent` に
届くこと、capability を持たない backend では何も変わらないこと、config からシナリオへの優先順位、
そして Unit 1 で interruption monitor 経由の経路が必要だと分かった場合は、BE-0399 のテストスイートが
アラートの monitor をカバーしているのと同じやり方でその経路をカバーします。

### 維持される prime directive

- **AI は判定しません。** 存在照会もスワイプによる dismiss アクションも、どちらも決定論的な driver
  呼び出しであり、本項目は新しい AI の経路を追加しません。
- **決定論が最優先です。** 固定の sleep はありません。ガードは上限付き間隔でポーリングし、通知バナー
  自身の自動消滅を待つのではなく、実測した枠を基準に消します。
- **アプリに依存しません。** スイッチとガードは汎用的な runner の仕組みであり、アプリ固有のコードは
  追加しません。

## 検討した代替案

- **通知バナーを `interrupts` 経由で処理する。** BE-0315 の動機がシステムアラートについてすでに
  示した前提と同じ理由で却下します。通知バナーを描画しているのはテスト対象のアプリの外側のプロセス
  であり、アプリ自身のツリーに対してのみ評価される `interrupts` の条件には、判定する相手がありません。
- **スワイプではなくタップで通知バナーを消す。** 却下します。実機の通知バナーをタップすると通知の
  送信元アプリが開いてしまい、テスト対象のシナリオから実行が離れてしまいます。これは通知バナーを
  消すことの正反対です。副作用なくバナーを取り除けるのはスワイプだけです。
- **ネイティブな照会で解決できない場合に備え、かつてシステムアラートが持っていた vision guard の
  ような AI vision の fallback を追加する。** prime directive 1 のもとで却下します。BE-0402 は同じ
  理由で `run` のシステムアラート経路から同等の fallback をすでに取り除いています。通知バナーの
  存在と枠は、まさにネイティブな照会が答えるべき事実であり、モデルに判定させる余地はありません。
- **スワイプで消す代わりに、通知バナーが自身のタイムアウトで自動的に消えるのを待つ。** prime
  directive 2（固定 sleep の禁止）のもとで却下します。しかも、自動的に消えるまでの間こそが、通知
  バナーがタップを妨げる時間帯そのものです。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] Unit 1 — 対象の iOS バージョンすべてで、起動済みの Simulator 上で通知バナーのアクセシビリ
      ティ上の見え方を測定する。
- [ ] Unit 2 — 決定論的な存在照会（通知バナーの枠、または不在を返す `Driver` のメソッド）。
- [ ] Unit 3 — 実測した枠を基準にしたスワイプによる決定論的な dismiss アクション。
- [ ] Unit 4 — 既存の優先順位に従う、config/シナリオのスイッチによるリアクティブガードの組み込み。
- [ ] Unit 5 — showcase の fixture と実機検証。
- [ ] Unit 6 — ドキュメント（`docs/scenarios.md` と ja 対訳）。
- [ ] Unit 7 — テスト。
- [ ] フォローアップ — Unit 1 の測定によって Unit 4 の経路が定まり次第、poll-and-clear 方式に残る
      レースの隙間を埋める。

## 参考

- [BE-0314](../BE-0314-scenario-interrupt-handlers/BE-0314-scenario-interrupt-handlers-ja.md) —
  `interrupts` フィールドと、その in-tree の条件がシステム側のオーバーレイに届かない理由。
- [BE-0315](../BE-0315-ios-native-system-alert-handling/BE-0315-ios-native-system-alert-handling-ja.md) —
  本提案が、アラートではなく通知バナー向けに再利用する、ネイティブな存在照会とリアクティブガードの形。
- [BE-0399](../BE-0399-ios-system-alert-interruption-policy/BE-0399-ios-system-alert-interruption-policy-ja.md) —
  interruption monitor とその順序。Unit 4 がこれを再利用できるかどうかは、Unit 1 が通知バナーに
  ついて測定して初めて決まります。
- [BE-0406](../BE-0406-system-alert-declared-prompts/BE-0406-system-alert-declared-prompts-ja.md) —
  プロンプトごとの宣言。通知バナーには宣言すべき別々のプロンプトがないため、本項目の単一の config
  スイッチはこれより単純です。
- [BE-0177](../BE-0177-run-behavior-target-config/BE-0177-run-behavior-target-config-ja.md) —
  Unit 4 のスイッチが従う、config からシナリオへ、フラグで上書きできる優先順位。
- [`docs/scenarios.md`](../../docs/scenarios.md) — Unit 3 が座標計算を再利用する既存の `swipe`
  ステップと、Unit 5 の fixture が通知バナーを決定論的に発生させるために使う `push` ステップ。
- Apple、[`XCTestCase.addUIInterruptionMonitor(withDescription:handler:)`](https://developer.apple.com/documentation/xctest/xctestcase/adduiinterruptionmonitor(withdescription:handler:)) —
  Unit 4 の interruption 経路が再利用することになる monitor。BE-0314 と BE-0399 も同じ先行事例として
  引用しています。
