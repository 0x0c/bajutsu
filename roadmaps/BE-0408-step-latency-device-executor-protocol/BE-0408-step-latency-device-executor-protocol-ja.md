[English](BE-0408-step-latency-device-executor-protocol.md) · **日本語**

# BE-0408 — 端末側ステップ実行ループの土台となる、端末側ステップ実行プロトコルの追加

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-0408](BE-0408-step-latency-device-executor-protocol-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **実装済み** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-0408") |
| 実装 PR | [#1949](https://github.com/bajutsu-e2e/bajutsu/pull/1949) |
| トピック | Platform support |
| 関連 | [BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)、[BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)、[BE-0409](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md)、[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md) |
<!-- /BE-METADATA -->

## はじめに

ドライバ内部の調整を提案する [BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md) の配下に記録したパフォーマンス調査は、証拠取得まで
含めた end-to-end のステップ実行時間について Bajutsu が掲げる目標、250〜500 ミリ秒に
照らして、実際の `tap` ステップ 1 回を計測しました。
BE-0407 が提案する削減を適用しても、iOS は 1 ステップあたりおよそ 0.3〜0.6 秒、
Android はおよそ 0.6〜1.2 秒にとどまり、目標には届きません。どのステップも、
自分がポーリングしている条件のたびに、ホストと端末の間の往復を少なくとも 1 回払って
いるためです。残るギャップを埋めるには、その条件自体を端末側で評価する必要があり、
ホスト側からのポーリングでは埋まりません。この項目は、それを可能にするプロトコルと
セレクタの意味論を定義します。何を端末側に移し、何をホスト側に残すか、そして
セレクタがホストと端末の両方で同じ要素に解決されることをどう保証するかです。この
項目は、2 つのプラットフォーム別の項目が土台とする共通の設計です。XCTest ランナー内の
iOS 側実行機である [BE-0409](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md) と、常駐 instrumentation サーバー内の Android 側実行機である
[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md) の 2 つで、どちらのプラットフォーム実装もこの項目自体のスコープには含みません。

## 動機

`wait for` ステップは、セレクタが一致するまで 50 ミリ秒ごとにホストからポーリング
します。`wait until: settled` ステップも同様にポーリングします。ポーリング 1 回は
それぞれ、ホストと端末間の完全な往復です。iOS では XCTest ランナーへの新規 HTTP
リクエスト、Android では常駐 instrumentation サーバーへのリクエストです。ドライバ
内部をどれだけ調整しても、このポーリングループ自体は消えません。待っている条件を
評価するには端末の読み取りが必要であり、今日その読み取りを行っているのはホスト
だけだからです。画面に閉じた `assert`（`exists`、`label`、`value`、`count`、
`enabled`）の評価も同じ事情です。評価には、今日はホストが持っている端末の読み取りが
要ります。

この評価を端末側に移せば、ポーリングループそのものがなくなります。条件を評価する
ステップは、ポーリングの繰り返しではなく、条件を送って結果を 1 回受け取るだけの
往復になります。これは、prime directive 1（「AI は作成者であり、失敗の調査者では
あっても、判定者にはならない」）を緩めるものではありません。この原則が禁じているのは、
AI が pass/fail を決めることであって、条件の評価をホストプロセス自身が担うことでは
ないからです。セレクタを決定的に解決し、wait や `assert` を評価する端末側の実行機は、
今日ホストが同じ読み取りを行っているのとまったく同じ意味で決定的です。
アクセシビリティツリーをたどるコードは、HTTP 経由ではなく端末上で動くからといって
非決定的にはなりません。このプロトコル設計が達成すべき、後から確かめられる成果は
次のとおりです。プラットフォーム実装が 1 つ着地し、このプロトコルを実際に使った
とき、`wait for` ステップの往復回数が 50 ミリ秒ごとのポーリング 1 回につき 1 往復
から、ステップ 1 回につき 1 往復に減ることです。これは
[BE-0105](../BE-0105-xcuitest-single-snapshot-query/BE-0105-xcuitest-single-snapshot-query-ja.md)
が要素読み取りの複数往復を単一のスナップショットにまとめたのと同じ種類の成果です。

## 詳細設計

**実装の順番。** この項目は、関連する 4 項目の厳密な順番のうち 2 番目です。ドライバ内部
調整の [BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)、
この項目、iOS 実行機の [BE-0409](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md)、
Android 実行機の [BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md)
の順に進みます。**この項目への着手は、BE-0407 が完了するまで行ってはいけません。** この項目の設計は、
その項目が出荷し実測した基準値を土台にするものであり、まだ動いている基準値を土台に
プロトコルの設計を始めれば、後で変わる数値を前提に設計してしまうおそれがあるためです。
この項目が出荷した後は、BE-0409 についても同じ理由で、この項目が完了するまで
着手してはいけません。まだ動いているプロトコル設計に対して構築した実行機は、
プロトコルが変わるたびに作り直しが必要になるからです。

### 何を移し、何を移さないか

Python は、プロトコルの変更後も次の 3 つの役割をホスト側に残します。

- シナリオを、端末側の実行機が実行できるステップの列に展開すること。シナリオの
  形式とその展開規則はホスト側の所有物のままです。
- 端末が返す証拠——解決済みの要素ツリー、座標、スクリーンショット、条件が満たされた
  時刻——を受け取り、`manifest.json` と HTML レポートに書き込むこと。証拠の書き方
  自体は今日と変わりません。
- pass/fail を確定すること。端末側の評価結果は入力であり、ホストがそれを、
  ホストがすでに適用している同じ決定的な規則に照らして再確認します。最終的な
  verdict を下すのは端末ではなくホストのままです。

セレクタの解決、`wait for`、`until: gone`、`until: settled`、画面に閉じた `assert`
（`exists`、`label`、`value`、`count`、`enabled`）、そして 4 種類のアクチュエーション
（`tap`、`type`、`swipe`、`scroll`）は端末側に移します。`http`、`email`、`generate`、
`visual`、`golden`、`request` の `assert` はホスト側に残します。これらはいずれも、
検査対象の端末そのものを読み取ってはいないためです。

### 共有される契約としてのセレクタ意味論

[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py) の
`find_all` と `resolve_unique` は、今日のセレクタの意味を定める唯一の定義です。
`within`、`idMatches`、`labelMatches`、trait の派生、そして Android 側の
derived-label フォールバック
（[`drivers/adb/_functions.py`](../../bajutsu/common/drivers/adb/_functions.py)）です。端末側の
実行機は、この論理を Swift と Kotlin にそれぞれ独自に持つ必要があり、両者は
どのセレクタについても、ホスト側の解決と同じ要素に解決しなければなりません。
曖昧な一致で失敗する場合も同じ失敗の仕方をする必要があります。セレクタの一致は、
prime directive 1 が求める決定的な判定そのものです。端末側とホスト側の解決が
食い違えば、それは性能の後退ではなく決定性の後退になります。
[BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)
の driver conformance suite は、これを確かめる既存の手段です。同じセレクタの
フィクスチャ集合を、端末側のリゾルバができた時点でそれに対しても実行できるように
拡張すれば、プラットフォーム実装は同値性を主張するのではなく証明できます。

### プロトコルの段階的な導入

以下の各段階は、それぞれ独立して有用であり、1 種類の往復を取り除きます。
プラットフォーム実装は、これらを 1 度の大きなプロトコル変更としてではなく、
段階的に着地させられます。

1. **`wait for` と `until: gone` を最初に移す。** `POST /wait` リクエストに
   セレクタとタイムアウトを乗せ、端末側が内部でポーリングして、条件が満たされるか
   タイムアウトした時点で応答します。これだけで、wait ステップが今日払っている
   50 ミリ秒ごとのホスト側ポーリングがすべてなくなります。
2. **次に `until: settled` を移す。** iOS は画面遷移シグナル
   （[BE-0310](../BE-0310-ios-accessibility-screen-change-readiness/BE-0310-ios-accessibility-screen-change-readiness-ja.md)）
   をホスト経由ではなく直接受け取ります。Android は、常駐サーバーがすでに監視している
   アクセシビリティイベントのストリームから、自分自身で settle を評価します。
3. **次に、画面に閉じた `assert` の種類を移す。** 先にホストへ返した木ではなく、
   端末自身が読み取った木に対して評価します。
4. **ステップを 1 回の `POST /scenario` にまとめる。** 個々のステップ種別が端末側で
   解決できるようになれば、シナリオの一区間を、途中でホストへの往復を挟まずに
   列として送って実行できます。ここに至って、ステップ 1 回のコストは往復 1 回以下に
   なり、この項目の動機と一致します。

### この項目のスコープに含まれないもの

この項目が定義するのは、プロトコルとセレクタ意味論の契約だけです。それを実装する
2 つのランタイム——XCTest ランナープロセス内の iOS 側実行機と、常駐 instrumentation
サーバー内の Android 側実行機——を構築する作業は、それぞれ別の、より大規模な提案と
します。どちらも、イベント注入やアクセシビリティツリーへのアクセス、
スクリーンショット取得といった、自分のプラットフォームに固有の端末側設計を
必要とするためです。

## 検討した代替案

- **プロセス境界の外ではなく、アプリ内実行機（BajutsuKit や Android の on-device
  SDK の内部）を構築する。** 却下します。アプリ内の実行機は、合成タッチやキーボード
  イベントを注入できず、frame を伴うアクセシビリティツリーを読めず、アプリ
  プロセスの内側からスクリーンショットも撮れません。これらができるのは XCTest
  ランナープロセスと Android の instrumentation だけです。権限ダイアログやシステム
  キーボード、`SFSafariViewController` のコンテンツといったシステム側の画面も
  見えず、アプリのクラッシュを観測することもできません。どちらも、アプリ自身の
  外側にあるプロセス境界を必要とします。アプリ内 SDK の役割は今日のまま、
  画面遷移シグナルのような観測の補助にとどめ、アクチュエータにはしません。
  アプリ非依存の原則（prime directive 3）も、もう 1 つの独立した理由です。
  アプリ内実行機は検査対象のすべてのアプリへの組み込みを必要とし、組み込んで
  いないアプリは端末側実行を丸ごと失います。プロセス境界にある実行機であれば、
  既存の XCTest ランナーや常駐 instrumentation サーバーと同じように、検査対象の
  アプリが何であっても駆動できます。
- **プロトコルの設計を省き、各プラットフォームに独自の通信形式を委ねる。** 却下
  します。両プラットフォームのセレクタ意味論や、wait と assert の種類は、`Driver`
  プロトコルの層ですでに統一されています。この統一を端末側実行機の層で崩せば、
  この提案が避けようとしているプラットフォームごとの特別扱いを再び持ち込むことに
  なります。
- **この提案を切り出さず、BE-0409 と BE-0410 のそれぞれに
  折り込む。** 却下します。セレクタ意味論の契約と段階的な導入順序は、両
  プラットフォームに等しく適用されます。ここで 1 度だけ述べ、両プラットフォームの
  項目からそれを参照する形にすれば、同じ設計の 2 つの写しが食い違っていく事態を
  避けられます。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

**順番の状態：BE-0407 が完了しました**（[#1944](https://github.com/bajutsu-e2e/bajutsu/pull/1944)）。
これにより、この項目のブロックが解除されました（詳細設計の「実装の順番」を参照）。
下のチェックリストは、すべてチェック済みです。

- [x] 段階 1（`POST /wait`）の通信形式を書き、どちらのプラットフォーム項目も
  着手する前に、両者の間で合意する。文章だけでなく、1 本の OpenAPI 3.1 文書
  （[`protocol/device-executor.openapi.yaml`](protocol/device-executor.openapi.yaml)、
  設計の経緯は [`protocol/README.md`](protocol/README.md) に記載）として出荷しました。
  `jsonschema` による検証テスト（`tests/test_be0408_protocol_fixtures.py`）で固定して
  あります。将来 BE-0409 や BE-0410 のどちらかがこの共有スキーマから外れれば、高速
  ゲートでそのまま失敗します。
- [x] `find_all` / `resolve_unique` のセレクタ意味論を、Swift と Kotlin という独立
  した 2 つの実装が境界事例について合意できるだけの精度で、共有の設計文書に移す。
  境界事例とは、曖昧な一致や trait の派生、Android の derived-label フォールバック
  などです。[`docs/ja/selectors.md`](../../docs/ja/selectors.md) に「別言語への
  移植契約」という新しい節として出荷しました。英語版は
  [`docs/selectors.md`](../../docs/selectors.md) です。ここに挙げた境界事例すべてに
  加え、移植先が意図的に揃えてはならない Swift 側の挙動も 2 つ明記しています。
  `PositionPath` の frame の許容誤差と、トレイトの順序つき比較です。
- [x] driver conformance suite
  （[BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)）
  を、端末側のリゾルバができた時点でそれに対して実行できるフィクスチャ集合で拡張する。
  出荷先は BE-0114 の `DriverConformanceContract` の拡張ではありません。その隣に置く
  独立したフィクスチャ集合、
  [`tests/fixtures/be0408/`](../../tests/fixtures/be0408/) です。この契約は生きた
  `Driver` を要求します。端末側のリゾルバはまだ存在しません。セレクタ解決はすでに
  バックエンド非依存です。全バックエンドが単一の `resolve_unique` を共有しています。
  バックエンドごとに同じフィクスチャを回しても、得られる情報は増えません。
  `tests/test_selector_fixtures.py` が今日、全ケースを実装本体へ照合しています。
  フィクスチャ集合自体が固定したい対象からずれることはありません。
- [x] 段階 2〜4（`settled`、画面に閉じた `assert`、`POST /scenario`）の通信形式を、
  段階 1 とプラットフォーム項目の実装から得られる知見をもとに定義する。実際の定義の
  もとにしたのは、この文書自身の段階 1 の設計と、BE-0409・BE-0410 それぞれの提案
  文書です。実装からの知見ではありません。BE-0409 はこの項目が完了するまで着手でき
  ません。実装からの知見自体が、まだ存在しないためです。出荷先は段階 1 と同じ
  OpenAPI 文書です。`POST /assert` と `POST /scenario` として出荷しました。`settled`
  は `POST /wait` の 4 つ目の mode に畳み込みました。実装からの学びをこの文書へどう
  反映するかは、`protocol/README.md` の「改訂履歴」に記しています。一度書いたきりで
  固定するものではありません。
- [x] `roadmap-id` ワークフローが `main` 上で 4 項目の ID を採番したら、BE-0407、
  BE-0409、BE-0410 との間で `関連` の相互リンクを補う（BE-0407 にある同じチェック
  項目を参照）。

ログ：

- [#1949](https://github.com/bajutsu-e2e/bajutsu/pull/1949) — 5つの単位すべてを完了しました。
  言語中立なセレクタ解決フィクスチャ（`tests/fixtures/be0408/`）を出荷しました。
  `find_all` / `resolve_unique` / `parse_hierarchy` への再生テストも出荷しました。
  `docs/selectors.md` の「別言語（Swift・Kotlin）への移植契約」節も出荷しました。
  ステージ1〜4を覆う、共有 OpenAPI 3.1 文書の草案
  （`protocol/device-executor.openapi.yaml` ＋ `protocol/README.md`）も出荷しました。
  Android を iOS と同じ JSON（JavaScript Object Notation）契約に含めました。現時点では
  org.json を使い、
  BE-0410 が評価すべき `openapi-generator` の Kotlin モデル生成を推奨として記録
  しました。単一呼び出しでのキャンセルの代わりに、`pollBudgetMs` によるポーリング
  設計を採用しました。この文書自身の適合性フィクスチャとテスト
  （`tests/fixtures/be0408/protocol/`、`tests/test_be0408_protocol_fixtures.py`）
  も出荷しました。陳腐化していた `bajutsu/common/drivers/base.py` /
  `drivers/adb.py` への参照（BE-0411 でクラスごとにパッケージ化済み）を、全体に
  わたって修正しました。自己矛盾していたチェックリスト項目も修正しました。
  ゲートを走らせる前に、CI のレビュー契約に対して3ラウンドの自己レビューを
  行いました。25件の指摘を見つけて修正しました。大半は草案 OpenAPI スキーマ
  自身の構造的な厳密さに関するものでした。null を受け付けてしまうフィールド、
  強制されていなかった「いずれか1つだけ」規則、検証されていなかった束ね
  ペイロードなどです。

## 参考

[BE-0105 — XCUITest の要素取得を単一スナップショット化する](../BE-0105-xcuitest-single-snapshot-query/BE-0105-xcuitest-single-snapshot-query-ja.md)、
[BE-0114 — backend 非依存の挙動を検査する driver conformance suite](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)、
[BE-0310 — アクセシビリティの画面遷移通知による readiness 判定の精度向上](../BE-0310-ios-accessibility-screen-change-readiness/BE-0310-ios-accessibility-screen-change-readiness-ja.md)、
[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)、
[`bajutsu/common/drivers/adb/_functions.py`](../../bajutsu/common/drivers/adb/_functions.py)、
[`protocol/device-executor.openapi.yaml`](protocol/device-executor.openapi.yaml)、
[`docs/ja/selectors.md`](../../docs/ja/selectors.md)
