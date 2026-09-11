[English](BE-XXXX-xcuitest-crash-report-scenario-artifact.md) · **日本語**

# BE-XXXX — iOS ランナーのクラッシュレポートを、失敗したシナリオの run ディレクトリへコピーする

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-xcuitest-crash-report-scenario-artifact-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | Platform support |
| 関連 | [BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics-ja.md)、[BE-0319](../BE-0319-xcuitest-cold-spawn-resilience/BE-0319-xcuitest-cold-spawn-resilience.md)、[BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md) |
<!-- /BE-METADATA -->

## はじめに

常駐する XCUITest ランナーがシナリオの途中でクラッシュし、実行パイプラインのクラッシュ回復リトライが
尽きて復旧できなかったとき、`bajutsu run` はクラッシュのエラーだけからシナリオの失敗メッセージを
組み立てます。ランナーが死んだという事実は名指しますが、ランナーログのパスもログの内容も、
プロセスがフォルトしたときに macOS 自身が書き出すレポートへの言及も一切含みません。その瞬間、
ディスク上には直接の証跡が2つ存在します。ランナー自身が記録した出力と、ホストプロセス自身が
フォルトしていれば macOS が書き出したクラッシュレポートです。どちらも、そのシナリオ自身の run
ディレクトリ（`runs/<run_id>/<sid>/`）、つまりそのシナリオの他のあらゆる証跡がすでに置かれている
場所には届きません。本項目は、この2つをそのディレクトリへコピーします。これにより、赤くなった
シナリオを調べる開発者は、同じ実行がすでに生成しているスクリーンショットや要素ツリーの隣でランナー
自身の失敗の証跡を見つけられます。警告レベルのログを漁ってパスを探す必要も、ランナープロセスが
実際に何をしたのか見るためだけに追加の診断を有効にして再実行する必要もなくなります。

## 動機

[BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics-ja.md) が、
iOS の継続的インテグレーション（CI）レーン向けに、階層化された診断情報の収集をすでに構築しました。
その第1層（ランナーの起動ごとの result bundle と、範囲を限定したストール時プローブ）が、CI
ワークフローが設定する環境変数の背後にある opt-in（明示的に有効化する）機能です。残る2つの層は
そうではありません。GitHub Actions のコンポジットステップがすでに、あらゆる iOS ジョブで
無条件に走り、macOS ホスト自身のクラッシュレポートとログストアを掃引しています
（`.github/actions/collect-ios-diagnostics/action.yml`）。つまり CI は、通常のケースでは、
ランナーのクラッシュレポートをすでに今日から集めています。

それでも、この収集には本項目が埋める2つの隙間が残っています。1つ目は、ジョブ単位でありシナリオ
単位ではないことです。`~/Library/Logs/DiagnosticReports` の中身をジョブ全体分まとめて固めるため、
1つのジョブが十数個のシナリオを走らせていて複数がクラッシュした場合、どのクラッシュレポートが
どの失敗シナリオのものかを、開発者は見分けられません。2つ目は、CI専用のシェルコードであり、
`bajutsu` 自身には対応するものがないことです。ローカルの `bajutsu run` でクラッシュを再現している
開発者には、何も届きません。BE-0319 のランナーログキャプチャがすでにログファイルへ書き出している
パスの手がかりすら届きません。そのパスは、シナリオ自身の失敗メッセージやレポートには一切届かず、
警告レベルのログ行1つにしか届かないからです
（[`_runner_log_hint`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py)）。
失敗した実行がその警告行を表示していなければ、それすら見えません。

そのクラッシュレポート自体が存在するのは、XCUITest のホストプロセス（`xcodebuild
test-without-building`）が普通の macOS プロセスだからです。スクリーンショットサービスの
ストールが引き起こす、テスト失敗コードでの終了というありふれた形とは違い、フォルトで終了すると、
OS は `~/Library/Logs/DiagnosticReports` 配下に `.ips` クラッシュレポートを書き出します。そこには
終了の原因となったシグナルと、システムフレームについてはシンボル化されたスタックトレースが
記録されています。これは、本物のプロセスフォルトが生み出す唯一の直接的な証跡です。本項目が
対象とする「チャンネルが応答しなくなった」という通常のクラッシュよりも、狭く、稀なケースです。

本項目が生み出そうとしている観測可能な違いは次の点です。クラッシュリトライが尽きて失敗した
シナリオは、自分自身の `runs/<run_id>/<sid>/` の下に `crash-diagnostics/` サブディレクトリを
獲得し、そこにランナーの記録出力全文と、macOS が `xcodebuild` プロセスについて書き出していれば
`.ips` クラッシュレポートを保持します。シナリオ自身の失敗文字列も、そのサブディレクトリの存在を
名指しします。失敗を読む開発者は、あらかじめその存在を知っている必要がなくなります。今日は、
このサブディレクトリとその言及のどちらも存在しません。

## 詳細設計

### すべての environment が自前で定義するメソッド。クラッシュ回復層がすでに使っている形に従う

`RunEnvironment`
（[`bajutsu/common/platform_lifecycle/protocols/run_environment.py`](../../bajutsu/common/platform_lifecycle/protocols/run_environment.py)）
は構造的な `Protocol` です。どの具象 environment もこれを継承していません。そのため、そこに
書いたメソッドの本体は誰にも結び付きません。「デフォルトでは no-op」というメソッドはどれも、
`request_device_replacement` と `replaced_device`（BE-0354）を含め、具象クラスごとに別々に
書き出されています。`_DeviceEnvironment`（[`ios.py`](../../bajutsu/common/platform_lifecycle/environments/ios.py)、
Simulator の XCUITest バックエンドと fake テストバックエンドが共有）、`WebEnvironment`
（[`web.py`](../../bajutsu/common/platform_lifecycle/environments/web.py)）、そして
`AndroidEnvironment`
（[`android_environment.py`](../../bajutsu/common/platform_lifecycle/environments/android/android_environment.py)）
の3つです。本項目は `crash_artifacts()` を、プロトコルの宣言する形にも、この3つのクラス
すべてにも追加し、それぞれ `[]` を返すようにします。

```python
def crash_artifacts(self) -> list[tuple[str, bytes]]:
    """Files this environment captured for its last backend crash, or [] when it has none."""
    return []
```

`XcuitestEnvironment` はこれをオーバーライドします。`_DeviceEnvironment` の
`request_device_replacement`（`xcuitest_environment.py:500`）をすでにオーバーライドしているのと
同じ形です。

### クラッシュ検出の瞬間にスナップショットを取る。後から生きた状態を読みには行かない

パイプラインのクラッシュ回復リトライループ `_run_one_impl`
（[`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py)）は、リトライ
ループがリトライするかどうかを決める*前に*、`_run_on_lease` 自身の `finally` の中でクラッシュした
lease をプールへ返却します（`free.put(udid)`）。もし `crash_artifacts()` が `self._runner_log` /
`self._runner_proc` を遅延評価で、つまりループが諦めた時点で初めて読みに行く作りだと、
複数デバイスの実行では競合が起こります。別のワーカーの次の lease は、この同じ environment
インスタンスを再利用でき（`pool.py` はウォームキャッシュを udid で管理しています）、このシナリオの
リトライループが古いクラッシュの証跡を読み戻すより前に、そのインスタンス上で新しいランナーを
再起動できてしまいます。それは `self._runner_log` と `self._runner_proc` をクリアし
（`_discard_runner`、`xcuitest_environment.py:1142`）、再起動が正常であれば、クラッシュ関連の
情報を何も残しません。

そこで `XcuitestEnvironment` は、代わりに前もってキャプチャします。タイミングは、
`_discard_runner` 自身が最初にクラッシュを観測する場所です。そこはすでに `crashed = True` を
設定し、「a mid-run crash」とログに記録している箇所であり
（`xcuitest_environment.py:1170-1176`）、その数行あとで `self._runner_proc = None` がハンドルを
クリアするより前です。まさにその場所で、以下の2種類のエントリを読み取り、
`self._last_crash_artifacts` としてキャッシュします。`crash_artifacts()` は、そのキャッシュ済み
リストを返すだけです。どちらのエントリもベストエフォートで、`_result_bundle_path` や
`_capture_stall` が自分自身のキャプチャですでに取っている姿勢と同じです。ログが見つからない場合、
`DiagnosticReports` ディレクトリが読み取れない場合（macOS 以外のプラットフォーム、または読み取り
権限のないサンドボックス化された CI ランナー）、クラッシュレポートが1つも存在しない場合
（プロセス自体は実際にはフォルトしておらず、単にチャンネルが応答しなくなっただけの場合）、
この3つのいずれであっても例外を投げません。該当するエントリを省略するだけにとどめます。

- **ランナー自身が記録した出力全文**。`_open_runner_output` が開く `self._runner_log` から
  全文を読み取ります。この出力は今日すでにデフォルトで（BE-0319）キャプチャされていますが、
  どこにもコピーされていません。
- **`xcodebuild test-without-building` プロセス自身の macOS クラッシュレポート**。
  `_spawn_runner` はすでに、`Popen` が返った直後にプロセスハンドルを `self._runner_proc` として
  記録しています（`xcuitest_environment.py:766`）。本項目は、その隣に起動タイムスタンプ
  `self._runner_spawned_at = time.time()` を追加します。`Popen` 自体は起動時刻を公開しないため
  です。このキャプチャは `~/Library/Logs/DiagnosticReports` を列挙し、`xcodebuild-*` という
  名前で、更新時刻が `self._runner_spawned_at` 以降である `.ips` ファイルを探します。ファイル名と
  時刻の両方を照合することで、同じホスト上で以前に動いた無関係な `xcodebuild` 呼び出しが残した
  レポートを、この掃引が拾わないようにしています。ファイル自身の JavaScript Object Notation
  （JSON）ヘッダーが `pid` を
  名指ししていれば、それを `self._runner_proc.pid` と照合することで、複数ワーカーのホスト上で
  並行して動く複数の `xcodebuild` プロセスをさらに絞り込みますが、ヘッダーが解析できない
  レポートも、名前と時刻の一致だけで採用します。このキャプチャは、あくまでベストエフォート
  だからです。列挙は最初の数件までに制限します。これは BE-0361 自身のキャプチャ上限と同じ
  考え方です。クラッシュを繰り返すランナーが、1つのシナリオの証跡を際限なく書き込むことを、
  この上限が防ぎます。

この順序こそが、一度解放されて再び貸し出された environment には取り消せないものです。
スナップショットは `free.put(udid)` が走るより前に、すでに取得してキャッシュ済みだからです。
後続の再起動がどんな状態変化を起こしても、それには一切触れません。1つだけ、狭い隙間が残ります。
これは environment インスタンス単位でキャッシュしていることに由来します。もし*同じ*
environment が、最初のシナリオのリトライループが `crash_artifacts()` を読み戻す前に、別の
シナリオで再びクラッシュしたら、2回目のクラッシュのスナップショットが1回目を上書きします。
これが起こるには、1つの共有されたウォーム environment 上で、複数のワーカーにまたがる2つの
クラッシュ回復エピソードが競合する必要があります。これは BE-0354 自身のデバイス交換の段（rung）が
すでに、通常のリトライではなく劣化デバイスのエスカレーションとして扱っているケースです。
本項目は、これをベストエフォートなキャプチャが抱える、受け入れ済みの狭い限界として残し、
埋める対象とはしません。

### シナリオ自身の writer へ届ける

`_run_one_impl` は、キャッシュ済みのスナップショットを書き出すために本項目が必要とする2つの
情報を、すでに両方保持しています。シナリオ自身の証跡ディレクトリ名である `sid` と、クラッシュ
した試行が実行されていた `Lease` である `lz` です。`Lease`
（[`bajutsu/common/runner/types.py`](../../bajutsu/common/runner/types.py)）に、フィールドを
1つ追加します。`relaunch` や `control` の隣にある他のフィールドと同じように、モジュール
レベルの no-op をデフォルトとして与えます。

```python
def _no_crash_artifacts() -> list[tuple[str, bytes]]:
    return []

# Lease 上:
crash_artifacts: Callable[[], list[tuple[str, bytes]]] = _no_crash_artifacts
```

`pool.py` の `lease()` クロージャの中で、`request_device_replacement=lease_env.request_device_replacement`
がすでに配線されているのと同じ形で配線します（`pool.py:556`）。束縛されたメソッド参照であって
呼び出しではないため、パイプラインが実際に求めるまでは何も実行されません。

パイプラインがそれを求めるのは、ちょうど1回だけです。リトライループが諦めて、クラッシュで
力尽きた失敗についてシナリオの最終的な `RunResult(ok=False, ...)` を組み立てる箇所の直前です。
この箇所はすでに、その失敗用に `failure` を設定している `if device_timeout ... elif ...
else:` の連なりです。`lz` が `None` でなく、`self._artifacts()` が writer を返すとき、パイプラインは
`lz.crash_artifacts()` を呼び出し、返ってきた `(name, content)` の組をそれぞれ
`writer.write_text(f"{sid}/crash-diagnostics/{name}", content.decode(errors="replace"))` として
書き込みます。これは、
[BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md)
がすでに `driver_trace.json` に使っている、シナリオ単位の書き込みの形と同じです。`write_bytes`
ではなく `write_text` を使うのは、本項目が生成したのではない内容に対しても、自由テキストの
マスキング処理が引き続き走るようにするためです（BE-0331）。このサブディレクトリのパスは
`failure` 自身にも追記されます。これにより、開発者が実際に読む失敗文字列が新しい証跡を直接
指すようになり、動機の節で述べた隙間を埋めます。書き込みの失敗（ディスク容量の枯渇や権限の
問題）は捕捉してログに記録し、シナリオ自身のクラッシュで力尽きた `RunResult` を差し替えることは
ありません。診断用のアーティファクトが、すでに確定した失敗を別の無関係な失敗にすり替えてしまう
ことがあってはならないからです。

### 毎回の試行ではなく、1回だけである理由

BE-0361 のストールプローブはクラッシュのたびに発火します。これは、*リトライそのもの*を
試す価値があるかどうかを調べているためです。本項目は、リトライループがすでに諦めたときにだけ
1回発火します。その証跡（ランナーのクラッシュ）は、1つのシナリオがクラッシュを繰り返す
どの試行でも同じ事実です。試行のたびにコピーすると、最終的に復旧したシナリオまでクラッシュ
証跡を抱えることになります。その証跡は、もはや自分自身の最終結果には表れていない失敗に
ついてのものです。リトライの予算内で復旧したシナリオは合格します。合格したシナリオに、
クラッシュレポートは必要ありません。

### 他のあらゆるバックエンドでのコスト

Android とウェブバックエンドの environment は、それぞれ自前の `crash_artifacts()` から `[]` を
返します。パイプラインの書き込みステップは空のリストを反復するだけの no-op になり、今日と変わり
ません。iOS バックエンド自体も macOS 上でしか構築されないため、`DiagnosticReports` の掃引は
そもそも Linux ホストでは走りません。本項目は、macOS 以外の実行がキャプチャする内容を何も
変えません。

## 検討した代替案

| 代替案 | 採らなかった理由 |
|---|---|
| BE-0361 の `BAJUTSU_XCUITEST_RESULT_BUNDLES` / `BAJUTSU_STALL_DIAGNOSTICS` に合わせ、環境変数で opt-in にする | 本項目が埋める隙間は、BE-0361 第1層の隙間とは逆です。CI はすでに、第2〜3層によってクラッシュレポートを無条件に集めています。足りないのは、ローカル実行向けの対応物と、シナリオ単位の帰属付けであり、どちらも CI 専用の opt-in 変数では埋まりません。このキャプチャは、シナリオがすでに失敗して終わろうとしている場面でしか走らないため、そのコストは有界なディレクトリ列挙と1回のファイルコピーにとどまり、ゲートで守るほどの常時オーバーヘッドではありません。 |
| BE-0361 unit 1 が生成できる `.xcresult` result bundle もコピーする | この bundle はすでに BE-0361 自身の opt-in なアーティファクトであり、`BAJUTSU_XCUITEST_RESULT_BUNDLES` の背後にあって、`.ips` レポートのようには上限がありません。ここでデフォルトで有効にすると、`.ips` クラッシュレポートとランナー自身のログがすでに要約している内容のために、上限のないアーティファクトを追加することになります。本項目が追加するコンパクトな証跡だけでは足りないとわかった場合の、将来の項目に残します。 |
| リトライ予算を使い切った1回だけでなく、クラッシュ回復の試行のたびにキャプチャする | 「毎回の試行ではなく、1回だけである理由」で述べたとおり却下します。最終的に復旧するシナリオに対して重複しますし、この証跡が説明すべき対象であるシナリオのクラッシュで力尽きた `RunResult` は、ループの終わりに一度しか存在しません。 |
| クラッシュ時に `xcrun simctl diagnose`、`log collect`、`sysdiagnose` によるフルスイープを行う | BE-0361 自身の「検討した代替案」がこれを却下し、実測した理由と同じ理由で却下します。`simctl diagnose` 単体でも、起動済みデバイス1台あたり22〜78 MB、約15秒を要します。ジョブの時間窓全体の `.logarchive` は数MBに達します。プロセス自身の `.ips` レポートは、終了の原因となったシグナルと、システムフレームについてはシンボル化されたスタックトレースを、数キロバイトのコストですでに記録しています。 |

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] Unit 1 — `crash_artifacts()` を `RunEnvironment` プロトコルの宣言する形に追加し、`[]` を
      返す実装を `_DeviceEnvironment`（ios.py）、`WebEnvironment`、`AndroidEnvironment` に
      それぞれ追加します。
- [ ] Unit 2 — `XcuitestEnvironment` によるオーバーライド。`self._runner_proc` の隣に記録する
      起動タイムスタンプ（`self._runner_spawned_at`）。`_discard_runner` 内部で、クラッシュした
      プロセスハンドルがクリアされる前に `self._last_crash_artifacts` としてキャッシュする
      前もってのスナップショット。ランナーログの読み取りと `xcodebuild-*.ips` に対する名前・
      時刻一致の `DiagnosticReports` 掃引。どちらもベストエフォートかつ上限つきです。
- [ ] Unit 3 — `Lease.crash_artifacts`。モジュールレベルの `_no_crash_artifacts` をデフォルトと
      し、`pool.py` の `lease()` クロージャ内で `request_device_replacement` と並んで配線します。
- [ ] Unit 4 — `pipeline.py` の呼び出し箇所。クラッシュで力尽きた `RunResult` の直前で1回だけ
      呼び出し、各アーティファクトを `RunArtifactWriter.write_text` を通じて
      `f"{sid}/crash-diagnostics/"` の下へ書き込み、そのパスを `failure` 文字列にも追記します。
      書き込みの失敗は例外を投げずログに記録します。
- [ ] Unit 5 — ドキュメント: BE-0361 が `docs/ci.md`（および `docs/ja/` のミラー）に追加した CI
      診断の節に、このデフォルト有効なシナリオ単位版についての注記を加えます。
- [ ] Unit 6 — テスト: スタブ化した `DiagnosticReports` ディレクトリに対する
      `XcuitestEnvironment` のクラッシュスナップショットのテスト（名前・時刻の一致、pid による
      絞り込み、上限、ログやレポートが見つからない場合）。共有された environment 上で2回目の
      クラッシュが1回目のシナリオのキャッシュ済みスナップショットを上書きすることを確認する
      テストで、文書化した限界を固定します。クラッシュで力尽きたシナリオの run ディレクトリに
      `crash-diagnostics/` とその `failure` 内のパスが現れることを確認する `pipeline.py` の
      テスト。復旧したシナリオでは現れないことを確認するテスト。Android／ウェブ／fake
      バックエンドで呼び出し箇所の no-op なデフォルトが変わらないことを確認するテスト。

## 参考

- [BE-0361](../BE-0361-ios-ci-simulator-diagnostics/BE-0361-ios-ci-simulator-diagnostics-ja.md) —
  本項目が、デフォルト有効なシナリオ単位の収集で補完する、CI スコープの診断層。「検討した
  代替案」が引用する `simctl diagnose` と `log collect` のコストの出典でもあります
- [BE-0319](../BE-0319-xcuitest-cold-spawn-resilience/BE-0319-xcuitest-cold-spawn-resilience.md) —
  本項目がシナリオディレクトリへコピーする、デフォルト有効なランナー出力キャプチャ
- [BE-0354](../BE-0354-xcuitest-wedge-fastfail-device-replacement/BE-0354-xcuitest-wedge-fastfail-device-replacement.md) —
  `request_device_replacement`。本項目の `crash_artifacts()` が従うクラスごとの no-op という
  形を持つ既存メソッドであり、その デバイス交換のエスカレーションが、「詳細設計」で受け入れる
  共有 environment 由来の狭い限界を境界付けてもいます
- [BE-0415](../BE-0415-driver-call-trace-per-scenario/BE-0415-driver-call-trace-per-scenario.md) —
  本項目が従う、シナリオ単位の `RunArtifactWriter` 書き込みの形
- [`bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py`](../../bajutsu/common/platform_lifecycle/environments/xcuitest/xcuitest_environment.py) —
  本項目が読み取る `_runner_log`、`_runner_proc`、`_discard_runner`、`_runner_log_hint` という
  接点
- [`bajutsu/common/platform_lifecycle/environments/ios.py`](../../bajutsu/common/platform_lifecycle/environments/ios.py) —
  `_DeviceEnvironment`。その `request_device_replacement` の no-op を本項目のデフォルトが
  踏襲します
- [`bajutsu/common/runner/pipeline.py`](../../bajutsu/common/runner/pipeline.py) — `_run_one_impl`。
  そのクラッシュで力尽きた `RunResult` が本項目の唯一の呼び出し箇所であり、その `_run_on_lease`
  は、リトライループがリトライするかどうかを決めるより前に、クラッシュした lease を解放します
- [`bajutsu/common/runner/pool.py`](../../bajutsu/common/runner/pool.py) — `Lease.crash_artifacts`
  を `request_device_replacement` と同じ形で配線する `lease()` クロージャ
- [`bajutsu/common/platform_lifecycle/protocols/run_environment.py`](../../bajutsu/common/platform_lifecycle/protocols/run_environment.py) —
  `crash_artifacts()` が `request_device_replacement` や `replaced_device` と並んで加わる
  プロトコル
- [`bajutsu/common/evidence/sink.py`](../../bajutsu/common/evidence/sink.py) — 本項目の
  アーティファクトが通過する、単一の書き込み境界（BE-0331）である `RunArtifactWriter`
- [`.github/actions/collect-ios-diagnostics/action.yml`](../../.github/actions/collect-ios-diagnostics/action.yml) —
  BE-0361 のすでに無条件な `DiagnosticReports` 掃引。動機の節で、そのジョブ単位のスコープと
  本項目のシナリオ単位のスコープを対比しています
