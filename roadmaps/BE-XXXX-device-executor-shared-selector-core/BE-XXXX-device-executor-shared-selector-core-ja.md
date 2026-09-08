[English](BE-XXXX-device-executor-shared-selector-core.md) · **日本語**

# BE-XXXX — RustとUniFFIで、iOSとAndroidの端末側セレクタコアを共有する

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-device-executor-shared-selector-core-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | Platform support |
| 関連 | [BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)、[BE-0208](../BE-0208-android-emulator-e2e-ci/BE-0208-android-emulator-e2e-ci-ja.md)、[BE-0238](../BE-0238-ios-device-cloud-execution/BE-0238-ios-device-cloud-execution-ja.md)、[BE-0405](../BE-0405-android-identifiertool/BE-0405-android-identifiertool-ja.md)、[BE-0407](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)、[BE-0408](../BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol-ja.md)、[BE-0409](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md)、[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md) |
<!-- /BE-METADATA -->

## はじめに

[BE-0408](../BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol-ja.md)
は、iOSとAndroid向けの端末側ステップ実行プロトコルを定義しています。BE-0408は、SwiftとKotlinがそれぞれ
独自にホスト側のセレクタ照合ロジックを持つ必要があると述べています。さらに、2つの実装がホスト側と
まったく同じ結果を返す必要があるとも述べています。本項目は、このロジックをRustで一度だけ書くことを提案します。両プラット
フォームは、[UniFFI](https://mozilla.github.io/uniffi-rs/)が生成するバインディング経由でこれを呼び出し
ます。手書きのSwift移植と手書きのKotlin移植の代わりに、1つのコンパイル済みコアを囲む2つの薄いバインディ
ングを置きます。
[BE-0409](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md)の
iOS実行エンジンと
[BE-0410](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md)の
Android実行エンジンは、それぞれ独自に書いた`matches`、`find_all`、`resolve_unique`を持つ代わりに、同じ
クレートを呼び出すことになります。

## 動機

BE-0408自身の設計は、リスクを明確に名指ししています。端末側の2つの実装は、「ホスト側の実装と同じ要素に
すべてのセレクタを解決」しなければなりません。さらに、「あいまいな一致に対しても同じように失敗」しなけれ
ばなりません。BE-0409とBE-0410は、順序付けでこのリスクに対応しています。iOS側の移植を先に行い、「この
移植が明らかにするギャップを、両プラットフォームが個別に再発見しなくて済むように」する設計です。この順序
付けは、ギャップを再発見するコストを下げます。しかし、2つの移植が最初から食い違うこと自体は防ぎません。
どちらの項目も、`find_all`／`resolve_unique`の移植をまだ始めていません。BE-0409はBE-0408の完了を待って
おり、BE-0410はBE-0409の完了を待っています。関連するSwiftのコードは、すでに1つ存在します。
[`BajutsuKit/Sources/BajutsuRunner/PositionPath.swift`](../../BajutsuKit/Sources/BajutsuRunner/PositionPath.swift)
の`resolvableMatchingIndex`です。これは、`_collapse_identical_duplicates`のランナー側の双子であり、
今日はコメントによる手動の同期でホスト側と揃えています。詳細設計では、これも共有クレートへ畳み込みます。
この1関数を除けば、SwiftのセレクタコードもKotlinのセレクタコードも、今日の時点でまだ存在しません。
だからこそ今は、1つの実装が2つの実装より安く済む時点です。

本項目が移す関数は、すでに純粋なデータ変換です。プラットフォーム固有の配線ではありません。
[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)の
`matches`、`find_all`、`resolve_unique`、`_collapse_identical_duplicates`は、`Element`のリストと
`Selector`を受け取ります。どちらも、文字列・リスト・タプルだけの単純な辞書です。各関数は、真偽値か、
絞り込んだリストか、単一の要素か、送出したエラーのいずれかを返します。この4つの関数は、アクセシビリティツリーを
読みません。タップも注入しません。ソケットも開きません。プラットフォーム固有の処理は、すべてこの関数の
外側で起きています。今日はPythonドライバの中で、実装後は両方の端末実行エンジンの中でです。プラット
フォームに依存しない関数が、独立に保守された3つのコピーとして存在する理由はありません。

独自に移植したときのリスクは、ふつうの実装ズレより深刻です。`idMatches`はPythonの
`fnmatch.fnmatchcase`を使います。`labelMatches`はPythonの`re.compile(...).search`を使います。独自の
Swift移植は`NSRegularExpression`とFoundation自身のglob処理に頼るでしょう。独自のKotlin移植は
`java.util.regex`とその独自の挙動に頼るでしょう。3つのエンジンが、シナリオ作者自身のパターンが何に
一致するかを、それぞれ別のルールで決めることになります。文字クラス、アンカリング、Unicodeプロパティの
扱いは、エンジンごとに違います。ホストでは通るのに端末実行エンジンでは落ちるセレクタは、大きなエラーで
はなく不安定なテストとして表面化します。別の要素に一致してしまう場合も同様です。誤った一致は、呼び出し
側から見て正しい一致と区別がつきません。Rustのエンジンを1つ共有すれば、この数は独立した3エンジンから
2エンジンへ減ります。ホスト側ではPythonの`re`と`fnmatch`が引き続き検証済みの基準であり続けます。Rustコア
は、端末実行エンジンが走らせるもう1つのエンジンになります。

実装が終われば、後の読者はこの結果を直接確かめられます。
[BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)のドライバ適合
スイートは、1つのコンパイル済みセレクタコアに対してフィクスチャ一式を実行します。現行の計画では、Swift
とKotlinそれぞれの移植に対して、別々に実行することになります。それぞれの移植は同じフィクスチャに通り
ながら、スイートが網羅していないケースで互いに食い違う可能性があります。新しいセレクタ規則（新しい
trait、新しいフォールバック）を追加するときの手間も変わります。共有コアなら、1回のRustの変更を
両方の実行エンジンが次のバイナリ更新で拾います。現行の計画では、記憶だけを頼りに歩調を合わせる、2回の
手書きの変更が必要です。

## 詳細設計

**実装順序。** 本項目は、BE-0407→BE-0408→BE-0409→BE-0410という4項目の並びを拡張します。BE-0408自身の
進捗チェックリストは、本項目が置き換える手順を記載しています。「`find_all`／`resolve_unique`のセレクタ意味論
を、2つの独立した実装が一致できるだけ精密な共有設計文書に落とし込む」という手順です。本項目は、この文書
の代わりにコンパイル済みクレートを用意します。着手のタイミングは、BE-0408がフィールドレベルのセレクタ
契約（`within`、`idMatches`、traitの導出）を確定させたあとです。BE-0409またはBE-0410がプラットフォーム側
の照合コードを書き始める前に着手します。本項目が着地すると、BE-0409とBE-0410が互いに順序付けている理由
も消えます。両者とも同じ検証済みのクレートを呼ぶだけになるため、どちらかの手書き移植を先に待つ必要が
なくなります。本項目のクレートと2つのバインディングができたあとは、BE-0409とBE-0410はどちらの順で進め
ても、並行に進めてもかまいません。

**クレートで実装し直す関数と、ホスト側だけに残す関数。**
[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)の
9つの関数を、Rustで実装し直します。Pythonの実装は、適合スイートの基準としてそのまま残ります。対象は
`matches`、`find_all`、`resolve_unique`、`_collapse_identical_duplicates`、`contains`、
`topmost_at_point`、`redirect_candidates`、`raise_if_covered`、`frame_center`です。これらは、セレクタ
解決と、BE-0408が端末へ移すアクチュエーション種別の1つである`tap`の被覆判定をカバーします。動機の節で
示したとおり、各関数は純粋です。`Element`と`Selector`の組（またはそのリスト）を受け取り、真偽値・
インデックス・座標・送出したエラーのいずれかを返します。

FFI（foreign function interface）境界を越えること自体が理由で、シグネチャが2箇所変わります。Python
のオブジェクト同一性には、境界の向こう側に対応物がないためです。1つ目は、`find_all`が`Element`の
リストの代わりに`Vec<u32>`（`elements`の中でのインデックス）を返し、`resolve_unique`が`Element`の
代わりに`u32`を1つ返す変更です。UniFFIのレコードはこの境界を値として越えるため、返された`Element`は
コピーにすぎず、呼び出し元がそこから解決した先のプラットフォーム側ハンドル（`XCUIElement`や
`AccessibilityNodeInfo`）へたどる手がかりを持ちません。インデックスであれば、呼び出し元は自分が組み
立てたリストから、`Element`と自分自身のハンドルの両方を同じ位置で引けます。2つ目は、`topmost_at_point`、
`redirect_candidates`、`raise_if_covered`が、`Element`の代わりに`target_index: u32`を受け取る変更
です。理由は同じです。Pythonは`target`引数を`elements`の中からオブジェクト同一性（`is`）で探して
います。等価性では探していません。これは意図的な設計です。内容が同一の2要素（既知のXCUITestの重複
登録）があっても、呼び出し元が実際に手にしている一方だけを指し続ける必要があるためです。インデックス
はこの区別を保ちますが、値としてコピーされたレコードはこの区別を保てません。

`gesture_anchor`も同じく純粋ですが、本項目の範囲外です。BE-0408が端末へ移すのは`tap`、`type`、`swipe`、
`scroll`であり、`gesture_anchor`が支点を計算する2本指の`pinch`／`rotate`ではありません。この関数を今
移植すると、本項目のプロトコルがまだ到達していない段階のための実装になってしまいます。

`deadline_ticks`と`wait_until`も移しません。どちらも、単発の判定の周りにホスト側のポーリングループを
実装したものです。BE-0408のステージ1は、ホストにポーリングの手段を公開する代わりに、端末側で内部的に
ポーリングさせる設計です。端末実行エンジンに必要なのは、共有した照合関数を包む、プラットフォームごとの
イベント駆動またはタイマー駆動のループです。ホストのポーリングループをそのまま移植したものではありませ
ん。すべてのバックエンドの`wait_for`が委ねる単発判定`default_wait_for`にも、同じ理由から個別の移植は
要りません。この関数の中身は`find_all(...).len() >= 1`そのものであり、共有した`find_all`に対して各
実行エンジン自身のネイティブなループが直接この判定を表現できます。`id_candidates`、
`validate_id_candidates`、`permission_capability`、`native_z_from_json`もPythonに残ります。
`id_candidates`が残る理由はデータモデルの節で述べます。残る3つの理由はもっと単純です。これらは、
シナリオの記述やエビデンスの解析といった、端末実行エンジンが担わない作業に使うためです。

**データモデル。** [`Element`](../../bajutsu/common/drivers/base/element.py)は、フィールドごとに
UniFFIの辞書型レコードになります。`identifier`、`label`、`value`はオプショナルな文字列に、`traits`
は文字列のリストに、`frame`は`(x, y, w, h)`の4フィールドのレコードに、`nativeZ`はオプショナルな浮動
小数点数になります。[`Selector`](../../bajutsu/common/drivers/base/selector.py)は、単純な改名だけ
では済みません。`id`と`idMatches`は、Pythonでは単一の文字列かリストのどちらも受け取ります
（`str | list[str]`、BE-0221のOR候補形式）。UniFFIにはこの種の合併型がないため、レコードの境界では
どちらも`Option<Vec<String>>`になります。フィールドが不在なら`None`です。これはPython自身のフィールド
存在チェック（`"id" in sel`）と対応し、空リストを不在の代わりに使うわけではありません。単一の値を
1要素のリストへ包むのは1行で済む作業であり、わざわざ
移植する価値はありません。そのため各呼び出し元がこの処理を済ませます。今日同じ処理を担う
Pythonのヘルパー`id_candidates`は、クレートへ移さずホスト側に残る理由がここにあります。クレート内部
の`matches`と`find_all`は、すでに正規化されたリストだけを見ます。`within`は、`Selector`が自分自身の
`within`フィールドの中に入れ子になりうるため、`Option<Box<Selector>>`になります。`index`は`u32`では
なく`Option<i32>`になります。Pythonでは末尾からの位置を表す負の値を受け付けるためです
（`_functions.py:322-325`）。Pythonの`total=False`な辞書でのフィールドの不在は、両側で同じ`None`
になります。

[`Trait`](../../bajutsu/common/drivers/base/trait.py)の6つの文字列定数、`button`、`link`、
`notEnabled`、`selected`、`other`、`secureTextField`は、両側でそのまま文字列として渡ります。これは、
PythonのコードとJavaScript object notation（JSON）のワイヤフォーマットがすでに使っている形と一致します。
そのため、7つ目の定数が加わっても、歩調を合わせる新しい列挙型は不要です。
[`ElementNotFound`](../../bajutsu/common/drivers/base/element_not_found.py)、
[`AmbiguousSelector`](../../bajutsu/common/drivers/base/ambiguous_selector.py)、
[`ElementNotTappable`](../../bajutsu/common/drivers/base/element_not_tappable.py)は、3つのバリアントを
持つ1つのUniFFIエラー列挙型になります。各バリアントは、整形済みのメッセージ文字列ではなく、セレクタ・
候補数・被覆した要素の識別子とフレームといった、構造化された失敗の詳細を持ちます。この詳細を、今日
実行レポートが表示するメッセージ文へ整形するのはホスト側であり、デバイス側ではありません
（[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)の
`resolve_unique`と`raise_if_covered`）。SwiftやKotlinの呼び出し元は、整形前のバリアントをそのまま既存のエビデ
ンス経路へ渡すため、端末実行エンジンで失敗したステップは、今日ホストで失敗した同じステップとまった
く同じ見え方になります。

`_collapse_identical_duplicates`には、ホスト側の実装にはない引数を1つ加えます。`frame_tolerance: f64`
です。デフォルト値はゼロです。2つの候補のフレームがどれだけ近ければ同じ内容として数えるかを決める値
です。ホスト側は常に1回の原子的なスナップショットに対してこれを呼ぶため、本物の重複登録が報告する
フレームは厳密に一致します。
[`PositionPath.swift`](../../BajutsuKit/Sources/BajutsuRunner/PositionPath.swift)の
`resolvableMatchingIndex`は、これとは違う許容差を必要とします。記録済みの要素ハンドルを、時間差の
あるライブ呼び出し1回ずつで候補ごとに再解決する場面だからです。さらに、この関数が行っていない2つの
ことも行っています。記録済みハンドル自身の属性で候補をまず絞り込む処理と、生き残った候補どうしが
食い違えば1つのグループではなく解決失敗として扱う処理です。共有するのはフレーム照合とグルーピングの
ロジックだけであり、それを取り巻く契約までは共有しません。この許容差を引数として公開すれば、
`resolvableMatchingIndex`は薄いラッパーになれます。自前の記録済み属性フィルタを先に走らせ、残った
候補を共有関数がグルーピングし、既存の「食い違えばnil」判定をその結果に適用する形です。

Androidの派生ラベルのフォールバック（`_derived_label`。
[`bajutsu/common/drivers/adb/_functions.py`](../../bajutsu/common/drivers/adb/_functions.py)にあり、
`_to_element`の中で適用）は、パイプライン中の現在の位置にそのまま留まります。共有した照合コードが読む
前に、`Element`へラベルを計算して
おく処理です。これは、今日のPythonドライバでも、BE-0410実装後の`BajutsuAndroidUIAutomatorServer`の
Kotlin側呼び出し元でも同じです。共有クレート側にAndroid固有の分岐は不要です。呼び出し側がそれぞれ、
自分のプラットフォームの生の読み取り結果を素の`Element`へ正規化してから、1つの共有コアを呼ぶという
構造だからです。ここには、手書きのKotlin移植が1つ残ります。`_derived_label`自体にはRust側の対応物が
ないため、Pythonの実装と歩調を合わせ続ける必要があります。その出力は後続処理のない単一の文字列で
あり、BE-0114のフィクスチャがすでにこれをカバーしています。この残存リスクは、照合パス全体を独立に
移植していた場合よりはるかに小さく済みます。

**iOS: `BajutsuRunner`。** [`BajutsuKit/Package.swift`](../../BajutsuKit/Package.swift)は、すでに
Swift Package Managerのビルドプラグイン`OpenAPIGenerator`を使い、`BajutsuRunner`のソースをビルド
するたびに、どのホストでも生成しています。`uniffi-bindgen`が生成するSwiftファイルは、これとは別の
もう1つのソース生成経路です。違いは1点です。ネイティブ側の実体が、プラグインの都度コンパイルではなく、
あらかじめビルド済みの`.xcframework`成果物である点です。`cargo build`の対象は、Simulator向けの
`aarch64-apple-ios-sim`と`x86_64-apple-ios`、[BE-0238](../BE-0238-ios-device-cloud-execution/BE-0238-ios-device-cloud-execution-ja.md)
の実機対応向けの`aarch64-apple-ios`、そして
[`swift.yml`](../../.github/workflows/swift.yml)のSimulatorを使わない素のApple Silicon macOSランナー
（`swift build --package-path BajutsuKit`と`swift test --package-path BajutsuKit`）が今日どおりビルド・
テストを続けられるようにする`aarch64-apple-darwin`です。`uniffi-bindgen`は、Swiftバインディングと、
この4つの`cargo build`成果物を統合した`.xcframework`（2つのSimulatorターゲットは1つのユニバーサル
スライスへまとまるため、実質3系統のプラットフォームスライス）を生成します。それを`Package.swift`に
バイナリターゲットとして追加し、
`BajutsuRunner`はそれに依存します。`BajutsuRunner`は、bajutsu自身が同梱するテストランナーです。
[BE-0292](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner-ja.md)のコンテンツハッシュ
方式のキャッシュを通じて、開発者の手元にはビルド済みの状態で届きます。利用側プロジェクトのビルド内で
コンパイルされることはありません。したがって、このビルド手順が走るのはbajutsu自身のリリースパイプライン
の中だけです。テスト対象アプリ自身のビルドの中では走りません。これは、アプリ組み込みライブラリのター
ゲットである`BajutsuKit`を、この手順から自由に保っているのと同じ境界です。

**Android: `BajutsuAndroidUIAutomatorServer`。**
[`BajutsuAndroidUIAutomatorServer/server/build.gradle.kts`](../../BajutsuAndroidUIAutomatorServer/server/build.gradle.kts)
は、この実行エンジンが拡張するのと同じインストルメンテーションのために、すでに`androidx.test.uiautomator`
に依存しています。このモジュールにネイティブの依存を加えても、増えるのは依存の「種類」です。依存を
許容する度合いを新たに広げるわけではありません。ただし、これはモジュールが届く範囲そのものへの変更
でもあります。このインストルメンテーションAPKは今日ネイティブコードを持たないため、`minSdk = 26`が
まだ許している32ビットの`armeabi-v7a`や`x86`を含め、端末が提供するどのABI（application binary
interface）にもインストールできます。`cargo-ndk`は、`arm64-v8a`と、
[BE-0208](../BE-0208-android-emulator-e2e-ci/BE-0208-android-emulator-e2e-ci-ja.md)のエミュレータレーン
向けの`x86_64`へクレートをクロスコンパイルします。これは、この範囲を初めて狭める変更です。32ビット
端末は、常駐サーバをもう実行できなくなります。本項目は、4つ全部のABI向けにビルドするのではなく、
この狭まりを受け入れます。32ビットのみのAndroid端末は、2019年以降のPlayストアがアプリから受け付け
なくなった範囲にすでに入っており、常駐サーバ自身の端末カバレッジは、今日実際のターゲットアプリが配布
できる範囲に揃うことになります。`cargo-ndk`が生成した`.so`ファイルは`jniLibs`の下に置きます。
`uniffi-bindgen`は、実行エンジンが直接呼ぶKotlinバインディングを生成します。このビルドファイル自身
のコメントは、サーバが
「dependency-light（依存を軽く保つ）」だとすでに述べています。理由は、HTTPとJSONのどちらのライブラリも
持たない、自己完結したインストルメンテーションだからです。これは、不要な依存を避けるという方針の表明
です。この実行エンジンが実際に必要とするネイティブの依存を禁じるものではありません。

**検証。** BE-0114の適合スイートは、プラットフォームのバインディングを経由せず、クレートを直接呼ぶ
フィクスチャ実行の経路を新たに持ちます。CIホスト自身のアーキテクチャ向けにビルドした、小さなRustの
バイナリです。wheelと常駐サーバのどちらにも同梱しません。標準入力からフィクスチャの`Element`リストと
`Selector`をJSONで読み、一致したインデックス、またはエラーのバリアントとその構造化された詳細を標準
出力へ書きます。既存のフィクスチャは、これで1つの成果物に
対して3つの層を検証することになります。クレート自身のRustユニットテスト、このCLI経由のフィクスチャ実行、
そしてBE-0409とBE-0410が実装されたあとの、各プラットフォームのバインディング経由での同じフィクスチャ
実行です。どちらかのプラットフォームバインディングでフィクスチャが落ちたときは、共有ロジック自体を疑い
直す前に、まず「バインディング側」だと絞り込めます。

## 検討した代替案

- **BE-0408の現行案を維持する。共有設計文書と、独立に書いたSwift・Kotlinの2つの移植を、適合スイートだけ
  で検証する案。** 唯一の安全策としては採用しません。BE-0408自身がすでに名指ししているリスクは残ります。
  2つの独立した実装が、あいまいな一致でどの候補を報告するかまで含めて完全に一致しなければならない、と
  いうリスクです。このリスクは、設計で取り除かれないまま残ります。今後セレクタ規則を追加するたびに、
  テストの失敗という事後の発見だけを頼りに、2つの手書きパッチの歩調を合わせる必要があります。
- **同じRustコアをPyO3経由でPythonにも広げ、3言語を1つの実装にまとめる案。** 採用しません。`bajutsu`の
  pipパッケージは、今日は純粋なPythonです。AI SDKとPlaywrightを基本の依存にせず、オプトインの拡張に
  とどめる方針をすでに取っています
  （[BE-0111](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency-ja.md)）。
  基本インストールへネイティブ拡張を加えると、`pip install bajutsu`のたびにクロスプラットフォームの
  wheelビルドが必要になります。[maturin](https://github.com/PyO3/maturin)のようなツールが、そのビルド
  を担います。このビルドは、上記のiOS・Androidのビルドとは違い、bajutsu自身のリリースパイプラインの
  中だけでなく、インストールのたびに走ります。Pythonの実装は、すでに適合スイートがRustコアを照合する
  検証済みの基準です。本項目の動機は、Python側を変える理由になりません。
- **同じRustコアを、BajutsuKitとBajutsuAndroidのアプリ組み込みコレクタ（`BajutsuNet`、`BajutsuZOrder`、
  クリップボードのレシーバ）にも広げる案。** 採用しません。これらのコンポーネントのプラットフォームフック
  機構は、収集先へPOSTするJSONペイロードの形という薄い契約以外に、共有できるロジックを持ちません。片方は
  `URLProtocol`のswizzling、もう片方はOkHttpの`Interceptor`です。片方はループバックのHTTPサーバ、もう
  片方は`AccessibilityNodeInfo`のextra-dataです。ここに共有Rustコアを持ち込んでも、置き換わるのはその
  薄い契約だけです。双方でゼロからのプラットフォーム固有実装が引き続き必要になります。`BajutsuRunner`と
  `BajutsuAndroidUIAutomatorServer`はbajutsu自身のテスト基盤として動きますが、これらのライブラリはテスト
  対象アプリの中に同梱されます。
  [BE-0405](../BE-0405-android-identifiertool/BE-0405-android-identifiertool-ja.md)は、そこに置く
  `IdentifierTool`を、依存を持たない最小フットプリントの設計にすでにコミットしています。同梱したRustの
  静的ライブラリは、その設計と噛み合いません。
- **1つの仕様言語からSwiftとKotlinの同等なソースを生成する案。両プラットフォームがリンクする1つのネイ
  ティブライブラリをコンパイルする代わりに。** 採用しません。独立にコンパイルされた2つの生成コードは、
  言語ごとのコード生成バックエンドがそれぞれ固有のバグを抱えれば、それでも食い違いえます。これは、本項目
  がなくそうとしている失敗のパターンそのものです。このリポジトリには、この水準のコード生成バックエンド
  の前例がありません。一方UniFFIは、Rustのコアを1つ用意し、プラットフォームごとにホスト言語のバインディ
  ングを生成する形のために存在するツールです。しかも、保守が続いています。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] `rust/selector-core/`にクレートの雛形を用意します。`Element`、`Selector`、`Trait`をUniFFIレコード
  として、3つのセレクタ関連エラーを1つのUniFFIエラー列挙型として、それぞれ用意します。
- [ ] [`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)から、
  9つのセレクタ・幾何関数を移植します。`find_all`は`Vec<u32>`を、`resolve_unique`は`u32`を（いずれも
  呼び出し元の`elements`へのインデックス）、`topmost_at_point`・`redirect_candidates`・
  `raise_if_covered`は`Element`の代わりに`target_index: u32`を、`_collapse_identical_duplicates`は
  `frame_tolerance: f64`を、それぞれ返す・受け取るよう変更します。
  - `matches`
  - `find_all`
  - `resolve_unique`
  - `_collapse_identical_duplicates`
  - `contains`
  - `topmost_at_point`
  - `redirect_candidates`
  - `raise_if_covered`
  - `frame_center`
- [ ] CLI形式の適合ランナーバイナリを構築します。
  [BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)のフィクスチャ
  スイートが、これを直接呼べるように拡張します。
- [ ] `cargo`と`uniffi-bindgen`を`BajutsuKit`のSwift Packageビルドに組み込みます。`BajutsuRunner`が
  リンクする`.xcframework`（Simulator、実機、macOS向けの4つの`cargo build`成果物を統合した、実質3系統
  のプラットフォームスライス）バイナリターゲットを生成します。
  [`PositionPath.swift`](../../BajutsuKit/Sources/BajutsuRunner/PositionPath.swift)の
  `resolvableMatchingIndex`は、共有グルーピング関数を呼ぶ薄いラッパーへ縮小し、`framesEqual`は廃止
  します。
- [ ] `cargo-ndk`と`uniffi-bindgen`を`BajutsuAndroidUIAutomatorServer`のGradleビルドに組み込みます。
  実行エンジンがリンクする、Kotlinバインディングと`arm64-v8a`／`x86_64`向け`jniLibs`を生成します。
- [ ] 共有する関数が不要にする、手動同期の契約コメントを更新します。
  [`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)の
  `_collapse_identical_duplicates`にある「ランナー側の双子」というコメントと、
  [`PositionPath.swift`](../../BajutsuKit/Sources/BajutsuRunner/PositionPath.swift)の
  `resolvableMatchingIndex`と`RecordedAttributes`にある対応するコメントです。
- [ ] `rust/selector-core/`向けにRustのCIレーン（`cargo test`、`cargo fmt --check`、`clippy`）を追加し、
  `make check`が直接これを呼ぶか、別のワークフローに任せるかを決めます。
- [ ] BE-0408の進捗チェックリストと、BE-0409・BE-0410の「Swift／Kotlinへ移植する」手順を、コンパイル済み
  バインディングを呼ぶ形に更新します。BE-0410の派生ラベル移植は、`_derived_label`が共有コアより手前で
  正規化を行うため、独立したステップとして残します。あわせて、iOS側移植を先に行うという順序付けを、
  BE-0409の詳細設計と、BE-0410の実装順序・「順序ステータス」の両方から取り除きます。BE-0409の
  「順序ステータス」はBE-0408ではなく本項目を指すよう、BE-0410の「順序ステータス」はBE-0409ではなく
  本項目を指すよう、それぞれ付け替えます。どちらも、互いの完了順ではなく本項目のクレートに依存する
  ためです。
- [ ] `roadmap-id`ワークフローがmain上で本項目のIDを割り当てたら、BE-0408・BE-0409・BE-0410へ相互の
  「関連」リンクを反映します。

## 参考

[BE-0111 — AI SDKをオプトインの依存にする](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency-ja.md)、
[BE-0407 — 証拠読み取りの重複排除とドライバ内部の調整によるステップ実行の高速化](../BE-0407-step-latency-driver-internal-tuning/BE-0407-step-latency-driver-internal-tuning-ja.md)、
[BE-0114 — backend 非依存の挙動を検査する driver conformance suite](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)、
[BE-0208 — AndroidエミュレータのCI](../BE-0208-android-emulator-e2e-ci/BE-0208-android-emulator-e2e-ci-ja.md)、
[BE-0238 — iOS端末クラウド実行](../BE-0238-ios-device-cloud-execution/BE-0238-ios-device-cloud-execution-ja.md)、
[BE-0292 — XCUITestの同梱ランナー](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner-ja.md)、
[BE-0405 — Android向けIdentifierTool](../BE-0405-android-identifiertool/BE-0405-android-identifiertool-ja.md)、
[BE-0408 — ステップレイテンシのための端末側実行プロトコル](../BE-0408-step-latency-device-executor-protocol/BE-0408-step-latency-device-executor-protocol-ja.md)、
[BE-0409 — XCTest ランナー内の iOS 端末側ステップ実行機](../BE-0409-step-latency-ios-device-executor/BE-0409-step-latency-ios-device-executor-ja.md)、
[BE-0410 — Androidの端末側ステップ実行エンジン](../BE-0410-step-latency-android-device-executor/BE-0410-step-latency-android-device-executor-ja.md)、
[`bajutsu/common/drivers/base/_functions.py`](../../bajutsu/common/drivers/base/_functions.py)、
[`bajutsu/common/drivers/adb/_functions.py`](../../bajutsu/common/drivers/adb/_functions.py)、
[`BajutsuKit/Sources/BajutsuRunner/PositionPath.swift`](../../BajutsuKit/Sources/BajutsuRunner/PositionPath.swift)、
[UniFFI](https://mozilla.github.io/uniffi-rs/)
