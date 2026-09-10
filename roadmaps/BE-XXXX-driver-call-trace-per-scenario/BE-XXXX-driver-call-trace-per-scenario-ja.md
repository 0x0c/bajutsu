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
使うのは、orchestrator がすでに持っている依存性注入の差し込み口だけです。その大半は
テスト向けに追加されたか、BE-0407 自身のドレイン追跡用ラッパーとして用意されていたものです。

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

- **`driver`**：`Driver` プロトコルの各メソッド呼び出し（`tap`、`query`、`screenshot`、`wait_for` など）1回につき1レコードです。加えて、プロトコルには含まれないものの、
  orchestrator が具象ドライバへ直接呼び出している `drain_interruptions` と `settled_query` も、
  `trace_run.py` と同様に計測対象とします。
- **`transport`**：1回のドライバメソッド呼び出しの**内部**で起きるホストと端末の往復
  1回につき1レコードです。`/zorder` も取得する `query()` 呼び出しは、1つの `driver`
  レコードの下に `transport` レコードを2つ持ちます。きれいに解決する `tap()` 呼び出しなら
  1つだけです。
- **`subprocess`**：Android 限定です。常駐サーバー経由に乗らない [`hierarchy_read.py:8-10`](../../bajutsu/common/drivers/adb/hierarchy_read.py) の `uiautomator dump` フォールバックや、[`_functions.py:111-112`](../../bajutsu/common/backend_cli/adb/_functions.py) の `adb shell` コマンドを指します。
  iOS の `simctl` と `xcodebuild` のプロセス起動は、デバイスのリース時、つまり
  どのシナリオのステップも始まる前に一度きり発生するだけです。ステップ単位の手がかりを
  持たないため、計測対象にしません。

各レコードは `{category, step, name, started_at, elapsed_s}` を持ちます。`step` は
その呼び出しが発生したステップの番号と種別（`trace_run.py` と同じ形式の
`f"{i:02d}:{種別}"`）です。`started_at` は壁時計の Unix エポック秒で、`device.log` や
`manifest.json` 内のステップ自身の `started_at` と突き合わせられます。`elapsed_s` は
その呼び出し自体の所要時間です。

### モンキーパッチではなく合成で実現する

`trace_run.py` がモンキーパッチに頼っているのは、`bajutsu` 自身のソースを編集できない
外部スクリプトだからです。この項目は編集できます。そして orchestrator は、同種の計測を
恒久機能とするために必要な差し込み口をすでに持っています。どれも新設するものではなく、
テスト向け、あるいは BE-0407 自身が、すでに追加していたものです。

1. **`TracingDriver`（新規）**：`base.Driver` を満たす委譲プロキシです。プロトコルの
   各メソッドと `drain_interruptions`、`settled_query` は、委譲する前に呼び出し時間を計測します。
   計測結果は、そのとき有効なステップ（後述）に対する `driver` カテゴリのレコードとして1件
   記録します。それ以外の属性アクセス（`.name`、`.device_os` など）は `__getattr__` で
   素通しします。これを保持する呼び出し元にとって、計測が加わる以外の挙動は変わりません。
2. **iOS の `transport`**：
   [`XcuitestDriver.__init__`](../../bajutsu/common/drivers/xcuitest/xcuitest_driver.py) は、
   BE-0407 作業単位 6 のドレイン追跡を組み込むために、すでに `self._transport` を
   委譲クロージャ `_tracking_transport` で1段ラップしています。この項目では、
   同じ場所にもう1段、計測用のラップを重ねるだけで済みます。追加するのは新しい任意引数
   （たとえば `on_transport_call: Callable[[str, float, float], None] | None`）1つで、
   `--trace-driver` が渡されたときだけ効きます。`_raw_http_transport` や他のモジュールには
   一切手を入れません。
3. **Android の `transport`**：
   [`backends.make_driver`](../../bajutsu/common/backends.py) の adb 分岐は、
   `fetch_hierarchy`、`fetch_clock`、`act` という呼び出し可能オブジェクトを呼び出し元から
   受け取り、そのまま `AdbDriver(...)` へ渡しているだけです。トレースが有効なときは、
   `AdbDriver(...)` を構築する前に、`make_driver` の内部でこの3つを計測用にラップします。
   `AdbDriver` 自体のソースは変更しません。
4. **Android の `subprocess`**：既存の注入口がない、唯一のカテゴリです。`real_run` や
   `uiautomator dump` フォールバックは、`bajutsu.common.backend_cli.adb` と
   `bajutsu.common.drivers.adb` の中の複数箇所から呼ばれていて、引数として外から
   渡される形になっていません。そこで、このモジュール1つに閉じた形で、
   `subprocess.run` と `subprocess.check_output` という名前だけを差し替えます。
   差し替えは `--trace-driver` を渡した実行中だけ有効にし、範囲もこのモジュールの
   名前空間の中だけに限ります。`trace_run.py` が採っていたのと同じ割り切りを、
   プロセス全体ではなく1モジュールに閉じ込める形です。
5. **注入点**：`bajutsu.common.runner.pool.device_pool` は、テストのために追加された
   注入可能な `make_driver` 引数（`Callable[..., base.Driver] = _make_driver`）を
   すでに持っています。`--trace-driver` が指定されたときは、`bajutsu/run/cli.py` の
   ディスパッチ処理が実体の `make_driver` を呼びます（作業単位2〜3の transport ラップ込みです）。
   返ってきたドライバは、`TracingDriver` で包んで渡します。
   - `pool.py` の `Lease.driver` は、この環境自身のテアダウン処理（`lease_env.end_lease` と `teardown`）にもそのまま渡ります。
     一見すると、テアダウン側に渡す値だけ生のドライバのままにするか、`run_scenario()` へ渡す値だけを
     ラップするかという選択を迫られそうですが、実際にはその必要がありません。どの環境の `teardown` も、
     `driver` 引数はインタフェースの形を揃えるためだけに受け取っていて、中身は一切読んでいません。
     いずれも `# noqa: ARG002  # Environment shape` という注記付きです
     （[`environments/ios.py:88`](../../bajutsu/common/platform_lifecycle/environments/ios.py)、
     [`android_environment.py:363`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)）。
     テアダウンが読むのは環境自身が持つ状態（`self._resident`、`self._serial`、ランナーのプロセスなど）だけです。
     したがって `Lease.driver` は一律に `TracingDriver` でラップしてよく、テアダウン用と
     ステップループ用とで値を使い分ける必要はありません。
6. **シナリオとステップの境界**：こちらは自分たちで直接編集するファイルなので、
   モンキーパッチではなく明示的な呼び出しを2箇所加えます。
   - [`pipeline.py`](../../bajutsu/common/runner/pipeline.py) の `_ScenarioRunner.run_one`
     は、冒頭でそのシナリオの `sid` を鍵にしたスレッドローカルなトレース文脈を開きます。
     `finally` では、蓄積したレコードを `self._artifacts()`
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
     常に「このシナリオの、今この瞬間」を指します。
7. **CLI フラグ**：`bajutsu run --trace-driver`（`bajutsu/run/cli.py`）を追加し、
   `_RunPlan` を経由して `device_pool(...)` まで渡します。既存の `--score` や `--zip` と
   同じ「診断専用で、デフォルトは無効」というパターンを踏襲します。

### 出力形式

`runs/<run_id>/<sid>/driver_trace.json`:

```json
{
  "scenario": "<シナリオ名>",
  "steps": [{"step": "00:tap", "wall_s": 1.02}],
  "records": [
    {"category": "driver", "step": "00:tap", "name": "tap", "started_at": 1234567890.1, "elapsed_s": 0.69},
    {"category": "transport", "step": "00:tap", "name": "POST /tap", "started_at": 1234567890.1, "elapsed_s": 0.62}
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
| `transport` と `subprocess` の両方を、モンキーパッチを一切使わず注入可能な引数だけで実現する | `transport`（上記の作業単位2〜3）についてはこれが可能で、この項目でも実際にその経路を採っています。一方 `subprocess` については、`backend_cli/adb` 内の `real_run` と `uiautomator dump` フォールバックのすべての呼び出し箇所でシグネチャを広げる必要があり、1モジュールに閉じたモンキーパッチよりも侵襲的になります |
| `trace_run.py` と同様に、証拠書き込み（`FileSink.capture`）の計測を4つ目のカテゴリとして加える | 証拠取得が内部で行うドライバ呼び出し（`screenshot`、`query`）自体は、すでに `driver` カテゴリで見えています。残るのはファイル I/O とマスク処理のオーバーヘッドで、これは「シミュレータ・エミュレータを操作する処理」というこの項目の動機の外側にあります。証拠書き込み自体の遅延が疑われる事態になれば、そのとき別項目として追加します |
| アーキテクチャ上の対称性のために、Web（Playwright）バックエンドも対象に含める | この項目の動機はシミュレータ・エミュレータの操作遅延に限定されています。Playwright のブラウザとの通信は自身の Python バインディング内部で完結していて、bajutsu のドライバ側が起点となる往復ではありません。`TracingDriver` が包む `Driver` プロトコルの境界自体は、将来 `PlaywrightDriver` を対象に加えたくなってもそのまま機能します |
| `BAJUTSU_LOG_LEVEL` や `BAJUTSU_STALL_DIAGNOSTICS` に倣い、環境変数（`BAJUTSU_DRIVER_TRACE=1`）で有効化する | 既存の2つの opt-in 診断機構との一貫性を考慮して検討しました。今回は代わりに CLI フラグを選び、有効・無効の判断が、オペレータが把握しておくべき環境変数の中にではなく、実行そのもののコマンド行や CI の設定の中に見えるようにしました |

## 進捗

> 作業が進むごとに、この節を最新の状態に保ちます。チェックリストは「詳細設計」の
> MECE な作業分解を写したもの（作業単位1つにつき1つのチェックボックス）で、
> ログには変更内容と日時を古い順に記録し、関連する PR へリンクします。

- [ ] 作業単位 1 — `base.Driver` を満たす委譲プロキシ `TracingDriver`。プロトコルの
      各メソッドと `drain_interruptions`、`settled_query` を計測し、それ以外は
      `__getattr__` で素通しする。
- [ ] 作業単位 2 — iOS 側の `transport` カテゴリの計測。`XcuitestDriver` に新しい
      任意のコンストラクタ引数を追加し、既存の `_tracking_transport` ラップと並べて
      `self._transport` をもう1段ラップする。
- [ ] 作業単位 3 — Android 側の `transport` カテゴリの計測。`backends.make_driver` の
      `adb` 分岐で、`AdbDriver` を構築する前に `fetch_hierarchy`、`fetch_clock`、`act`
      をラップする。
- [ ] 作業単位 4 — Android の `subprocess` カテゴリの計測。
      `bajutsu.common.backend_cli.adb` に閉じた、`--trace-driver` 有効時だけの
      `subprocess.run` と `subprocess.check_output` の差し替え。
- [ ] 作業単位 5 — 注入の配線。`--trace-driver` 時に `device_pool(...)` へ渡す
      `make_driver` ラッパー。`Lease.driver` は一律にラップする（テアダウンは読まない）。
- [ ] 作業単位 6 — `_ScenarioRunner.run_one` と `_StepRunner._run_one` への
      シナリオ・ステップ境界フックの追加。`RunArtifactWriter.write_json` 経由での
      `driver_trace.json` 書き出し。
- [ ] 作業単位 7 — `bajutsu run --trace-driver` という CLI フラグの追加と、
      `_RunPlan` への配線。
- [ ] 作業単位 8 — テスト。`FakeDriver` に対する `TracingDriver` のユニットテスト、
      `fake` バックエンドに対して `--trace-driver` を付けて実行し出力ファイルの形を
      検証するテスト、フラグなしの実行では `driver_trace.json` が書き出されないことを
      検証するテスト。
- [ ] 作業単位 9 — ドキュメント。`bajutsu run` のフラグ一覧に、両言語で
      `--trace-driver` を追記する。

## 参考

- [BE-0407 — 証拠読み取りの重複排除とドライバ内部の調整による、ステップ実行の高速化（iOS と Android）](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)
- [`trace_run.py`](../BE-0407-step-latency-driver-internal-tuning/misc/step-performance/trace_run.py) — この項目が恒久的なシナリオ単位の機能へ引き上げる、調査用スクリプト
