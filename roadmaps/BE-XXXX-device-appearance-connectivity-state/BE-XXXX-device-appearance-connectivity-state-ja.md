[English](BE-XXXX-device-appearance-connectivity-state.md) · **日本語**

# BE-XXXX — 端末状態のステップ：画面の向き、外観、機内モード

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-device-appearance-connectivity-state-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | シナリオ記述機能 |
| 関連 | [BE-0035](../BE-0035-device-control-primitives/BE-0035-device-control-primitives-ja.md), [BE-0052](../BE-0052-device-state-timezone-clipboard-shake/BE-0052-device-state-timezone-clipboard-shake-ja.md), [BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities-ja.md), [BE-0128](../BE-0128-device-step-capability-preflight/BE-0128-device-step-capability-preflight-ja.md), [BE-0029](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions-ja.md), [BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions-ja.md), [BE-0282](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage-ja.md) |
<!-- /BE-METADATA -->

## はじめに

端末状態のステップを 3 つ、まとめて提案します。`setOrientation`、`setAppearance`、
`setAirplaneMode` です。3 つとも同じ形をしているからです。どれも要素ツリーの外側で端末を変え、
どれも自分の `deviceControl.*` ケイパビリティトークンでゲートされ
（[BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities-ja.md)）、
どれもバックエンドごとに忠実な経路で実行されます。サポート行列は意図的に不揃いで、その不揃いさ
自体が要点です。iOS Simulator には無線がないので、機内モードのトークンを広告せず、プリフライトが
端末作業の前にそのシナリオを拒否します。

## 動機

横向きのレイアウト、ダークテーマ、オフラインの挙動を検証したいスイートは、いまその状態変化を表現
できません。そのため 3 つの流れは、このリポジトリのどのシナリオにも存在しません。

なかでもダークモードが要になります。要素スコープとマスクを備えた視覚回帰
（[BE-0029](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions-ja.md) と
[BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions-ja.md)）
は、このツールのもっとも強い保証の 1 つですが、比べられる外観はいつも 1 つだけです。端末をもう一方
の外観にする手段がないからです。機内モードは、オフライン試験の欠けた半分です。シナリオの `mocks`
はすでに*応答*をスタブできます
（[BE-0282](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage-ja.md)）。
しかし無線を切るステップがないので、アプリ自身の到達性判定や再試行の経路は、テストの下で一度も
走りません。

画面の向きが 3 つ目を埋めます。レイアウトへの影響範囲がもっとも広い状態変化であり、しかも問われる
ことのないまま壊れやすい状態変化でもあります。

これが入ると、読者はベースラインの対を指せるようになります。いまリポジトリには 2 つ目の外観の視覚
ベースラインが 1 枚もありません。どのシナリオもそこへ到達できないからです。この変更のあとは、
`data` に 2 行を持つ**1 つの**シナリオファイルが `home-light.png` と `home-dark.png` の 2 つの比較を
生み、その対がショーケースのベースラインディレクトリに置かれます。そこへ到達するのに新しい
アサーション種別は要りません。理由は後述します。

## 詳細設計

### 3 つのアクション

```ebnf
Action ::= …
  | { setOrientation:  { to: "portrait" | "landscape" } }
  | { setAppearance:   { to: "light" | "dark" } }
  | { setAirplaneMode: { enabled: boolean } }
```

`to:` は文としての読みに沿い、既存の単一ペイロードの端末ステップ（`setClipboard: { text }`、
`setLocation: { lat, lon }`）とも揃います。向きの語彙を 4 つではなく 2 つにするのは意図的です。
`landscapeLeft` と `landscapeRight` には web に忠実な対応物がなく、電話型のターゲットでは作成者から
見た違いもありません。この項目は可搬な 2 つを出荷し、4 値の是非は後述の論点に残します。

### 3 つの新しいケイパビリティトークン

`deviceControl.orientation`、`deviceControl.appearance`、`deviceControl.airplaneMode` を
`base.Capability` に加えます。既存の `DC_SET_LOCATION`、`DC_CLIPBOARD`、`DC_PUSH`、
`DC_CLEAR_KEYCHAIN`、`DC_APP_LIFECYCLE`、`DC_STATUS_BAR` の隣です
（`bajutsu/common/drivers/base.py:88-93`）。それぞれが `_DEVICE_CONTROL_OPS`
（`capability_preflight.py:163`）に 1 行ずつ増えます。ここはトークンとラベルと述語のデータ表なので、
プリフライト自体に新しい論理は要りません。

ここに小さく、見落としやすい編集が 1 つあります。`DEVICE_CONTROL_ALL`（`base.py:127`）は、xcuitest
ドライバが一族をまとめて広告するための集合です（`xcuitest.py:840`）。機内モードについては、この
近道を**壊す**必要があります。Simulator が実行できないからです。xcuitest が自分の部分集合を明示的に
並べるか、`DEVICE_CONTROL_ALL` を「simctl が支える端末が実行できる操作」と定義し直して、機内モードを
その外に置くかのどちらかです。

### サポート行列を正直に書く

| トークン | xcuitest | adb | playwright | fake |
|---|---|---|---|---|
| `deviceControl.orientation` | ✅ simctl ではなく常駐ランナー経由 | ✅ 加速度計の回転を無効化してから `user_rotation` を設定 | ✅ コンテキストのビューポート入れ替え | — |
| `deviceControl.appearance` | ✅ `simctl ui <udid> appearance light\|dark` | ✅ `cmd uimode night yes\|no` | ✅ コンテキストの `color_scheme` エミュレーション | — |
| `deviceControl.airplaneMode` | **—** Simulator に無線がない | ✅ `cmd connectivity airplane-mode enable\|disable` | ✅ コンテキストのオフライン切り替え | — |

この表の 2 行が設計を決めます。どちらも均してはいけません。

**iOS の向きは `simctl` の操作ではありません。** `xcrun simctl` に向きのサブコマンドはなく、
Simulator の画面の向きは `XCUIDevice.shared.orientation` で設定します。これは常駐する XCUITest
ランナーの側にあり、`handleSystemAlert` やピッカーホイールの対応と同じ場所です。4 つ目のトップレベル
トークンを作るのではなく、シナリオから見える概念は端末状態の一族に置いたままにします。これは
要素ツリーの外側で端末を変える操作だからです。そのうえで iOS のコントローラがランナーへ届くように
します。具体的には `Environment.controller(self, eff)`
（`bajutsu/common/platform_lifecycle/protocols.py:272`）を、起動済みのドライバを取る形に広げます。
`relauncher(self, eff, scenario, driver)`（`protocols.py:262`）がすでにそうしている前例があります。

**iOS Simulator は機内モードをまったく実行できません。** 無線がなく、`simctl` の面もなく、
`overrideStatusBar` のバーは見た目だけです。そこで `xcuitest` は機内モードのトークンを広告せず、
プリフライトが端末作業の前にそのシナリオを拒否します。メッセージには代替を書きます。シナリオの
`mocks` と `network` のフィルタで、iOS ではこれが唯一のオフライン経路です。何も広告せずに早く失敗
させることこそ、
[BE-0212](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities-ja.md)
の操作単位の分割が表現できるようにしたものです。

### web バックエンドが初めて `DeviceControl` を持つ

`WebEnvironment.controller` はいま `None` を返します。コメントは「ドライバがブラウザを所有しており、
simctl の端末制御はない」です（`environments/web.py:105-106`）。新しい `web_device_control(driver)`
ファクトリが、生きているドライバに束ねたコントロールを返します。3 つの新しい操作を実行し、
プロトコルの残りには `UnsupportedAction` を送出します。Android のコントローラがすでに使っている形
です。残りはプリフライトが事前に弾くので、この送出は黙った no-op ではなく最後の砦になります。この
項目でもっとも構造的な変更であり、独立した作業単位にします。

### 罠になるので、3 つの線を明示的に引く

- **`rotate` アクションは `setOrientation` ではありません。** `rotate: { sel, radians }` は
  `multiTouch` ケイパビリティの背後にある 2 本指のジェスチャで、要素の*内側*の内容（地図や写真）を
  回します
  （[BE-0232](../BE-0232-adb-multitouch-gestures/BE-0232-adb-multitouch-gestures-ja.md)）。
  `setOrientation` は端末の画面の向きを変え、アプリ全体を再レイアウトさせます。端末制御トークンの
  背後にあり、まったく別の経路を通ります。英語の語が同じだけで、共有するコードはありません。
- **`serve` のテーマ機構は `setAppearance` ではありません。**
  [BE-0191](../BE-0191-pluggable-theme-system-serve-ui/BE-0191-pluggable-theme-system-serve-ui-ja.md)
  は Bajutsu の Web UI 自身のライトとダークのテーマで、運用者が見るブラウザの外装です。
  `setAppearance` は、端末上のテスト対象アプリの外観を設定します。重なりはありません。
- **`overrideStatusBar` のバーは接続性ではありません。** `wifiBars` と `cellularBars`
  （[BE-0035](../BE-0035-device-control-primitives/BE-0035-device-control-primitives-ja.md)）は、
  スクリーンショットを安定させるためにシミュレータのステータスバーを描き替えます。無線には触れず、
  アプリの通信は成功したままです。オフラインの挙動を試そうとして `wifiBars: 0` に手を伸ばすのが
  典型的な誤りで、オフラインのバナーをアサートしても一度も現れないシナリオができあがります。

### 外観のアサーション種別は追加しません

外観のアサーションは端末の設定を読むことになります。`setAppearance` の直後では、それはほぼ同語反復
であり、アプリが追随したかどうかを何も言いません。作成者が本当に主張したいのは「この画面がダーク
テーマで描かれている」ことであり、文法はすでに 2 通りでそこへ届きます。外観ごとのベースラインに
対する `visual` アサーション（BE-0171 以降は要素スコープが使えます）か、テーマが変えるものに対する
通常の `exists` や `selected` や `label` のアサーションです。

隠さずに挙げておくべき先例があります。`clipboard`
（`bajutsu/common/scenario/models/assertions.py:250`）は同じ制御チャネルで端末の状態を読み戻すもので、
これは受け入れられています。ですから「画面ではなく端末を読む」ことは、それだけでは種別を退ける理由に
なりません。要素ツリーにもネットワークにも解決しない種別は、すでに 6 つあります
（[selectors](../../docs/ja/selectors.md)）。`appearance` が `clipboard` と違うのは、クリップボードの
中身はテストが主張したいことそのものであるのに対し、外観の読み戻しは直前の `setAppearance` を
言い直すだけだという点です。反対の理由は同語反復だけです。外観をまたぐ組み合わせは、新しい文法なしに
合成から出てきます。

```yaml
- name: home renders in both appearances
  data: [{ appearance: light }, { appearance: dark }]
  before:
    - setAppearance: { to: "${row.appearance}" }
  steps:
    - wait: { for: { id: home.title }, timeout: 5 }
  expect:
    - visual: { baseline: "home-${row.appearance}.png", element: { id: home.card } }
```

データ展開は `${row.*}` をシナリオ全体に補間するので
（[BE-0031](../BE-0031-data-driven-scenarios/BE-0031-data-driven-scenarios-ja.md)）、ステップの
ペイロードもベースラインのファイル名も、いまのままで賄えます。1 ファイル、2 ベースライン、新しい
機構なしです。

### 固定 sleep を置かずに落ち着かせる

向きと外観はレイアウトを変えるので、次の `query()` がまだ古いツリーを返すことがあります。ハンドラは
sleep を**しません**。変更を実行してから、端末自身の読み戻しを有界な期限までポーリングします。条件
待ちがすでに共有している期限とバックオフの骨組みをそのまま使います。`simctl ui <udid> appearance` は
引数なしで現在値を印字し、Android では `cmd uimode night` が印字し、ブラウザのコンテキストは直接
答えます。

限界は `scroll` が物理を述べるのと同じように書きます。ハンドラが待つのは、**端末**が新しい状態を
報告することです。**アプリ**が再レイアウトを終えたかどうかは作成者の領分で、通常の
`wait: { for: … }` で待ちます。ここに sleep の言い換えはありません。

### 作業分解（MECE）

1. **文法とトークン**です。3 つのアクション、3 つの `Capability` メンバ、`DEVICE_CONTROL_ALL` の
   訂正、`_DEVICE_CONTROL_OPS` の 3 行、そして DSL 文法と英語版を書きます。
2. **プロトコルの拡張**です。`DeviceControl` の 3 メソッドと、`controller(eff)` から
   `controller(eff, driver)` への変更を `protocols.py` と全環境に通し、唯一の呼び出し箇所も直します。
3. **iOS** です。`simctl ui appearance` の設定と読み戻し、常駐ランナー経由の向き（チャネルメッセージ
   込み）、そして機内モードを意図的に広告せず、プリフライトのメッセージで `mocks` を案内します。
4. **Android** です。3 つの `adb` コマンド構築と読み戻しを実装します。`user_rotation` を設定する前に
   加速度計の回転を無効化することも含みます。
5. **web** です。`web_device_control(driver)` ファクトリ、それを返す `WebEnvironment.controller`、
   Playwright ドライバ上の 3 操作を実装します。
6. **落ち着きの条件**です。有界な読み戻しポーリングと、「端末は落ち着いた、アプリは必ずしもそうでは
   ない」という限界の明記を行います。
7. **ドキュメントとフィクスチャ**です。[drivers](../../docs/ja/drivers.md) のケイパビリティ表、
   [scenarios](../../docs/ja/scenarios.md)、上の 3 つの線引き、2 行の外観比較ショーケースシナリオと
   ベースラインの対、そして英語版を書きます。
8. **実機での検証**です。iOS、Android、web の各 end-to-end ワークフローに 1 シナリオずつ入れます。

### prime directive との整合性

- **run の経路にモデルを置きません。** どの操作も端末へのコマンドと、その答えの読み戻しです。合否は
  引き続き機械判定のアサーションだけが決めます。
- **決定性**です。固定 sleep は置かず、落ち着きは端末自身が報告する状態への有界なポーリングです。
  実行できないバックエンドは、途中で失敗するのではなくプリフライトで失敗します。
- **アプリ非依存**です。ステップはどのターゲットでも同一で、バックエンドごとの差はケイパビリティ
  集合と選ばれた経路にあります。プラットフォームの差が置かれるべき場所です。
- **codegen** です。これらはアプリ内に対応物のない端末レベルの変更なので、codegen はラベル付きの
  `TODO` を出します。BE-0035 の端末制御ステップの扱いと同じです。

## 検討した代替案

- **外観のアサーション種別を追加する。** 理由 1 つで却下します。端末の設定を読むだけで、
  `setAppearance` の直後ではほぼ同語反復であり、アプリについて何も言いませんし、作成者が求める主張は
  外観ごとのベースラインに対する `visual` ですでに書けます。「セレクタを解決しないから」を理由には
  *しません*。`clipboard` も解決しませんが、受け入れられているからです。使うはずだった読み戻しは、
  ランナーの落ち着き条件として残します。
- **アプリの内側から各状態を近似する**（`UI_TEST_FORCE_DARK=1` のような起動環境変数やディープ
  リンクを使う）。BE-0035 がすでに使った理由で却下します。アプリごとの仕掛けになり、アプリ非依存を
  壊します。ターゲットがどんなフックを露出しているかでツールの振る舞いが変わってしまいます。起動
  環境変数は、本当にアプリ固有の準備のために残ります。
- **iOS でも `deviceControl.airplaneMode` を広告し、バーを 0 にした `overrideStatusBar` で実装する。**
  明確に却下します。バーは見た目だけで、アプリの通信は成功し続けます。「オフラインのバナーが出る」を
  アサートするシナリオは不可解に失敗し、さらに悪いことに「その通信は行われなかった」をアサートする
  シナリオは、まったく誤った理由で成功します。何も広告せずプリフライトで失敗するほうが、はるかに
  正直です。
- **3 つを別々のロードマップ項目にする。** 却下します。3 つとも同じ形であり、8 つの作業単位のうち
  2 つ（`DeviceControl` プロトコルの拡張と、web バックエンドにコントローラを与えること）は共有され
  ます。分割してもレビューが読みやすくなることはなく、プロトコルの変更が 3 倍になるだけです。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] 文法とトークン。`DEVICE_CONTROL_ALL` の訂正も含めます。
- [ ] `DeviceControl` のメソッドと、`controller(eff, driver)` への拡張。
- [ ] iOS。simctl の外観、常駐ランナー経由の向き、プリフライトで拒否する機内モード。
- [ ] Android。3 つの `adb` 構築と読み戻し。
- [ ] web。初めての `DeviceControl` と 3 操作。
- [ ] 落ち着きの条件。有界な読み戻しポーリングと、その限界の明記。
- [ ] ドキュメント、3 つの線引き、外観比較のショーケースシナリオ。
- [ ] 3 つの end-to-end ワークフローでの実機検証。

実装しながら決める論点です。

- 向きの語彙を 4 値にするかどうかです。2 値で出荷しますが、iOS だけを対象にする作成者が
  `landscapeLeft` と `landscapeRight` を必要とするかは未解決です。
- iOS の実機が機内モードを実行できる余地があるかどうかです。実機のトグルは `xcodebuild` から届かない
  ので、おそらく答えは変わりませんが、仮定ではなく明記すべきです。
- 並列ワーカーとの相互作用です。端末制御はすでにレーンごとですが、web レーンのオフライン切り替えは
  コンテキスト単位で、Android エミュレータの機内モードは端末全体に効きます。1 台のエミュレータを
  共有する 2 レーンは干渉します。おそらくの答えは、レーンがシリアルを共有するときに Android の
  機内モードを拒否することです。
- 端末の状態をシナリオごとにマニフェストへ記録すべきかどうかです。外観が違うベースラインとの
  `visual` の差分を、証跡だけで診断できるようになります。
- `erase` が各バックエンドで外観と向きを戻すかどうかです。戻さないなら、ダークモードを設定した
  シナリオが同じリース内の次のシナリオへ漏れます。決定性の欠陥になるので、テストで固定します。

## 参考

- [BE-0035 — 端末制御ステップ](../BE-0035-device-control-primitives/BE-0035-device-control-primitives-ja.md)。
  この項目が倣うステップの型であり、区別すべき `overrideStatusBar` のバーの出どころでもあります。
- [BE-0052 — 端末状態のプリミティブ：タイムゾーン、クリップボード、シェイク](../BE-0052-device-state-timezone-clipboard-shake/BE-0052-device-state-timezone-clipboard-shake-ja.md)。
  この項目が続きとなる、2 枚目の端末状態のスライスです。
- [BE-0212 — 粗い deviceControl ケイパビリティを操作単位のトークンに分割する](../BE-0212-granular-device-control-capabilities/BE-0212-granular-device-control-capabilities-ja.md)
  と [BE-0128 — 端末制御ステップをケイパビリティでプリフライトゲートする](../BE-0128-device-step-capability-preflight/BE-0128-device-step-capability-preflight-ja.md)。
  不揃いなサポート行列を表現可能にする、トークンの分割とゲートです。
- [BE-0029 — 視覚回帰アサーション](../BE-0029-visual-regression-assertions/BE-0029-visual-regression-assertions-ja.md)
  と [BE-0171 — 要素スコープの視覚アサーション](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions-ja.md)。
  2 つ目の外観が解き放つものです。
- [BE-0282 — CI での実バックエンドのネットワーク捕捉・モック・アサーション網羅](../BE-0282-real-backend-network-coverage/BE-0282-real-backend-network-coverage-ja.md)。
  オフライン試験の応答スタブ側の半分であり、プリフライトが iOS で案内する代替でもあります。
- `bajutsu/common/drivers/base.py:88-141`（`deviceControl.*` トークンと `DEVICE_CONTROL_ALL`）、
  `bajutsu/common/capability/capability_preflight.py:163`（`_DEVICE_CONTROL_OPS`）、
  `bajutsu/common/platform_lifecycle/protocols.py:262-272`（`relauncher` と `controller`）、
  `bajutsu/common/platform_lifecycle/environments/web.py:105`（この項目が置き換える `None`）。
