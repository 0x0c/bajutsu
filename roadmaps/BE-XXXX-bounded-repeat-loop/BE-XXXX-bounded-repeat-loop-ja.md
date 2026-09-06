[English](BE-XXXX-bounded-repeat-loop.md) · **日本語**

# BE-XXXX — 回数付きループと上限付き条件ループ

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-bounded-repeat-loop-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | シナリオ記述機能 |
| 関連 | [BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md), [BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element-ja.md), [BE-0400](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount-ja.md), [BE-0082](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check-ja.md), [BE-0392](../BE-0392-scenario-before-after-hooks/BE-0392-scenario-before-after-hooks-ja.md), [BE-0297](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage-ja.md) |
<!-- /BE-METADATA -->

## はじめに

`repeat` ステップは、ステップの本体を 2 通りの有界な形で複数回実行します。`repeat: { times: N,
steps: [...] }` は本体をちょうど N 回実行します。`repeat: { while: <Assertion>, maxIterations: M,
steps: [...] }` は、各回の前に機械判定のアサーションを評価し、成り立つあいだ本体を実行します。
条件が成り立ったまま上限に達したら、そのステップは失敗します。`maxIterations` は必須で、どちらの
上限もモデルが拘束します。ローダーが受け付けるシナリオは、終わらないループを表現できません。

## 動機

「追加を 5 回押す」は、いまは 5 つの複製ステップです。「受信箱が空になるまで削除する」には、
そもそも書き方がありません。前者は保守の費用です。ほぼ同一の 5 ステップは、1 つの意図ではなく
5 つの意図として読めてしまいます。後者は能力の欠落です。作成者は固定回数で近似することになり、
別のデータセットではその回数が誤りになります。

[BE-0033](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md)
はこの欠落を名指ししたうえで、埋めずに残しました。その動機には、作成者が必要とする形の変化として
「ステップを有界な回数だけ繰り返す」流れが挙がっています。そして代替案では「一般的なスクリプト言語
や式言語」を却下しました。理由は「任意の式と**無制限の**ループは、シナリオを発散させたり、ランナー
が拘束できない論理に合否を依存させたりする」からです。この理由は無制限のループを退けますが、有界な
ループを退けません。BE-0033 が `forEach` を出荷した論拠も同じで、そのループは「静的に解決された
一致集合によって拘束され、必ず終了する」というものでした。

`scroll` には、有界な条件ループが必要とする形がすでにあります。作成者がステップ数の上限
（`maxScrolls`、既定 15、`gt=0`）を書き、ランナーは毎ステップで条件を確かめ直し、上限への到達は
静かな脱出ではなく**失敗**になります
（[BE-0326](../BE-0326-scroll-to-element/BE-0326-scroll-to-element-ja.md)、
[BE-0400](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount-ja.md) が精緻化）。この形を
1 つのアクションからステップの本体へ一般化することが、この提案のすべてです。

これが入ると、読者は 2 つの違いを指せるようになります。1 つ目は、いまシナリオファイルに N 個の
ほぼ同一の連続ステップとして現れる繰り返しが、1 つのステップとして現れることです。実行の
`manifest.json` には、これまでどおり N 回の作動が記録されます。2 つ目は、「一覧が空になるまで」を
表すシナリオがリポジトリに存在することです。いまはどのシナリオもそれを表現できません。

## 詳細設計

### `repeat` アクション

```ebnf
Action ::= … | { repeat: <Repeat> }        # capture / extract は取らない（if・forEach と同じ）

Repeat ::= { times: integer, as?: string, steps: list(<Step>) }                    ┐ XOR
         | { while: <Assertion>, maxIterations: integer, as?: string,
             steps: list(<Step>) }                                                 ┘
    # times:         1 ≤ times ≤ 100
    # maxIterations: 必須、1 ≤ maxIterations ≤ 100
    # as:            1 始まりの反復番号を vars.<as> に束縛する（forEach が要素を束縛するのと同じ）
```

```yaml
# 作成者が知っている固定回数
- repeat:
    times: 5
    steps:
      - tap: { id: cart.add }

# 画面が決める条件を、作成者の書いた上限のもとで回す
- repeat:
    while: { exists: { id: inbox.row } }
    maxIterations: 20
    steps:
      - tap: { id: inbox.row, index: 0 }
      - tap: { id: inbox.confirmDelete }
```

### 終了保証は、助言ではなく構造で与える

3 つの決定がそれを担います。どれも意図したものです。

**`maxIterations` は必須です。** `scroll.maxScrolls` が既定値 15 を持てるのは、それが自然な終了条件
を備えた物理的な過程を守るからです。対象が画面に入ったか、入っていないかのどちらかです。`while` の
本体は作成者が書く任意の作業なので、上限そのものが作成者の契約です。文法は、上限を書かないループを
拒みます。つまり文法は無制限のループを**表現できません**。単に推奨しないのではありません。

**どちらの上限もモデルが 100 で拘束します。** いま `Pinch.scale > 0` を強制しているのと同じ形です。
本体の最悪実行回数はファイル自身によって拘束されるので、BE-0033 の「必ず終了する」という性質が、
慣習ではなく構造として保たれます。

**条件が成り立ったまま `maxIterations` に達したら、そのステップは失敗します。** 失敗の理由には
反復回数と条件を書きます。静かに脱出すると、作成者が求めたより少ない仕事しかしていないシナリオが
緑になります。`scroll` の「上限で失敗する」がすでに拒んでいる失敗の形です。

### 実行時

`_run_repeat` を `bajutsu/common/orchestrator/loop.py` の `_run_if` と `_run_for_each` の隣に置き、
同じ `tuple[bool, str]` を返します。ステップのディスパッチには、`"if_"` と `"for_each"` の隣に
`"repeat"` の枝が増えます（`loop.py:1281-1284`）。`_run_repeat` は `_run_if` の条件の経路、つまり
`bindings` に対するアサーションの補間と `driver.query()` と評価を共有します。述語の経路は 1 つだけに
なり、分岐しうる 2 つ目は生まれません。

割り込みガードはこの共有から外します。`_InterruptGuard` は条件を評価のたびではなく `__post_init__` で
一度だけ補間しており、その理由は `loop.py:1002-1005` に記録されています。「`observe` は wait の
ティックごとに走るので、`${...}` を含まない条件をそこで補間し直すと、何も変わらないのに毎回直列化
することになる」というものです。`_fire_once`（`:1012`）は自分で `driver.query()` を発行せず、ループが
すでに持っているツリーに対して評価します（`:983-985`）。呼び出しごとに補間と問い合わせを行うヘルパーへ
畳み込むと、wait のティックごとに直列化し直し、ポーリングの中に余計なツリー取得を足すことになります。
ガードと共有しうるのは*評価*の半分だけで、補間と問い合わせは呼び出し側それぞれの都合の場所に残します。

条件は `Assertion` なので、`while: { count: { sel: …, atLeast: 1 } }` も `while: { request: … }` も
書けます。どこにもモデルは介在しません。`if` がすでに持っている性質です。入れ子は `_StepCounter` を
そのまま使うので、マニフェストには各回の証跡がそれぞれの経路の下に現れます。証跡に特別扱いは要りません。

### 新しい枝を覚える必要のある 5 つの走査

ステップの入れ子に降りる走査は 5 つあり、どれもすでに `if_` と `for_each` の対を持っています。
1 つでも漏らすと、欠陥になります。

- `bajutsu/common/capability/capability_preflight.py` の `_walk_steps`（`:83-87`）です。漏らすと、
  ループ本体の未対応ステップがゲートをすり抜け、端末上で遅れて失敗します。
  [BE-0082](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check-ja.md) が
  まさに防ぐために存在するものです。
- `bajutsu/analysis/audit.py` のセレクタの走査（`:130-137`）と指摘の走査（`:234-239`）です。別々の
  関数で、それぞれが自分の対を持っています。
- `bajutsu/analysis/coverage.py` の通信の走査（`:131-136`）です。
- `bajutsu/analysis/trace.py` の制御構文の判定（`:291`）です。

`bajutsu/codegen/common.py` の `_reject_runtime_only`（`:263`）は 6 つ目の箇所ですが、走査では
ありません。平坦な拒否であり、出力側の作業 — 各ターゲットのステップ生成が `times` の展開を覚えること
— は別の作業単位なので、下に単独で挙げます。

### ループをまたぐ `audit` と `impact`

`audit` は本体のセレクタを `times` 回ではなく**1 回**採点します。セレクタの安定性はセレクタの性質で
あって、何回実行されるかの性質ではありません。N 回数えると、ループがシナリオの安定度の割合を
水増しできてしまいます。新しい `loose-loop` の指摘は、`audit` がすでに名指ししている緩い形の条件を
使う `while` と、上限 100 に張り付いた `while` を対象にします。

`impact` は本体のステップを、囲む `repeat` ステップ自身の番号に帰属させます。いま `forEach` の本体が
そうなっているのと同じなので、`StepRef` に変更は要りません。`coverage` は本体が参照する id と
エンドポイントを、これまでどおり折り込みます。

### codegen は `times` を出力し、`while` を拒否する

`if` と `forEach` と `extract` がいま拒否されるのは、静的なテストにそれらを再現する実行時がないから
です（[BE-0297](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage-ja.md)）。
`repeat: { times: N }` は違います。上限がコンパイル時の定数なので、Swift でも TypeScript でも
Kotlin でも、回数付きループにそのまま写ります。**`times` は出力し、`while` は
`_reject_runtime_only` に加えます。** codegen が翻訳できる初めての制御構文であり、翻訳できる理由は
このループが安全である理由と同じです。

### 作業分解（MECE）

1. **文法**（`bajutsu/common/scenario/models/`）です。`Repeat` モデル、`times` と `while` の XOR
   バリデータ、1〜100 の上限、`maxIterations` の必須化、
   [dsl-grammar](../../docs/ja/dsl-grammar.md) の §2・§4・§5 と英語版を書きます。
2. **条件評価の共有**です。`_run_if` と `_run_repeat` が 1 つの経路を使い、`if` の既存の振る舞いが
   変わらないことを示します。割り込みガードは、一度だけの補間と呼び出し側から渡されるツリーを
   そのまま保ちます。
3. **`_run_repeat` とディスパッチ**です。両方の形、`as` の束縛、理由に回数を書く上限失敗、
   `_StepCounter` による入れ子を実装します。
4. **プリフライトの走査**です。`_walk_steps` が `repeat.steps` に再帰し、ループ本体の未対応ステップが
   端末作業の前に拒否されることをテストで示します。
5. **静的解析の走査**です。`audit`（セレクタ、指摘、`loose-loop`）、`coverage`、`trace` を直します。
6. **codegen** です。3 つの出力先が `times` を出し、`while` を声を上げて拒否します。
7. **ドキュメントとフィクスチャ**です。[scenarios](../../docs/ja/scenarios.md) の記述節、
   [cli](../../docs/ja/cli.md) の `audit` 指摘の行、両方の形のショーケースシナリオ、そして英語版を
   書きます。

### prime directive との整合性

- **run の経路にモデルを置きません。** 条件は `if` がすでに評価している機械判定のアサーションと同じ
  ものです。合否は引き続き `expect` のアサーションだけが決めます。
- **決定性**です。文法は終わらないループを表現できません。上限への到達は静かな脱出ではなく失敗なので、
  求めたより少ない仕事しかしていないシナリオが緑になることはありません。
- **アプリ非依存**です。`repeat` はバックエンドに欠けうるものを何も必要とせず、ケイパビリティトークン
  も増えません。本体のステップは、いまと同じようにゲートされます。
- **codegen** です。`times` は忠実に写ります。`while` は声を上げて拒否し、シナリオが求めていない
  ものを検証する固定回数へ退化しません。

## 検討した代替案

- **無制限の `while`。** 独立した 2 つの理由で却下します。BE-0033 がすでに退けています。発散しうる
  シナリオは、ランナーが拘束できない論理に合否を依存させるからです。そして実務上の失敗は、遅い
  テストよりたちが悪いものになります。発散した実行は CI の実時間タイムアウトで打ち切られ、失敗では
  なく**そもそも判定が出ません**。実行履歴には穴として残ります。`flakiness` と `audit --history` が
  唯一まわりを解析できない形です。
- **任意のステップに付ける `times:` 修飾子**（`tap: {...}` に `times: 5` を添える形）。却下します。
  `Step` が強制する「アクションキーはちょうど 1 つ」という規則を壊し、共有する反復変数の置き場も
  なく、複数ステップの本体を表せません。2 ステップを繰り返したい作成者は元の場所に戻ります。
- **`times` をローダーで展開する**（`expand_components` や `expand_data` と並べて N 個に複製する）。
  静的解析にも実行時にも変更が要らないので、確かに魅力的です。2 つの理由で却下します。レポートには
  1 つのループの N 回ではなく、見分けのつかない N 個のステップが並びます。読者は意図した繰り返しと
  コピー&ペーストの誤りを区別できません。そして `while` をまったく表せないので、1 つの概念に対して
  無関係な 2 つの機構を文法が抱えることになります。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] 文法。`Repeat` モデル、バリデータ、上限、DSL 文法を書きます。
- [ ] 条件評価の括り出し。`_eval_condition` を 3 つの呼び出し元で共有します。
- [ ] `_run_repeat` とディスパッチの枝。上限失敗とステップの入れ子を実装します。
- [ ] `repeat.steps` へのプリフライト走査。早期失敗のテストで示します。
- [ ] 静的解析の走査。`audit`、`coverage`、`trace`、`loose-loop` の指摘を直します。
- [ ] codegen。`times` を出力し、`while` を拒否します。
- [ ] ドキュメントと、両方の形のショーケースシナリオ。

実装しながら決める論点です。

- 上限 100 が妥当かどうか、そしてターゲットごとに設定可能にすべきかどうかです。設定可能にすると
  「文法自身がループを拘束する」という論拠が弱まるので、現時点の立場は固定の定数です。
- `as` は既存の束縛マップに合わせて文字列を束縛します。数値の用途がこのマップを広げるに値するか
  どうかは、別の決定です。
- 条件が偽になって抜けた `while` の反復回数を、マニフェストに記録すべきかどうかです。作成者が
  5 回を期待したのに 1 回で終わったループの診断には役立ちますが、マニフェストの面が増えます。
- ループ本体で割り込みが発火したとき、回をまたぐ復旧の抑止とどう噛み合うかです。

## 参考

- [BE-0033 — シナリオ変数と軽量な制御構文](../BE-0033-scenario-variables-control-flow/BE-0033-scenario-variables-control-flow-ja.md)。
  `if` と `forEach` を出荷し、この欠落を名指しし、この項目が提案しない無制限の形を却下しました。
- [BE-0326 — `scroll` アクション：要素が現れるまでスクロールする](../BE-0326-scroll-to-element/BE-0326-scroll-to-element-ja.md)
  と [BE-0400 — scroll ステップに求めた距離を進ませる](../BE-0400-scroll-step-amount/BE-0400-scroll-step-amount-ja.md)。
  この項目が一般化する `maxScrolls`、つまり作成者が書く上限と、上限での失敗という先例です。
- [BE-0082 — 実行前のケイパビリティプリフライト](../BE-0082-capability-preflight-check/BE-0082-capability-preflight-check-ja.md)。
  プリフライトの走査がループ本体へ再帰しなければならない理由です。
- [BE-0297 — XCUITest codegen の実コンパイル網羅を DSL 全面へ広げる](../BE-0297-codegen-xcuitest-dsl-coverage/BE-0297-codegen-xcuitest-dsl-coverage-ja.md)。
  `while` が加わる、実行時専用構文の拒否です。
- `bajutsu/common/orchestrator/loop.py`（`_run_if`、`_run_for_each`、ステップのディスパッチ）、
  `bajutsu/common/capability/capability_preflight.py`（`_walk_steps`）、
  `bajutsu/codegen/common.py`（`_reject_runtime_only`）。
