[English](BE-XXXX-publish-package-pypi.md) · **日本語**

# BE-XXXX — 実体のあるバージョンとリリースワークフローでパッケージを公開する

<!-- BE-METADATA -->
| 項目 | 値 |
|---|---|
| 提案 | [BE-XXXX](BE-XXXX-publish-package-pypi-ja.md) |
| 提案者 | [@0x0c](https://github.com/0x0c) |
| 状態 | **提案** |
| トラッキング Issue | [検索](https://github.com/bajutsu-e2e/bajutsu/issues?q=is%3Aissue+label%3Aroadmap-tracking+in%3Atitle+"BE-XXXX") |
| トピック | CI / build infrastructure |
| 関連 | [BE-0292](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner-ja.md)、[BE-0272](../BE-0272-serve-version-badge/BE-0272-serve-version-badge-ja.md)、[BE-0277](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge-ja.md)、[BE-0111](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency-ja.md)、[BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md)、[BE-0164](../BE-0164-config-aware-environment-installer/BE-0164-config-aware-environment-installer-ja.md)、[BE-0173](../BE-0173-slim-web-worker-image/BE-0173-slim-web-worker-image-ja.md) |
<!-- /BE-METADATA -->

## はじめに

パッケージは公開されておらず、`pyproject.toml` は `version = "0.0.0"`（`:3`）を抱えたままです。
同じ文字列は `bajutsu/__init__.py`（`:3`）にも重複しています。この項目は、ドキュメントがすでに
書いているインストール手順を本当に実行できるものにします。バージョンの単一情報源、タグを起点に
した OpenID Connect の信頼された公開（trusted publishing）によるリリースワークフロー、
`bajutsu --version` フラグ、そして純粋な Python ホイールに収まらない成果物それぞれについての
判断を用意します。

## 動機

[README](../../README.md)（`:167`）と
[入門ガイド](../../docs/ja/getting-started/index.md)（`:50`）はどちらも `pip install bajutsu` を
指示し、そのうえで基本インストールに何が含まれ何が含まれないかまで説明しています。しかし、
どちらの指示も動きません。そのため評価は必ずクローンとツールチェーンの用意から始まり、
ドキュメントが最初に示す具体的な一歩を読者は踏み出せません。

この欠落は、すでに出荷済みの機能を 2 つ劣化させています。
[BE-0272](../BE-0272-serve-version-badge/BE-0272-serve-version-badge-ja.md) のバージョンバッジは
`0.0.0` を表示します。バッジが読む欄を誰も埋めないからです。
[BE-0277](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge-ja.md) が存在
すること自体、BE-0272 がビルド時の刻印を見送らざるを得なかった結果です。フックする先の
ビルドパイプラインがなかったのです。

任意の追加依存（extra）のうち 4 つは自己参照です。`bedrock`（`:31`）、`worker-web`（`:41`）、
`worker-ios`（`:45`）、`cloud`（`:70`）はいずれも `bajutsu[…]` への依存を宣言しています。
自己参照の extra は、配布物が名前で見つかるようになって初めて外部の利用者の環境で解決されます。
宣言そのものがどれだけ正しくても、`pip install 'bajutsu[worker-web]'` は今日誰の環境でも
成功しません。

これが入れば、このリポジトリのクローンを持たないマシンから読者自身が確かめられます。
`pip install bajutsu && bajutsu --version && bajutsu lint <file>` が成功し、`0.0.0` ではない
バージョンを表示します。同時に、出荷済みの 2 つの機能 — `serve` のヘッダーバッジと
セルフホストイメージのバージョン欄 — がプレースホルダを出すのをやめます。

## 詳細設計

### バージョン付けと、その番号が約束するもの

**`0.1.0`** から始めるセマンティックバージョニングを採用し、1.0 未満として運用します。そのうえで
1 点を明記します。シナリオ文法の互換性の約束を担うのは
[BE-0119](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md) の
`schema:` であり、パッケージのバージョンでは**ありません**。この切り分けは重要です。マイナー
バージョンの繰り上げはコマンドラインのフラグを変えることがありますが、古い Bajutsu が新しい
シナリオファイルを誤読せずに拒否するのは `schema` が上がったときだけです。これを書き残すことで、
後の読者がバージョン番号からツールの実際より強い約束を読み取ってしまうのを防ぎます。

### バージョンの情報源を 1 つにする

この文字列は今日 2 か所にあり、静かに食い違い得ます。`pyproject.toml` に `dynamic = ["version"]`
と、`bajutsu/__init__.py` を指す `[tool.hatch.version]` を置き、モジュール中のリテラルを単一の
情報源として hatchling がビルド時に読みます。加えてリリースジョブは、push されたタグが
`bajutsu.__version__` と一致しない場合に公開を拒否します。こうすればタグが、自身の生んだ
成果物と食い違うことはありません。

### `bajutsu --version`

このフラグは存在しません。ルートアプリケーションに Typer のコールバックを置き、バージョンと、
`.git` ディレクトリがある場合には `serve` のバージョンエンドポイントがすでに読んでいるのと同じ
短縮コミットを表示します。作業単位としては小さく、インストール直後に誰もが最初に打つものです。

### リリースワークフロー

`v*` タグの push を起点とする新しいワークフローを追加します。

1. `make check` — 赤いまま公開しない、どのブランチにも課しているのと同じ契約です。
2. タグと `__version__` の一致を確かめるガード。
3. `uv build` による sdist と `py3-none-any` ホイールの生成。
4. リポジトリのシークレットに長命のトークンを置くのではなく、**OpenID Connect による信頼された
   公開**を使います。このリポジトリのシークレット走査の体制を踏まえると、公開用トークンは
   リポジトリ内で最も価値の高いシークレットになってしまいます。OpenID Connect はそれを丸ごと
   取り除きます。
5. 成果物を添えた GitHub Release。リリースノートはその範囲でマージされた PR のタイトルから
   生成します。変更履歴ファイルはコミットしません。索引を committed で持つより導出する、という
   このリポジトリの好みに沿った判断です。
6. **公開後の、まっさらな仮想環境での検証**。ワークフローの真価はここにあります。
   - `pip install bajutsu` を行い、`anthropic` が import **できない**ことを確認します。これは
     [BE-0111](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency-ja.md) の
     「基本インストールに AI は含まれない」という保証を、`ai` extra が入った開発用の同期環境
     ではなく、公開された成果物そのものに対して証明します。
   - 自己参照の 4 つの extra をそれぞれ `pip install` します。ここで初めて解決できるようになる
     ものです。
   - フィクスチャに対する `bajutsu --version`、`bajutsu schema`、`bajutsu lint`。端末を必要と
     しない範囲を、インストール済みのホイールから実際に動かします。

`pyproject.toml` かこのワークフローに触れる PR では、手順 1 から 3 とメタデータ検査だけを行う
ドライランのジョブを走らせます。パッケージングの破損がタグではなくブランチの段階で表に出ます。

### XCUITest ランナーが難所

[BE-0292](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner-ja.md) はビルド済み
ランナーをホイールへ強制的に含めますが、そのディレクトリを作るのは **macOS 上の Xcode** を必要と
する make ターゲットであり、ビルドメタデータには Xcode のバージョン、ソフトウェア開発キット
（SDK）のバージョン、ソースのハッシュが記録されます。Linux でビルドしたホイールにはそれが入り
ません。macOS でビルドしたホイールは、Xcode との互換性を**ホイールのプラットフォームタグでは
表現できない**シミュレータ専用ランナーを配ることになります。その結果 `pip` は利用者の Xcode では
動かせないランナーを解決してインストールし、失敗は解決時のエラーではなく分かりにくい実行時
エラーとして現れます。

そこでこう決めます。**基本ホイールは純粋な Python のままとし、ランナーを含めません。** それでも
web と Android は完全に賄えますし、ターゲットが自前のランナーやビルド設定を指定している場合は
iOS も賄えます。この 2 つのつまみは、BE-0292 が任意化したうえで残したものです。ランナーは
**併走する配布物** — ランナーだけを収めた macOS プラットフォームのホイール — として出し、新しい
`ios` extra から引きます。Mac の利用者は `pip install 'bajutsu[ios]'` と打ちます。プラットフォーム
タグでは依然として Xcode のバージョンを表現できないため、`doctor` に、インストール済みランナーの
ビルドメタデータと手元の `xcodebuild -version` を突き合わせ、平易な言葉で告げる検査を追加します。

### Android の UI Automator サーバー

こちらはすでに任意であり、すでに機能を落として動きます。常駐サーバーがビルドされていないとき、
Android 環境は代わりに `uiautomator dump` でツリーを読みます
（`bajutsu/common/platform_lifecycle/environments/android.py:174`）。1 回の読み取りは遅くなりますが、
アクセシビリティツリーとしては完全です。つまり pip インストールでも Android は今日すでに、届く範囲を
狭めることなく、速度だけを落とした形で動きます。サーバーのビルド成果物はアーキテクチャに依存しないデータ
なので、同梱してもホイールは `py3-none-any` のままです。リリースワークフローに Gradle の手順を
足します。これは独立した作業単位なので、最初のリリースを止めることなく 2 回目以降へ回せます。

### 過大な約束をやめるべきドキュメントと、書き始めるべきメタデータ

[README](../../README.md) と[入門ガイド](../../docs/getting-started/index.md)、および
それぞれの日本語版に、正直なインストール対応表を載せます。日本語の
[README](../../README.ja.md) には現在この指示自体がないので、ここで初めて載せることになります。web と Android は基本インストール、
web のブラウザ導入は今日どおり、iOS は `ios` extra と Xcode バージョンについての注記付き、
という内容です。[ai-boundary](../../docs/ja/ai-boundary.md) の基本インストールに関する記述には、
その裏づけとしてリリースジョブの検証を添えます。

これらと一緒に、パッケージングのメタデータの修理を 2 つ入れます。`readme = "DESIGN.md"`（`:5`）は
パッケージインデックスのプロジェクトページを 56 KB の日本語設計文書に向けています。ここは README
であるべきで、その相対リンクはドキュメントサイトの絶対リンクに直す必要があります。パッケージ
インデックスは相対リンクを壊れたものとして描画しますし、そのページは評価者が最初に見る場所だから
です。また `[project.urls]` は丸ごと欠けています。ホームページ、ドキュメント、リポジトリ、
Issue を書きます。

### 作業分解（MECE）

1. **バージョンの単一情報源化**です。`dynamic = ["version"]`、`[tool.hatch.version]`、
   `bajutsu/__init__.py` の `0.1.0`、そしてタグと `__version__` のガードを入れます。
2. **`bajutsu --version`** です。ルートのコールバックと [cli](../../docs/ja/cli.md) への記載を
   加えます。
3. **リリースワークフロー**です。タグ起動、`make check`、`uv build`、信頼された公開、生成される
   リリースノート、そして PR 上のドライランジョブを組みます。
4. **公開後の検証**です。AI を含まない基本インストールと、自己参照の各 extra を、まっさらな環境で
   確かめます。
5. **パッケージングのメタデータ**です。README を絶対リンクで指す readme、`[project.urls]`、
   分類子を整えます。
6. **XCUITest ランナーの経路**です。併走する配布物、`ios` extra、`doctor` の Xcode 互換性検査を
   用意します。
7. **UI Automator サーバー**です。パッケージデータへ同梱し、リリースワークフローに Gradle の手順を
   足します。
8. **ドキュメント**です。両言語の README と入門ガイドにインストール対応表を載せ、`ai-boundary` に
   裏づけの一文を足します。

### prime directive との整合性

- **run の経路にモデルを置きません。** ここで扱うのはパッケージングとリリース工程だけで、ランナー
  にも合否判定にも触れません。
- **決定性**です。リリースはどのブランチにも課している `make check` で門番され、公開後の検査は作業
  ツリーではなく成果物そのものを確かめます。
- **アプリ非依存**です。インストール対応表はアプリケーションではなくバックエンドで区分し、`ios`
  extra が運ぶのはツールチェーンの成果物であって、個々のアプリの知識ではありません。

## 検討した代替案

- **XCUITest ランナーを内包した macOS ホイールを公開する。** 却下します。ホイールの
  プラットフォームタグが符号化するのはオペレーティングシステムとアーキテクチャであって、
  ランナーがどの Xcode と SDK でビルドされたかではありません。ランナーのビルドメタデータが
  その 2 つを正確に記録しているのは、まさにそれが重要だからです。この方式では `pip` が動かせない
  ランナーを解決してインストールし、利用者は依存解決のエラーではなく実行時の失敗としてそれに
  出会います。併走する配布物と `doctor` の互換性検査なら、食い違いが目に見えます。
- **カレンダーバージョニング。** 外部利用者がまだおらず、ロードマップ項目を速く多く出荷している
  今のプロジェクトには本当に魅力的です。それでも却下します。カレンダーバージョニングは新しさは
  伝えますが、互換性については何も伝えません。このリポジトリの文化は互換性の約束を明示すること
  であり、`schema:` はまさにそれです。セマンティックバージョニングなら 2 つの約束は切り離した
  うえで両方とも述べられますが、カレンダーバージョニングではどちらも述べられません。
- **sdist だけを公開し、利用者にビルドさせる。** 却下します。sdist を役立てるにはビルド
  バックエンドが要り、iOS のためには macOS 上の Xcode ツールチェーンまで要ります。それこそ
  この項目が取り除こうとしている、クローンとツールチェーンの負担そのものです。
- **インストール済み配布物のメタデータからバージョンを読み、`pyproject.toml` を正とする。**
  却下します。`__version__` が実行時の参照になり、配布物としてインストールされていない
  チェックアウトでは例外になります。そしてこの属性は `serve` のリクエスト経路で読まれています
  （BE-0272）。

## 進捗

> 開発の進行に合わせて常に最新の状態に保ってください。チェックリストは *詳細設計* の MECE な
> 作業分解（作業の単位ごとに 1 つ）に対応し、ログには変更内容と時期（古い順）を PR へのリンクと
> ともに記録します。

- [ ] バージョンの単一情報源化とタグのガード。
- [ ] `bajutsu --version` と CLI リファレンスへの記載。
- [ ] 信頼された公開と PR ドライランを備えたリリースワークフロー。
- [ ] まっさらな環境での公開後検証。
- [ ] パッケージングのメタデータ — readme、URL、分類子。
- [ ] XCUITest ランナーの併走配布物、`ios` extra、`doctor` の検査。
- [ ] パッケージデータとしての UI Automator サーバー。
- [ ] ドキュメント — 両言語のインストール対応表。

構築の途中で決めるべき論点です。

- 配布物の名前がパッケージインデックスで空いているかどうか。何よりも先に登録します。この項目
  全体がそこに懸かっています。
- 最初のリリースに併走するランナー配布物を含めるか、それとも GitHub Release にランナーを添付し
  ダウンロード手順を書いておく暫定形にするか。
- yank とホットフィックスの方針、および 1.0 未満のリリースを常にテスト用インデックスへ先に出すか
  どうか。
- ドキュメントサイトをリリースに合わせてバージョン付けするか、単一バージョンのままにするか。
  この項目のスコープ外ですが、判断はこの項目の頻度によって決まります。

## 参考

- [BE-0292 — XCUITest ランナーを同梱して testRunner を省略可能にする](../BE-0292-xcuitest-bundled-runner/BE-0292-xcuitest-bundled-runner-ja.md)
  — この項目がホイールに正直に載せられる場所を見つけなければならない強制同梱。
- [BE-0272 — serve の Web UI のヘッダーに bajutsu 自身のコミット・バージョンを表示する](../BE-0272-serve-version-badge/BE-0272-serve-version-badge-ja.md)
  と [BE-0277 — セルフホスト用 Docker イメージにコミットハッシュを埋め込み、バージョンバッジに表示する](../BE-0277-docker-build-commit-badge/BE-0277-docker-build-commit-badge-ja.md)
  — リリースパイプラインの不在によって劣化している、出荷済みの 2 つの機能。
- [BE-0111 — AI SDK を extra へ降ろし、決定的ゲートを AI 非依存でインストールできるようにする](../BE-0111-ai-sdk-optional-dependency/BE-0111-ai-sdk-optional-dependency-ja.md)
  — 公開後の検査が成果物に対して証明する保証。
- [BE-0119 — バージョン間の読み込みに備えてシナリオスキーマにバージョンを持たせる](../BE-0119-scenario-schema-versioning/BE-0119-scenario-schema-versioning-ja.md)
  — パッケージのバージョンがあえて担わない互換性の約束。
- [BE-0164 — config を踏まえた環境インストーラー](../BE-0164-config-aware-environment-installer/BE-0164-config-aware-environment-installer-ja.md)
  と [BE-0173 — 軽量な Linux web worker のコンテナイメージ](../BE-0173-slim-web-worker-image/BE-0173-slim-web-worker-image-ja.md)
  — ホイールの先で新規インストールがなお必要とするもの、およびワーカーの実行時クロージャの extra。
- `pyproject.toml`（`:3` version、`:5` readme、`:31`／`:41`／`:45`／`:70` の自己参照 extra）、
  `bajutsu/__init__.py:3`、`README.md:167`、`docs/ja/getting-started/index.md:50`、
  `bajutsu/common/platform_lifecycle/environments/android.py:174`（`uiautomator dump` への
  フォールバック）。
