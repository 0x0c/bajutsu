# XCUITestバンドルRunnerの自動更新

> ステータス: 実装完了
> 対象: `bajutsu/common/platform_lifecycle/environments/xcuitest/`、`bajutsu/common/platform_lifecycle/environments/_bundled_runner.py`、`scripts/serve.sh`、`Makefile`
> 関連: [BE-0292](../../roadmaps/BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner.md)、[docs/architecture.md](../architecture.md)

BajutsuKitのソースが存在するチェックアウトでは、wheel同梱のXCUITest Simulator Runnerを、呼び出し経路によらず常にソースと同じ状態に保つ。鮮度判定と差分時の再ビルドを`_resolve_runner`側の1箇所に集約し、`scripts/serve.sh`が独自に持つbash実装をそこへ委譲する。

## 1. なにをつくるのか

Simulatorターゲットが`xcuitest.testRunner`を指定していないとき（bundled tier）を考える。`_resolve_runner`はBajutsuKitソースの内容ハッシュを計算する。この値を、バンドル済みRunnerの`build-info.json`が記録する`sourceHash`と比較する。両者が一致しなければ、`make runner-bundle`と同等の再ビルドを実行し、その結果を使う。この判定と再ビルドは、bundled tierを実際に解決するあらゆる呼び出し経路で共通して働く。対象には`bajutsu run`、pytest経由のテスト、`bajutsu serve`が含まれる。`bajutsu doctor`は別枠であり、後述のとおり判定結果の開示だけを行い、再ビルドはしない。

再ビルドが必要なのに実行できない場合は、古いバンドルへフォールバックせずその場でエラーにする。実行できない場合とは、`xcodebuild`または`xcodegen`がない場合と、`xcodebuild`自体が失敗する場合を指す。

`doctor`の`xcuitest_runner_summary`は、ビルドを走らせずにハッシュ比較だけを行う。バンドルが最新か失効しているかを、1行追加で開示する。

### やらないこと

- **explicit tier（`xcuitest.testRunner`を指定したターゲット）には触れない。** ユーザーは`build`フィールドですでに再ビルドコマンドを制御できる。
- **device tierには触れない。** 実機Runnerは署名が要るため、引き続き明示設定を必須とする（BE-0288）。
- **BajutsuKitソースを含まないインストール（wheelインストール）では鮮度判定自体をしない。** ハッシュを取る対象のソースが存在しないため、現状どおり同梱バンドルをそのまま使う。
- **呼び出しのたびに無条件で`xcodebuild`を実行する仕組みにはしない。** ハッシュが一致する限り再ビルドは走らせない。
- **再ビルド失敗時に古いバンドルへフォールバックする経路は作らない。** 失敗はその場でエラーにする。
- **新しいコマンドライン引数は追加しない。** 既存の`BAJUTSU_SKIP_RUNNER_BUNDLE`環境変数を流用する。`serve.sh`だけでなく`_resolve_runner`側の判定にも、この環境変数を適用する。

## 2. なぜつくるのか

`bajutsu/_xcuitest_runner/`（wheel同梱のbundled Runner）の鮮度判定と自動再ビルドは、現在`scripts/serve.sh:76-101`にしかない。この仕組みは`serve_uses_xcuitest`とハッシュ比較（`scripts/xcuitest-runner-hash.sh`）を経て、`make runner-bundle`を呼ぶ。`make serve`から`bajutsu serve`を起動する経路だけがこの仕組みを発火させる。

一方、`_resolve_runner`（`_functions.py:512-554`）は、bundled tierに落ちたとき`bundled_products_dir()`の存在だけを見る。その中身が現在のBajutsuKitソースと一致しているかは確認しない。`bajutsu run`を直接叩く経路、pytestからxcuitestバックエンドのテストを実行する経路、`bajutsu doctor`で疎通確認する経路は、すべてこちらを通る。

存在確認だけで鮮度を見ない設計は、BajutsuKit/Runnerの開発中に次の事故を招きうる。Runner側のソースを変更したあと、`make serve`を経由せず`bajutsu run`やpytestを直接実行すると、`_xcuitest_runner/`に残っている古いバンドルをそのまま掴む。テストは通常どおり実行され、失敗もしない。変更した挙動が実際には反映されていないまま、「動いた」という誤った確認が残る。この不整合は`make runner-bundle`を手動で叩くまで気づけない。

デバイス経由の`demos/showcase/`のターゲット（`run-swiftui`や`e2e-*`など）は`runner-build`をmakeの前提条件にしている。CI（`ios-e2e.yml`）も明示的に`make runner-bundle`を都度実行している。したがってこの事故は、bundled tierを頼る経路に限られる。つまりBajutsuKit開発者がserve以外の経路で、素朴にxcuitestバックエンドを動かす場面に限られる。裏を返せば、その1箇所（`_resolve_runner`）に鮮度判定を集約すれば、経路ごとに個別対応する必要がなくなる。

## 3. どう実現するか

### ハッシュ計算をPythonに移す

`scripts/xcuitest-runner-hash.sh`は、次の5つを対象にハッシュを計算している。

- `BajutsuKit/Package.swift`
- `BajutsuKit/Sources`
- `BajutsuKit/Runner/Host`
- `BajutsuKit/Runner/Sources`
- `BajutsuKit/Runner/project.yml`

このハッシュ算出（sha256の入れ子）を、`_bundled_runner.py`に`source_hash() -> str`として移植する。アルゴリズムはシェル版と一致させる。既存の`build-info.json`が記録済みの`sourceHash`と食い違うと、移行直後のすべてのバンドルが不必要に「失効」と判定されてしまう。

実装時の補足を記す。実装の途中で`Package.swift`がリポジトリルートへ移動した（コミット「`chore(swift): move Package.swift to the repo root`」）。この移動を受けて、`_HASH_SOURCE_PATHS`の対象は`BajutsuKit/Package.swift`ではなく`Package.swift`にした。上の5項目は移植元のシェルスクリプトが対象にしていたものをそのまま記録している。以後の対象は`_bundled_runner.py`の`_HASH_SOURCE_PATHS`を正とする。

`Makefile`の`runner-bundle`ターゲットも、`build-info.json`への書き込みでこの関数を呼ぶよう変更する（`uv run python -c "..."`経由）。ハッシュの算出箇所を1つに保ち、シェル版とPython版が別々に変化してずれることを防ぐ。`scripts/xcuitest-runner-hash.sh`はこの時点で呼び出し元がなくなるため削除する。

### ソース有無の判定

`_bundled_runner.py`に`runner_source_present() -> bool`を追加する。`_BUNDLE_DIR`は`bajutsu/_xcuitest_runner`を`Path(__file__).resolve()`起点で指す。この判定も同じ起点の1階層上（`parents[4]`、リポジトリルート）を基準にする。そこから`BajutsuKit/Runner/project.yml`の存在を見る。`pyproject.toml`の`packages = ["bajutsu"]`が示すとおり、wheelインストールには`BajutsuKit/`が含まれない。したがってこの判定は、Gitチェックアウトかどうかを確実に見分ける。

### 鮮度判定と再ビルド

`_bundled_runner.py`に`ensure_bundled_runner_fresh() -> None`を追加する。処理の流れを次に示す。

1. `runner_source_present()`が`False`なら何もせず戻る。
2. 環境変数`BAJUTSU_SKIP_RUNNER_BUNDLE`が`"1"`なら何もせず戻る。
3. `source_hash()`を計算し、`bundled_runner_build_info()`が返す`sourceHash`と比較する。一致し、かつ`bundled_products_dir()`が値を返すなら、何もせず戻る（最新）。
4. 一致しない、またはバンドルが存在しない場合、モジュールレベルのロックを取得する。このロックは`materialize()`の`_digest_lock`と同じ位置づけを持つ。SimulatorのDevice Poolは複数レーンから並行して`_resolve_runner`を呼ぶ。ロックがなければ、同時に複数の`xcodebuild`が走りかねない。
5. ロック内で手順3を再確認する（二重チェックロック）。別レーンが直前に再ビルドを終えていれば、そのまま戻る。
6. `xcodebuild`と`xcodegen`がどちらも実行できれば、`make runner-bundle`相当のビルドをサブプロセスで実行する。
7. いずれかのツールがない、またはビルドが失敗したら、`simctl.DeviceError`を送出する。メッセージは`scripts/serve.sh:94-98`と同じ形式にする。欠けているツールを名指しする（例: 「Xcode (xcodebuild) — install Xcode」）。ビルド自体の失敗では、`xcodebuild`の失敗理由を添える。
8. サブプロセスの終了コードが0でも、手順3の一致判定を取り直す。`make`は`printf`への値渡しに使うコマンド置換の失敗を拾わない。そのため`sourceHash`が空文字列のまま`build-info.json`に書かれても、`make runner-bundle`は成功として終了しうる。一致しなければ、そのビルドを「見た目は成功したが結果が一致しない」ものとして`simctl.DeviceError`を送出する。再確認せずに戻ると、以後の呼び出しがすべて同じ不一致を検出しては黙って再ビルドを繰り返す。

`_resolve_runner`のbundled tier（`_functions.py:543`の直前）で呼び出しを追加する。`bundled_products_dir()`を呼ぶ前に`ensure_bundled_runner_fresh()`を呼ぶ。

### `scripts/serve.sh`の変更

現在bashで書かれている鮮度判定と再ビルド呼び出し（`scripts/serve.sh:73-101`）を、共通関数の呼び出しに置き換える。この呼び出しは`ensure_bundled_runner_fresh()`を呼ぶだけにとどめる。`BAJUTSU_SKIP_RUNNER_BUNDLE`のチェックはPython側にも入るが、bashのガードは残す。スキップ時は`uv run`の起動コストを払わずに済む。`serve_uses_xcuitest`によるバックエンド判定と、起動前に「staging…」を表示するUXは維持する。`ensure_bundled_runner_fresh()`が`DeviceError`を送出したら、serveの起動を中断してそのエラーメッセージを表示する。

### `doctor`の開示

`xcuitest_runner_summary`（`doctor.py:135-149`）に、ビルドを伴わない鮮度チェックの結果をもう1行加える。`runner_source_present()`が`True`で、かつハッシュが不一致のとき、バンドルが失効していて次回実行時に再ビルドされる旨を注記する。ビルドや`materialize()`は呼ばない。開示だけを行うという既存の方針は変えない。

## 4. 検討した代替案と、採らなかった理由

| 案 | 概要 | 採らなかった理由 |
|---|---|---|
| `serve.sh`と同じbashロジックを他の入口（`bajutsu run`、pytestのfixtureなど）にも複製する | 各エントリポイントの前段に同種のシェル処理を追加する | 実装が経路の数だけ増え、シェルとPythonの二重実装がドリフトする |
| ハッシュ比較を省き、bundled tierを解決するたびに無条件で`xcodebuild`を実行する | 常に最新を保証するもっとも単純な方式 | Simulatorのdevice poolは複数レーンを並行起動するため、レーンごとに数十秒単位の待ちが乗り、テスト実行全体が大幅に遅くなる |
| 自動発火はさせず、`--rebuild-runner`のような明示フラグでのみ再ビルドする | ユーザーが必要と判断したときだけ実行する | 「常に最新」という動機を満たさない。フラグを付け忘れれば従来どおり古いバンドルを掴む |
| 再ビルドに失敗したら既存バンドルへフォールバックし警告だけ出す（`serve.sh`の現行挙動を踏襲） | ビルド環境が整っていないホストでも動作を止めない | 「常に最新」を守れないまま実行を続けてしまい、古いRunnerでの実行に気づけない事故を再発させる |

## 5. 作業手順

| # | 状態 | やること | 触るファイル | 完了条件 | 前提 |
|---|---|---|---|---|---|
| 1 | ✅ | `source_hash()`を実装し、既存の`scripts/xcuitest-runner-hash.sh`と同じ入力に対して同じ値を返すことをテストで確認する | `bajutsu/common/platform_lifecycle/environments/_bundled_runner.py`、対応するテスト | 固定したフィクスチャに対するユニットテストが通る（`pytest`） | — |
| 2 | ✅ | `runner_source_present()`を実装する。`BajutsuKit/`がないディレクトリとあるディレクトリの両方をテストで確認する | 同上 | ユニットテストが通る | — |
| 3 | ✅ | `Makefile`の`runner-bundle`ターゲットの呼び出しをPython版（`source_hash()`）に置き換える。`scripts/xcuitest-runner-hash.sh`本体の削除は、`scripts/serve.sh`がまだ参照しているため手順8へ後ろ倒しする | `Makefile` | macOS上で`make runner-bundle`を実行し、`build-info.json`の`sourceHash`が従来と同じ値になる | 1 |
| 4 | ✅ | `ensure_bundled_runner_fresh()`を実装する。`subprocess.run`をモックし、鮮度一致時は何もしない、不一致時はビルドを呼ぶ、ツール欠如時はエラーになる、の3経路をテストする | `bajutsu/common/platform_lifecycle/environments/_bundled_runner.py` | ユニットテストが通る | 1, 2 |
| 5 | ✅ | 並行呼び出しのテストを追加する。2スレッドから同時に`ensure_bundled_runner_fresh()`を呼び、モックした`subprocess.run`の呼び出し回数が1回であることを確認する | 同上 | ユニットテストが通る | 4 |
| 6 | ✅ | `_resolve_runner`のbundled tierから`ensure_bundled_runner_fresh()`を呼ぶ。既存の`_resolve_runner`のテストに、鮮度判定が呼ばれることの確認を足す | `bajutsu/common/platform_lifecycle/environments/xcuitest/_functions.py`、対応するテスト | ユニットテストが通る | 4 |
| 7 | ✅ | `xcuitest_runner_summary`に鮮度の注記を追加する | `bajutsu/cli/commands/doctor.py`、対応するテスト | ユニットテストが通る | 4 |
| 8 | ✅ | `scripts/serve.sh`のbashロジックを`ensure_bundled_runner_fresh()`の呼び出しに置き換える。これで`scripts/xcuitest-runner-hash.sh`の呼び出し元がなくなるため、本体を削除する | `scripts/serve.sh`、`scripts/xcuitest-runner-hash.sh` | macOS上で`make serve`を実行し、初回はビルドが走り、2回目以降は走らないことを目視で確認する | 6 |
| 9 | ✅ | `docs/architecture.md`とそのja版のRunner解決の記述を更新する。`docs/ai-development.md`はbundled runnerに触れていないため対象外 | `docs/architecture.md`、`docs/ja/architecture.md` | 記述が現在の挙動と一致する | 8 |
| 10 | ✅ | `make check`を実行し、E2E CI（`ios-e2e.yml`）がすでに`make runner-bundle`を明示実行しているため、この変更が追加の待ちを生まないことを確認する | — | `make check`が通る | 9 |
