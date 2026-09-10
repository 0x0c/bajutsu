[English](BE-XXXX-driver-call-trace-per-scenario.md) · **日本語**

# BE-XXXX — Python とドライバ間の呼び出しを、シナリオ単位で恒久的にトレースする

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-driver-call-trace-per-scenario-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | Driver & backend architecture |
| 関連 | [BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md) |
<!-- /BE-METADATA -->

## はじめに

[BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)
は、iOS シミュレータと Android エミュレータで `tap` ステップが遅い理由を調べました。この調査には
[`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py)
という単独のラッパースクリプトを使いました。このスクリプトは `bajutsu run` を起動する前に、
ドライバの各クラス、通信用の関数、`subprocess.run` へモンキーパッチを当てます。計測結果は、
実行1回につき1つの JavaScript Object Notation（JSON）ファイルへまとめて書き出します。この方法で
BE-0407 の調査自体は達成できました。しかし `bajutsu run` の代わりに、誰かが思い出して実行しなければ
ならないスクリプトのままです。出力もシナリオ単位に分かれておらず、複数シナリオを1回で実行すると
すべての呼び出しが1つの平坦なリストに混ざります。

この項目は、同じ種類の計測を `bajutsu run` の恒久的なオプション機能にするものです。
`--trace-driver` を渡すと、実行のたびに各シナリオの `driver_trace.json` が、そのシナリオの
他の証拠と並んで書き出されます。記録するのは、Python とドライバ間のすべての呼び出しです。
各レコードには、呼び出されたドライバのメソッド名と、そのメソッド1回がホストと端末の間で
何往復したかを記録します。Android に限っては、その往復のうちどれが subprocess 起動へ
フォールバックしたかも記録します。さらに、各呼び出しの開始時刻と所要時間を、発生した
ステップに紐づけて記録します。`trace_run.py` と異なり、モンキーパッチは一切使いません。
合成するのは、orchestrator がすでに持っている依存性注入の差し込み口です。その大半は
テスト向けに追加されたか、BE-0407 自身のドレイン追跡用ラッパーとして用意されていたものです。
それに加えて、ステップとの対応づけのためにこの項目自身が持ち込む、小さなスレッドローカルな
トレース文脈が1つだけあります。

### やらないこと

- **Web バックエンド（Playwright）は対象外とします。** この項目の動機が指す
  「シミュレータ・エミュレータ」には当たりません。ブラウザとの通信は、Playwright 自身の
  Python バインディング内部で完結しています。XCUITest や adb の往復と違い、bajutsu の
  ドライバ側が起点になるものではないからです。
- **スクリーンショットや要素ツリーの証拠書き込み（`FileSink.capture`）の計測は対象外とします。**
  証拠取得が内部で行うドライバ呼び出し（`screenshot()`、`query()`）自体は、すでに `driver`
  カテゴリで見えています。証拠書き込みが追加で持ち込むのは、ファイルの Input/Output（I/O）と
  マスク処理のオーバーヘッドです。これは、この項目の動機である「シミュレータ・エミュレータを
  操作する処理」の外側にあります。
- **シナリオの合否には一切影響しません。** トレースファイルは、現在の `--score` や `--zip`
  と同じく診断用の証拠です。プライム・ディレクティブ 1 は、あらゆる AI と診断機構を判定経路から
  締め出しており、この項目もそれに従います。
- **`transport` レコードの `response` フィールドは、小さな構造化された結果だけです。レスポンス
  本文まるごとは記録しません。** GET（読み取り）は何も持ちません。POST が持つのは、iOSの
  `_Reply.status` か、Androidの `ActOutcome.acted`／`.published_mark` だけです。`/elements` や
  `/act` の応答が持ちうる要素ツリーはここに含めません。その内容はランの証拠（`elements.json`）としてすでに記録済みです。
  `driver_trace.json` にも複製すると、診断用の成果物自体がラン本体と同じか、それ以上の大きさになりかねません。

## 動機

BE-0407 はステップの遅延を大きく削減しました。ただしその数値（iOS の `tap` ステップで
1 回あたり 0.3〜0.6 秒、Android で 0.6〜1.2 秒）自体が、目標の 250〜500 ミリ秒には
まだ届いていません。残りを埋めるには、端末側のステップ実行機というより大きな変更が必要です。
これは別項目（[BE-0408](../BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol-ja.md)〜[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md)）として追跡しています。
この後続作業に着手する人、あるいは実行時間が悪化した別のシナリオを
調査する人は、BE-0407 の調査が使ったのと同じ、呼び出し単位の内訳を必要とします。しかし
現状では、それはロードマップ項目の `misc/` ディレクトリの奥から `trace_run.py` を
見つけ出す作業です。その起動方法が `bajutsu` 自身の引数の前にラッパーを1つ挟んだものだと
思い出し、1つにまとまった JSON ファイルを手作業でシナリオごとに分け直す作業でもあります。
そのどれもが、恒久的なコマンドラインインタフェース（CLI）フラグ1つで消える手間です。

これを単発のスクリプトのままにしておくコストは、想像上のものではありません。BE-0407 の
「はじめに」自身が述べているとおり、ドライバ内部の遅延に関する調査は BE-0407 で
終わっていません。CI で誰かが気づいた実行時間の悪化も、新しいバックエンドの最初の性能検証も、
この機能なしでは毎回ゼロから始まります。シナリオ単位に区切り、`run` がすでに
書き出しているランディレクトリに統合する形で、一度だけ作っておきます。そうすれば、
次の調査は問題を再現できるスイートに対して `bajutsu run --trace-driver` を実行するだけで
済みます。別のスクリプトを用意する必要も、どの呼び出しがどのシナリオに属するかを手作業で
対応づける必要もありません。

## 詳細設計

### 計測する3つのカテゴリ

1ステップの中でホストと端末の往復回数を実際に左右しているものに合わせて、
カテゴリを3つに分けます。

- **`driver`**：`Driver` プロトコルの各メソッド呼び出し（`tap`、`query`、`screenshot`、`wait_for` など）1回につき1レコードです。加えて、`trace_run.py` も計測していた
  `drain_interruptions` と `settled_query` の2つも対象とします。この2つは対応する能力プロトコル
  （後述）を実装しているドライバにだけ存在し、orchestrator がそのドライバへ直接呼び出します。
- **`transport`**：1回のドライバメソッド呼び出しの**内部**で起きるホストと端末の往復
  1回につき1レコードです。`/zorder` も取得する `query()` 呼び出しは、1つの `driver`
  レコードの下に `transport` レコードを2つ持ちます。きれいに解決する `tap()` 呼び出しなら
  1つだけです。POST の往復（読み取りではなく操作）のレコードには、端末がもともと返している
  小さな構造化された結果も追加で持たせます。iOSなら `_Reply.status`
  （`bajutsu/common/drivers/xcuitest/_reply.py:22`、たとえば `"ok"`／`"stale"`）、Androidなら
  `ActOutcome.acted`／`.published_mark`（`bajutsu/common/drivers/adb/act_outcome.py:25-26`）です。
  レスポンス本文まるごと（`_Reply.raw` や、`act()` の応答が `want_tree` 次第で持ちうる要素ツリー）は含めません。
  トレースをランの証拠取得の複製にせず、呼び出し単位の小さなログのまま保つためです。
- **`subprocess`**：Android 限定です。常駐サーバー経由に乗らない
  [`adb_driver.py:457`](../../bajutsu/common/drivers/adb/adb_driver.py) の `uiautomator dump`
  フォールバックや、同じ経路を通る `id_u`／`getevent`／`wm size` の `adb shell` プローブ
  （`adb_driver.py:1148,1159,1190`）を指します。iOS の `simctl` と `xcodebuild` のプロセス起動は、
  デバイスのリース時、つまりどのシナリオのステップも始まる前に一度きり発生するだけです。
  ステップ単位の手がかりを持たないため、計測対象にしません。

各レコードは `{category, step, name, started_at, elapsed_s}` を持ちます。`step` は
その呼び出しが発生したステップの番号と種別（`trace_run.py` と同じ形式の
`f"{i:02d}:{種別}"`）です。`started_at` は壁時計の Unix エポック秒で、`device.log` や
`manifest.json` 内のステップ自身の `started_at` と突き合わせられます。`elapsed_s` は
その呼び出し自体の所要時間です。POST の往復を表す `transport` レコードだけは、もう1つ
`response` フィールドを持ちます。これが前述の小さな構造化結果で、GET（読み取り）のレコードは
これを持ちません。

### モンキーパッチではなく合成で実現する

`trace_run.py` がモンキーパッチに頼っているのは、`bajutsu` 自身のソースを編集できない
外部スクリプトだからです。この項目は編集できます。そして orchestrator は、同種の計測を
恒久機能とするために必要な差し込み口をすでに持っています。どれも新設するものではなく、
テスト向け、あるいは BE-0407 自身が、すでに追加していたものです。

1. **`TracingDriver`（新規）**：`base.Driver` を満たす委譲プロキシです。ただし実装するのは
   `__getattr__` **だけ**で、プロトコルのメソッドを自前で1つも宣言しません。属性を読むたびに、
   まず素の `getattr` で包んでいるドライバが実際にその属性を持っているかを確認します（持たない
   ときは、ラップしていないドライバと同じように例外が上がります）。計測対象の一覧に載っている
   名前であれば、素の属性の代わりにタイミング計測付きのラッパーを返します。それ以外は透過的に
   渡すだけです。この設計は `tap`／`query`／`screenshot` だけの問題ではありません。
   `drain_interruptions` と `settled_query` は「ドライバ固有の余分なメソッド」ではなく、
   `@runtime_checkable` な能力プロトコル `base.InterruptionPolicyTarget` と `base.SettledReadProvider`（[`bajutsu/common/drivers/base/`](../../bajutsu/common/drivers/base/)）に属していて、
   orchestrator は `hasattr` ではなく `isinstance` でこれを判定しています
   （`gestures.py:212`、`waits/_functions.py:273`、`loop/_step_runner.py:166`）。もしプロキシが
   この2つを実メソッドとして宣言してしまうと、包んでいる相手が誰であろうと `isinstance` が
   常に真を返してしまいます。`settled_query` を持たない `FakeDriver` や、どちらも持たない
   `PlaywrightDriver` を包んだ場合も同様で、能力があると誤判定された分岐へ進んだ先で、
   プロキシ自身の `__getattr__` が失敗します。`TracingDriver` が何も自前で宣言しないからこそ、
   どの能力プロトコルに対する `isinstance` も、包んでいるドライバの本当の能力をそのまま反映します。
2. **注入するのはパラメータではなく共有トレース文脈**：ステップが実際に操作するドライバは、
   `--trace-driver` の値が見える場所（作業単位5）から何段も奥で構築されます。代替案として
   `backends.make_driver` に引数を1つ足し、`launch_driver`・`RunEnvironment`・具象環境クラス
   それぞれのコンストラクタへ順に通す方法もありますが、診断機能のためだけに各バックエンドの
   ライフサイクルクラスすべてへ手を入れることになります。代わりに、`make_driver` と
   `AdbDriver` の subprocess 経路（作業単位4）は、作業単位6がステップとの対応づけのために
   もともと必要とするのと同じスレッドローカルなトレース文脈を読みます。これは
   `--trace-driver` のとき `_ScenarioRunner.run_one` が一度だけセットするスレッドローカルです。
   アンビエントな状態をスレッドローカルから読む方式は、`RunEnvironment` の各サブクラスへ
   コンストラクタ引数を足すよりも変更範囲が小さくて済みます。代わりに、差し込み口が明示的な
   引数ではなく暗黙のものになります（詳細は「検討した代替案」）。
3. **iOSの `transport`**：
   [`XcuitestDriver.__init__`](../../bajutsu/common/drivers/xcuitest/xcuitest_driver.py) は、
   BE-0407 作業単位 6 のドレイン追跡を組み込むために、すでに `self._transport` を
   委譲クロージャ `_tracking_transport` で1段ラップしています。この項目では、
   同じ場所にもう1段、計測用のラップを重ねるだけで済みます。追加するのは新しい任意引数
   （たとえば `on_transport_call: Callable[[str, float, float, str | None], None] | None`。
   最後の引数はPOSTなら `_Reply.status`、GETなら `None`）1つで、`backends.make_driver` の
   `xcuitest` 分岐が、作業単位2のトレース文脈がトレース有効を示しているときにこれを渡します。
   `_raw_http_transport` にも他のモジュールにも一切手を入れません。
4. **Androidの `transport` と `subprocess` は、同じ差し込み口を通る**：
   [`backends.make_driver`](../../bajutsu/common/backends.py) の adb 分岐は、
   `fetch_hierarchy`、`fetch_clock`、`act` という呼び出し可能オブジェクトを呼び出し元から
   受け取り、そのまま `AdbDriver(...)` へ渡しているだけです。トレースが有効なときは、
   `AdbDriver(...)` を構築する前に、`make_driver` の内部でこの3つを計測用にラップします
   （`transport`）。`act` のラップは、戻り値の `ActOutcome`（`.acted`、`.published_mark`）も
   レコードへ読み込みます。Android側で唯一POSTにあたる往復だからです。同じ分岐は
   `subprocess` も同じ考え方で扱います。`AdbDriver.__init__` はすでに
   `run: RunFn = adb.real_run`（[`adb_driver.py:125`](../../bajutsu/common/drivers/adb/adb_driver.py)）を受け取っていて、
   `AdbDriver` が発行する adb 向けの subprocess 呼び出しはすべて `self._run`
   を経由します。`uiautomator dump` フォールバック（`:457`）、`id_u`／`getevent`／`wm size` の
   各プローブ（`:1148,1159,1190`）、そして `adb.Env(self.serial, run=self._run)`（`:1400,1453`）です。
   `make_driver` は、同じ条件のもとで計測用にラップした `adb.real_run` を `run=` として
   渡します。したがって、どちらのカテゴリにも `subprocess` へのモンキーパッチはどのモジュールにも
   要りません。この経路が唯一届かない呼び出しが `AdbDriver._run_text`（`:1381`、`typeText` の
   経路。タイプした秘密情報が adb プロセスの引数列に載らないよう、あえて `self._run` の外に
   置かれています）で、これはもともとのコメントが「テストがパッチできるようクラスレベルの属性経由に
   してある」と述べているとおり、すでに差し替え可能です。このモジュールも、同じ条件のもとで
   同じ属性を差し替えます。
5. **`driver` カテゴリのラップは、実際にシナリオのドライバを組み立てる場所で行う**：
   シナリオのドライバは `device_pool` の注入可能な `make_driver` 引数
   （`Callable[..., base.Driver] = _make_driver`）からは来ません。この引数が読まれるのは
   [`pool.py:387`](../../bajutsu/common/runner/pool.py) の1箇所だけで、これは自身のアクチュエータが
   ドライバ経由でネットワークを観測しないランがフォールバックする、読み取り専用のネットワーク
   証拠プロバイダ（BE-0020）のためのものです。シナリオのステップが実際に操作するドライバを
   組み立てることは一度もありません。そのドライバは
   [`pool.py:408`](../../bajutsu/common/runner/pool.py) の `launch_driver(...)` から来ます。
   `launch_driver` は `RunEnvironment.start(...)` を呼び、各環境がそこで自ら `backends.make_driver`
   を呼び出します
   （[`xcuitest_environment.py:772`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py)、
   [`android_environment.py:166`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)）。
   `device_pool` の `lease()` クロージャは、`launch_driver(...)` が返す値をその場で
   `TracingDriver` に包んでから `Lease.driver` へ格納します。これは `lease_env` のテアダウンが
   後で受け取るのと同じオブジェクトです。
   - このテアダウン呼び出し（`lease_env.end_lease`／`teardown`）は、一見すると選択を迫るように
     見えます。テアダウン側に渡す値だけ生のドライバのままにするか、`TracingDriver` の透過性が
     テアダウンにも及ぶと確認するかです。しかし実際にはその必要がありません。どの環境の
     `teardown` も、`driver` 引数はインタフェースの形を揃えるためだけに受け取っていて、中身は
     一切読んでいません。いずれも `# noqa: ARG002  # Environment shape` という注記付きです
     （[`environments/ios.py:88`](../../bajutsu/common/platform_lifecycle/environments/ios.py)、
     [`android_environment.py:363`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)）。
     テアダウンが読むのは環境自身が持つ状態（`self._resident`、`self._serial`、ランナーのプロセス
     など）だけです。したがって `Lease.driver` は一律に `TracingDriver` でラップしてよく、
     テアダウン用とステップループ用とで値を使い分ける必要はありません。
6. **シナリオとステップの境界**：こちらは自分たちで直接編集するファイルなので、
   モンキーパッチではなく明示的な呼び出しを2箇所加えます。
   - [`pipeline.py`](../../bajutsu/common/runner/pipeline.py) の `_ScenarioRunner.run_one`
     は、`--trace-driver` が有効なときだけ、作業単位2で導入したスレッドローカルなトレース文脈を
     そのシナリオの `sid` を鍵にして開きます。無効な実行では一度もセットしないので、
     `make_driver` や `AdbDriver` の `run=` 側が読む「トレースなし」の判定は追加コストなしで
     終わります。`finally` では、蓄積したレコードを `self._artifacts()`
     （[`RunArtifactWriter.write_json`](../../bajutsu/common/evidence/sink.py)）経由で
     `f"{sid}/driver_trace.json"` へ書き出します。これはラン全体で唯一の書き込み境界
     （BE-0331）です。現状どのレコードもシナリオが書いた文字列を含んでいませんが、
     秘密情報のマスク処理がこの経路に乗ることで無料で効きます。
   - [`_step_runner.py`](../../bajutsu/common/orchestrator/loop/_step_runner.py) の
     `_StepRunner._run_one` は、現在のステップの鍵を同じスレッドローカルな文脈へ
     出し入れします。
   - スレッドローカルで足りる理由は、`_ScenarioRunner.run_one` が
     `ThreadPoolExecutor`（`pipeline.py` の `run_all`）の1ワーカースレッド上で、
     1シナリオを最初から最後まで実行するからです。あるスレッドが同時に2つのシナリオの
     途中にいることはありません。「このスレッドで今アクティブなトレース文脈」は、
     常に「このシナリオの、今この瞬間」を指します。しかもこれは、そのシナリオのリースのために
     `launch_driver`／`make_driver` が動くのと同じスレッドなので、ドライバ構築の最中に
     作業単位2がこの文脈を読んでも、正しいシナリオの文脈を読むことになります。
7. **CLI フラグ**：`bajutsu run --trace-driver`（`bajutsu/run/cli.py`）を追加し、
   `_RunPlan` を経由して `_ScenarioRunner`（作業単位6の開始・書き出しを制御するフィールド）まで
   渡します。既存の `--score` や `--zip` と同じ「診断専用で、デフォルトは無効」という
   パターンを踏襲します。

### 出力形式

`runs/<run_id>/<sid>/driver_trace.json`:

```json
{
  "scenario": "<シナリオ名>",
  "steps": [{"step": "00:tap", "wall_s": 1.02}],
  "records": [
    {"category": "driver", "step": "00:tap", "name": "tap", "started_at": 1234567890.1, "elapsed_s": 0.69},
    {"category": "transport", "step": "00:tap", "name": "POST /tap", "started_at": 1234567890.1, "elapsed_s": 0.62, "response": {"status": "ok"}}
  ]
}
```

`--trace-driver` を渡さないシナリオ実行では、このファイルを書き出しません。フラグが
無効な経路のコストは、フラグの判定自体を除けば発生しません。

## 検討した代替案

| 代替案 | 採らなかった理由 |
|---|---|
| `trace_run.py` 自身のモンキーパッチ方式を、そのまま `bajutsu` 内部の恒久モジュールへ昇格させる | `_raw_http_transport` や `adb_resident.ResidentServer.start` といった非公開の内部実装に踏み込む方式です。今日これらは `trace_run.py` 以外の誰にも依存されていないからこそ自由に形を変えられますが、これを恒久的な契約にすると、使い捨てのスクリプトが持っていた脆さを、保守し続けなければならない脆さへ変えてしまいます |
| `XcuitestDriver` と `AdbDriver` の各メソッド本体に、直接タイミング計測コードを書き込む | 実際のアクチュエーション処理を持つ2つのファイルの、約20個のメソッドすべてに手を入れることになります。診断機能のためだけに、両バックエンドがすでに経由して構築している唯一の差し込み口（`make_driver`）で合成する場合よりも、はるかに大きく、リスクの高い差分になります |
| `backends.make_driver` に明示的な `trace` 引数を足し、`launch_driver`・`RunEnvironment`・各具象環境のコンストラクタへ順に通す（スレッドローカルの代わりに） | より一般的な依存性注入の形で、この項目の初期案が「`device_pool` 自身の `make_driver` 引数がすでにこれを与えている」と誤って前提にしていたものでもあります（実際には与えていません。作業単位5を参照）。実際にこの形で配線すると、`XcuitestEnvironment`・`AndroidEnvironment`・`WebEnvironment`・`FakeEnvironment` という `RunEnvironment` の各サブクラスの公開コンストラクタすべてに、診断機能のためだけに手を入れることになります。作業単位2が使うスレッドローカルの方が変更範囲が小さくて済みますが、その代わり差し込み口が明示的な引数ではなく暗黙のものになります |
| `trace_run.py` と同様に、証拠書き込み（`FileSink.capture`）の計測を4つ目のカテゴリとして加える | 証拠取得が内部で行うドライバ呼び出し（`screenshot`、`query`）自体は、すでに `driver` カテゴリで見えています。残るのはファイル I/O とマスク処理のオーバーヘッドで、これは「シミュレータ・エミュレータを操作する処理」というこの項目の動機の外側にあります。証拠書き込み自体の遅延が疑われる事態になれば、そのとき別項目として追加します |
| アーキテクチャ上の対称性のために、Web（Playwright）バックエンドも対象に含める | この項目の動機はシミュレータ・エミュレータの操作遅延に限定されています。Playwright のブラウザとの通信は自身の Python バインディング内部で完結していて、bajutsu のドライバ側が起点となる往復ではありません。`TracingDriver` が包む `Driver` プロトコルの境界自体は、将来 `PlaywrightDriver` を対象に加えたくなってもそのまま機能します |
| `BAJUTSU_LOG_LEVEL` や `BAJUTSU_STALL_DIAGNOSTICS` に倣い、環境変数（`BAJUTSU_DRIVER_TRACE=1`）で有効化する | 既存の2つの opt-in 診断機構との一貫性を考慮して検討しました。今回は代わりに CLI フラグを選び、有効・無効の判断が、オペレータが把握しておくべき環境変数の中にではなく、実行そのもののコマンド行や CI の設定の中に見えるようにしました |
| `transport` の POST レコードに、小さな構造化結果ではなくレスポンス本文まるごとを記録する | 1つのトレースファイルでより多くの疑問に答えられます（たとえば `/tap` がどのフォールドを畳み込んだかまで正確にわかります）。採らなかった理由は、`/elements` や `/act` の応答が持ちうる本文は、ランの証拠（`elements.json`）としてすでに記録されているからです。`driver_trace.json` にも複製すると、診断用の成果物がラン本体より大きくなりかねません。この項目の動機（往復回数と所要時間）にはその内容までは要りません |

## 進捗

> 作業が進むごとに、この節を最新の状態に保ちます。チェックリストは「詳細設計」の
> MECE な作業分解を写したもの（作業単位1つにつき1つのチェックボックス）で、
> ログには変更内容と日時を古い順に記録し、関連する PR へリンクします。

- [ ] 作業単位 1 — `base.Driver` を満たす委譲プロキシ `TracingDriver`。自前のプロトコル
      メソッドは1つも宣言せず（`__getattr__` のみ）、包んでいるドライバが実際にその呼び出しを
      持つときだけ計測する。これにより、能力プロトコル（`InterruptionPolicyTarget`、`SettledReadProvider` など）への `isinstance` は、
      包んでいるドライバの本当の能力をそのまま反映し続ける。
- [ ] 作業単位 2 — `make_driver` と `AdbDriver` の `run=` ラップが読む、共有のスレッドローカルな
      トレース文脈。作業単位6の `_ScenarioRunner.run_one` フックがセットする。
- [ ] 作業単位 3 — iOS側の `transport` カテゴリの計測。`XcuitestDriver` に新しい
      任意のコンストラクタ引数を追加し、既存の `_tracking_transport` ラップと並べて
      `self._transport` をもう1段ラップし、POSTなら `_Reply.status` を記録する。
      `backends.make_driver` の `xcuitest` 分岐が、作業単位2の文脈がトレース有効を示すときに
      これを渡す。
- [ ] 作業単位 4 — Android側の `transport` と `subprocess` カテゴリの計測。どちらも
      `backends.make_driver` の `adb` 分岐の内部で行う。`fetch_hierarchy`、`fetch_clock`、`act`
      をラップし（`transport`。`act` のラップは `ActOutcome.acted`／`.published_mark` も
      記録する）、計測用にラップした `adb.real_run` を `AdbDriver` の `run=` として渡す
      （`subprocess`）。`run=` が届かない1呼び出しのために `AdbDriver._run_text` の
      クラスレベル属性も差し替える。どのモジュールにも `subprocess` へのモンキーパッチは行わない。
- [ ] 作業単位 5 — `driver` カテゴリのラップ。`device_pool` の `lease()` クロージャが、
      `launch_driver(...)` の戻り値を `TracingDriver` で包んでから `Lease.driver` へ格納する
      （テアダウンはその引数を読まないことを詳細設計の作業単位5で確認済み）。
- [ ] 作業単位 6 — `_ScenarioRunner.run_one` と `_StepRunner._run_one` への
      シナリオ・ステップ境界フックの追加。トレース文脈（作業単位2）の開始・書き出しと、
      `RunArtifactWriter.write_json` 経由での `driver_trace.json` 書き出し。
- [ ] 作業単位 7 — `bajutsu run --trace-driver` という CLI フラグの追加と、
      `_RunPlan` から `_ScenarioRunner` への配線。
- [ ] 作業単位 8 — テスト。`FakeDriver` に対する `TracingDriver` のユニットテストと、
      `settled_query` を持たないドライバに対するテスト（`isinstance` の判定が崩れないことを
      確認する）、`fake` バックエンドに対して `--trace-driver` を付けて実行し出力ファイルの形を
      検証するテスト、フラグなしの実行では `driver_trace.json` が書き出されないことを
      検証するテスト。
- [ ] 作業単位 9 — ドキュメント。`bajutsu run` のフラグ一覧に、両言語で
      `--trace-driver` を追記する。

## 参考

- [BE-0407 — 証拠読み取りの重複排除とドライバ内部の調整による、ステップ実行の高速化（iOS と Android）](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)
- [`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py) — この項目が恒久的なシナリオ単位の機能へ引き上げる、調査用スクリプト
