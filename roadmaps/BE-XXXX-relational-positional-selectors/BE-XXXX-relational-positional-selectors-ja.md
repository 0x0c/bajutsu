[English](BE-XXXX-relational-positional-selectors.md) · **日本語**

# BE-XXXX — 位置関係セレクタ：隣接要素を起点に要素を指定する

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-relational-positional-selectors-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | シナリオ記述機能 |
| 関連 | [BE-0221](../BE-0221-android-scenario-portability-guarantee/BE-0221-android-scenario-portability-guarantee-ja.md), [BE-0171](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions-ja.md), [BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element-ja.md), [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md), [BE-0050](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md), [BE-0321](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis-ja.md) |
<!-- /BE-METADATA -->

## はじめに

ほかの要素との位置関係で要素を指す 5 つのセレクタフィールドを追加します。`above`、`below`、
`leftOf`、`rightOf`、`containing` の 5 つです。それぞれが、起点となる要素を指す入れ子の
`<Selector>` を取ります。5 つとも、各バックエンドがすでに `Element` に載せている `frame`
（`bajutsu/common/drivers/base.py:158`）だけを使う純粋な幾何計算です。ドライバの変更もケイパビリティ
トークンも要らず、プリフライトの行も増えません。これらは `find_all` の中で候補集合を絞ります。
`resolve_unique` の曖昧さの規則には手を触れません。曖昧な一致は、これまでどおり任意の 1 件に
解決されるのではなく失敗します。

## 動機

いまセレクタが持つフィールドは、どれも候補要素そのものを説明します。要素をまたぐ制約は
`within` だけで、しかも幾何的な包含しか表せません。「メールアドレスというラベルの下にある入力欄」
と書く手段がないため、識別子を持たない画面に届く道は 3 つしかありません。そしてどれも、
本リポジトリ自身が弱いと採点しているものです。

- `label` と `labelMatches` は、アプリを翻訳すると壊れます。
- `index` は、並び順が変わると壊れます。[selectors](../../docs/ja/selectors.md) 自身が
  「最終手段、フレーキー」と採点しています。
- `tapPoint` と座標ジェスチャは、レイアウトが変わると壊れます。安定度の梯子の最下段です。

チームが所有するアプリなら識別子を育てられますし、`doctor` と
[`coverage`](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md) はまさにその方向へ
押し出します。しかしサードパーティの画面では、それができません。誰も手を入れられないレガシー画面
でも、フレームワークが生成するコントロールでも同じです。`audit` はこの状況を採点できますが、
助言はできません。ラベルや trait だけで指すセレクタには `moderate-selector` の指摘が付きます。
その文言は `is auxiliary; prefer a unique id`（`bajutsu/analysis/audit.py:247`）です。`index` に頼る
セレクタは `fragile-selector`（`audit.py:243-246`）になります。一意な識別子は、識別子を持てない
画面がまさに用意できないものです。識別子を持つ隣接要素を起点にする指定は、上の 3 つのどれよりも
安定します。翻訳に耐え、読み順を保つレイアウト変更にも耐えるからです。

これが入ると、作成者は今日との違いを 2 つ具体的に指せるようになります。1 つ目は、識別子も
識別に足るラベルも持たないコントロール（ラベル付きの行に並ぶアイコンなど）を、`index` や座標に
頼らず指せることです。いまの文法が用意しているのはその 2 つと、`within` のスコープだけです。
`within` は、囲むコンテナ自体を指せるときにしか助けになりません。2 つ目は、`audit` が
`positional-selector` の指摘を出し、ステップが依存している起点要素と、その起点自身の階層を
名指しすることです。いまその同じステップに付く指摘は、危険の所在は言いますが、ステップが何に
依存しているかは言いません。

## 詳細設計

### 5 つの位置関係フィールド

```ebnf
Selector ::= {
  id?, idMatches?, label?, labelMatches?, traits?, value?, index?,   # 変更なし
  within?:     <Selector>,   # 変更なし: 候補の frame が起点の内側にある
  containing?: <Selector>,   # 新規: 候補の frame が、起点に一致する要素を内包する
  above?:      <Selector>,   # 新規 ┐ above と below は排他
  below?:      <Selector>,   # 新規 │ leftOf と rightOf も排他
  leftOf?:     <Selector>,   # 新規 │ 軸ごとに 1 つずつの併用は可能で、AND で結ばれる
  rightOf?:    <Selector>,   # 新規 ┘
}
```

```yaml
# 入力欄自体は識別子を持たないが、ラベルは識別子を持つ画面
- type: { text: "a@example.com", into: { traits: [textField], below: { id: form.emailLabel } } }

# 行の右側にあるアイコン。trait で絞るので、同じ行に 2 つあれば曖昧のまま失敗する
- tap: { traits: [button], rightOf: { label: "Wi-Fi" } }

# 既知のセルを内包する行。within の逆向き
- tap: { traits: [cell], containing: { label: "Order 12345" } }
```

[dsl-grammar](../../docs/ja/dsl-grammar.md) の §4 に個数制約が 3 つ増えます。`above` と `below`
は排他で、`leftOf` と `rightOf` も排他です。3 つ目は新しい制約で、起点以外のフィールドを最低 1 つ
求めます。`Selector._non_empty` はこの場合を拾いません。設定されたフィールドなら入れ子のセレクタ
でも数えるので、`{below: {id: x}}` はロードを通り、その列のすべてに一致してしまいます。別の
バリデータを置いて、ロード時に拒否します。

### 解決の手順

`find_all`（`bajutsu/common/drivers/base.py:756`）はいま、`within` を取り除いて基本フィールドを
照合し、`contains` で絞ります。位置関係フィールドは、この鎖を次の順序で延長します。

1. 候補自身のフィールド照合（`matches`）です。変更はありません。
2. `within` のスコープです。変更はありません。
3. `containing` です。起点に一致する要素の frame が候補の内側にあるとき、その候補が残ります。
   判定には既存の `contains`（`base.py:749`）を使います。
4. 半平面の判定と、直交する軸でのスパンの重なりです。`below` は、`y` が起点の下辺以降から始まり、
   かつ水平方向のスパンが起点と重なる候補を残します。ほかの 3 つも同様です。スパンの重なりを
   求めることが、`below` を「画面のどこか下」ではなく「同じ列の下」という意味にします。
5. 最近接ランクのフロンティアです。ほかの生存候補が、その候補と起点のあいだにその軸上で完全に
   挟まっているものを落とします。`containing` には対称の規則を当てます。ほかの生存コンテナを
   **真に**内包するコンテナを落とします。`contains` は辺を含むので、真にとは「内包しつつ内包され
   ない」という意味です。同じ frame を持つ 2 つのコンテナは、どちらも残って曖昧のままになります。
6. `resolve_unique` を通します。曖昧さの規則は**そのまま**です。

手順 4 と 5 は frame の集合に対する全域の純粋関数であり、**どちらも同着を解きません**。起点の
真下の同じ行に 2 つのコントロールが並べば両方が生き残り、同じラベルのボタンが 2 つあるときと
同じようにセレクタは失敗します。作成者は `traits` や `labelMatches` や `within` で絞ります。

ここがこの設計の要点です。位置関係フィールドは候補集合を**絞る**だけで、そこから**選び**ません。
`resolve_unique` の保証は、新しい場所でもそのまま成り立ちます。0 件なら `ElementNotFound`、
1 件なら解決、2 件以上なら `AmbiguousSelector` です
（[selectors](../../docs/ja/selectors.md)）。

### 起点は `within` と同じ解き方をし、`find_all` は全域のままです

起点はどれも `resolve_unique` ではなく `find_all` で照合します。いまの `within` のコンテナと
まったく同じ扱いです。起点が一致させる**いずれかの**要素に対して、述べられた関係が成り立てば、
その候補は残ります。ここから 2 つの帰結が出ます。どちらも意図したものです。

**一致しない起点は、エラーではなく空の候補集合になります。** これで `find_all` は全域のままです。
18 の呼び出し箇所がこの性質に依存しています。`base.default_wait_for`
（`base.py:965`）は `len(find_all(driver.query(), sel)) >= 1` であり、実在のバックエンドの
`wait_for` はここへ委譲します。`FakeDriver` と `WebContextDriver` は同じ判定を直に書いています。
起点がないときに送出してしまうと、
`wait: { for: { traits: [button], below: { id: x } } }` が自分の起点の出現を待てなくなります。
これは位置関係セレクタのもっとも自然な使い方であり、第 2 の prime directive に資するどころか
争うことになります。同じ全域性は 2 か所でも要ります。`negate: true` を伴う `_eval_exists`
（`bajutsu/common/assertions/evaluate.py:85`）と、`equals: 0` を伴う `_eval_count`
（`evaluate.py:124`）です。
一致しない `within` のコンテナは、すでに空のリストを返します（`base.py:783`）。これは新しい契約
ではなく、既存の契約です。

**複数に一致する起点は、その場で失敗せずに候補集合を広げます。** 増えた候補はそのまま
`resolve_unique` に流れ、2 件以上が残れば `AmbiguousSelector` が送出されます。声を上げる失敗は
1 段あとに、それを本来担っている場所で起きます。そのメッセージが位置関係フィールドと、集合を
広げた起点を名指しするので、保守する人を対象要素のほうへ向かわせずに済みます。

このメッセージが `resolve_unique` への唯一の変更です。`find_all` がすでに計算して捨てている起点の
一致結果を、外へ持ち出す必要があります。曖昧さの規則そのものは動きません。

広がりが声を上げるのは、2 件以上が残るときだけです。1 つの候補の上に起点が 2 つあれば、生き残るのは
1 件です。`resolve_unique` は数える前に内容の同じ候補をまとめます
（`_collapse_identical_duplicates`、`base.py:862-875`）。曖昧な起点でも、黙って解決してしまう場合が
残ります。この残りの場合に専用の診断を与えるかどうかは、後述の未解決の論点です。メッセージの質だけ
の問題ではありません。

### `audit` は候補を採点し、起点は別に報告します

`_tier`（`bajutsu/analysis/audit.py:54-60`）はいま 3 通りに採点します。`id` と `idMatches` は
`stable` です。`label`、`labelMatches`、`traits`、`value`、`within` は `moderate` です。`index` は
`fragile` です。位置関係フィールドには**独自の階層を与えません**。その安定性は起点から受け継ぐものであり、安定した
識別子を起点にすることと、翻訳されるラベルを起点にすることは、同じ危険ではないからです。候補は
これまでどおり自身のフィールドで採点し、位置関係フィールドは
`Finding(kind="positional-selector")` として別に記録して、起点と起点自身の階層を名指しします。
こうすると `audit` は点を付けるだけでなく、そのステップが何に依存しているかを説明します。

`_with_nested`（`audit.py:63`）はいま `within` にしか降りません。6 つの入れ子の起点すべてに降りる
必要があります。これを欠くと
[`coverage`](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md) が過小に数え、
[`impact`](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis-ja.md) が、起点だけが
識別子を参照しているステップを取りこぼします。

### バックエンドと、明記する 2 つの限界

すべてのバックエンドで動きます。ケイパビリティトークンは要らず、プリフライトの行も増えません。
`frame` は `Element` の必須フィールドであり、`xcuitest`、`adb`、`playwright`、`fake` のいずれも埋めます。

**`web` ブロックの中**では、`WebContextDriver` の frame が WebView 自身の座標系にあります。
位置関係セレクタはブロックの中では一貫して動きますが、ネイティブ要素と DOM 要素を関係づける用途に
使ってはいけません。

**要素ツリーに存在しない要素には、やはり届きません。** 位置関係セレクタは、ツリーが報告する要素
どうしの幾何を表すものであって、ツリーが載せていない要素を呼び出すものではありません。
`demos/showcase/ios/scenarios-noax/generated.yaml` の `tapPoint` がその実例で、理由はその
`from:` 自身が記録しています。「そのタブは要素リストにないので、見える中心をタップする」という
記述です。このステップは移行しませんし、この項目はそこでの改善を主張しません。

### コード生成

3 つのエミッタは、新しいフィールドを声を上げて拒否します。すでに持っている未対応フィールドの
一覧（`playwright._UNSUPPORTED_FIELDS` と、xcuitest のエミッタによる幾何的な `within` の拒否）に
加えます。黙って弱いセレクタを出力すると、シナリオより検証の薄いネイティブテストをチームに
渡してしまいます。

### 作業分解（MECE）

1. **文法**（`bajutsu/common/scenario/models/selector.py`）です。5 つのフィールドと、軸ごとの排他
   バリデータ 2 つ、起点以外のフィールドを 1 つ求める 3 つ目のバリデータ、
   [dsl-grammar](../../docs/ja/dsl-grammar.md) の §2 と §4 の生成規則、そして英語版を書きます。
   自己参照のための `model_rebuild()` は新たに要りません。
2. **幾何のヘルパー**（`bajutsu/common/drivers/base.py`）です。`contains` の隣に `beyond` と
   `spans_overlap` を置いて幾何を 1 つのモジュールにまとめ、純粋なユニットテストを付けます。
3. **解決**（`base.find_all`）です。フィルタの鎖とフロンティアを実装し、`resolve_unique` の
   曖昧さの規則には触れません。`find_all` が全域のままであることを、依存する呼び出し箇所で
   証明します。
   `base.default_wait_for`、`negate: true` を伴う `_eval_exists`、`equals: 0` を伴う `_eval_count`
   の 3 つです。ドライバ適合スイート
   （[BE-0114](../BE-0114-driver-conformance-suite/BE-0114-driver-conformance-suite-ja.md)）を
   拡張し、すべてのバックエンドが同じ答えを出すことを示します。
4. **起点を名指しする失敗**です。`resolve_unique` の `AmbiguousSelector` のメッセージが、位置関係
   フィールドと、候補集合を広げた起点を名指しするようにします。そのために起点の一致結果を
   `find_all` から捨てずに持ち出し、メッセージは既存の `base.py` と同じ文体で書きます。
5. **静的解析の走査**（`bajutsu/analysis/audit.py`）です。`_with_nested` が 6 つの起点すべてに降り
   るようにします。`_describe` は `within` と同じように、それらをセレクタ自身の文面から除きます。
   起点だけが識別子を参照するケースの回帰テストを、`coverage` と `impact` の双方に足します。
6. **`audit` の報告**です。`positional-selector` の指摘と、[cli](../../docs/ja/cli.md) の該当行を
   書きます。
7. **コード生成の拒否**です。3 つのエミッタが未対応フィールドを名指しし、`bajutsu run` を案内します。
8. **ドキュメント**です。[selectors](../../docs/ja/selectors.md) の解決表、
   [scenarios](../../docs/ja/scenarios.md) の実例、上の 2 つの限界の明記、そして英語版を書きます。

### prime directive との整合性

- **run の経路にモデルを置きません。** 解決は、ドライバがすでに報告している frame に対する算術です。
  合否はこれまでどおり機械判定のアサーションだけが決めます。
- **決定性**です。位置関係フィールドは候補集合を絞るだけで、そこから選びません。`resolve_unique` の
  曖昧さの規則は変わりません。フロンティアは、より遠いと証明できる候補を取り除いたところで止まり、
  同着を解くことはありません。
- **アプリ非依存**です。フィールドはどのターゲットでも同一で、特定のアプリやバックエンドに固有の
  ものは何もありません。
- **codegen** です。新しいフィールドは既存の明示的な拒否に加わり、弱いセレクタへ退化しません。

## 検討した代替案

- **半平面で絞ったあと、起点にもっとも近い候補を選んで解決する。** 却下します。「フィルタが最初に
  並べたものに解決する」を新しい場所へ持ち込むからです。[selectors](../../docs/ja/selectors.md)
  が定める `resolve_unique` の契約に反し、第 2 の prime directive にも反します。最近接**ランクの
  フロンティア**は、選ばずに使いやすさだけを得ます。より遠いと証明できる候補を取り除いてそこで
  止まるので、本当の同着は失敗のまま残ります。
- **何もせず、識別子を付けるよう促し続ける。** 却下します。ただし、その答えがどこまで通るかを
  隠さずに書きます。チームが所有するアプリには通り、サードパーティやレガシーの画面には通りません。
  そこでの逃げ道は `tapPoint` です。翻訳とレイアウト変更のどちらにも耐えず、`audit` も有用なことを
  何ひとつ言えません。
- **`Driver` プロトコルに階層クエリを足し、`childOf` を構造的に解く。** 却下します。正規化された
  `Element` のツリーは 4 つのバックエンドすべてで構造上フラットであり、親へのリンクを足すことは、
  1 つのセレクタ族のためにすべてのバックエンドが満たすべき `Driver` の API 変更になります。
  `within` の幾何的な包含がすでに `childOf` の意味を担い、`containing` がその逆を担います。フラットな
  ツリーは直接の子とより深い子孫を区別できないので、1 つのフィールドで両方を表すことにしました。
  読者に見つけさせるのではなく、ここに書いておきます。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] 文法。5 つの `Selector` フィールドと、3 つのバリデータ、DSL 文法を書きます。
- [ ] 幾何のヘルパー。`contains` の隣に `beyond` と `spans_overlap` を置き、純粋なユニットテストを付けます。
- [ ] 解決。`find_all` のフィルタの鎖とフロンティアを実装します。`default_wait_for`、`exists`、
      `count` に対して全域性を証明し、適合スイートを拡張します。
- [ ] 位置関係フィールドと、集合を広げた起点を名指しする `AmbiguousSelector`。
- [ ] 静的解析の走査。`_with_nested` が 6 つの起点に降り、`_describe` がそれらを除き、`coverage` と
      `impact` の回帰テストを足します。
- [ ] `audit` の報告。`positional-selector` の指摘と、CLI リファレンスの該当行を書きます。
- [ ] 3 つのエミッタでのコード生成の拒否。
- [ ] ドキュメント。selectors の解決表、scenarios の実例、2 つの限界、そして英語版を書きます。

実装しながら決める論点です。

- フロンティアに opt-out を用意するかどうかです。その軸の候補をすべて欲しい作成者もいます。既定は
  フロンティアとし、opt-out を入れるならそれ自身の決定性の議論が要ります。
- 複数に一致した起点に、専用の診断を与えるべきかどうかです。いまは候補集合が広がり、通常の
  `AmbiguousSelector` として表に出ます。これは 2 つの原因を一緒くたにします。対象そのものが曖昧な
  場合と、起点が曖昧だった場合です。さらに、広がっても 1 件しか残らなければ、診断は何も出ません。
- `index` とフロンティアの合成です。`index` はいま `other` を除外した集合を数えますが、この変更後は
  フロンティア通過後の集合を数えることになります。順序を明記しないと、2 つの機能が互いを驚かせます。
- スクロールするコンテナ上の frame です。起点より下にあって画面外の候補が、あるバックエンドでは
  ビューポート外の frame を返し、別のバックエンドではクリップされることがあります。適合スイートで
  1 つの答えに固定します。
- `record` が位置関係セレクタを出力すべきかどうかです。現時点の立場は「出力しない」です。`record`
  は識別子優先のままとし、位置関係は手で書くときの逃げ道に留めます。

## 参考

- [selectors](../../docs/ja/selectors.md)。`resolve_unique` と安定度の梯子、そしてこの項目が拡張する
  `within` の包含について書かれています。
- [dsl-grammar](../../docs/ja/dsl-grammar.md)。`Selector` の生成規則と §4 の個数制約です。
- [BE-0221 — 共有シナリオが Android でそのまま動くことを保証する](../BE-0221-android-scenario-portability-guarantee/BE-0221-android-scenario-portability-guarantee-ja.md)。
  id の候補リストであり、解決を変えずにセレクタ文法を広げた先例です。
- [BE-0171 — 要素スコープの視覚アサーションとセレクタによるマスク](../BE-0171-element-scoped-visual-assertions/BE-0171-element-scoped-visual-assertions-ja.md)。
  `Element.frame` のもう 1 人の利用者です。あちらは比較を絞り、この項目は選択を絞ります。
- [BE-0326 — `scroll` アクション：要素が現れるまでスクロールする](../BE-0326-scroll-to-element/BE-0326-scroll-to-element-ja.md)。
  要素を画面内に運びます。幾何が成り立つには起点が見えている必要があるので、この項目と合成します。
- [BE-0050 — E2E カバレッジマップ](../BE-0050-e2e-coverage-map/BE-0050-e2e-coverage-map-ja.md) と
  [BE-0321 — テスト影響分析](../BE-0321-test-impact-analysis/BE-0321-test-impact-analysis-ja.md)。
  起点の識別子が見えている必要のある、静的な読み手です。
- `bajutsu/common/drivers/base.py`（`Element`、`contains`、`find_all`、`resolve_unique`）と
  `bajutsu/analysis/audit.py`（`_tier`、`_with_nested`、`_selector_finding`）。
