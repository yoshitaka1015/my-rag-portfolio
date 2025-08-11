# RAGシステム ポートフォリオ（GCP & Vertex AI）

## TL;DR（30秒で概要）
- **何を作ったか**: GCP×Vertex AIで動く **RAG（Retrieval-Augmented Generation）**。PDF等の非構造文書をOCR→分割→ベクトル化し、対話で検索・回答。
- **なぜこう作ったか**: MVPでは “**最短で価値検証**” を優先。**GCS(JSONL)** をベクトルストアにして外部DB依存を排除し、**IaC(Terraform)** と **CI/CD(GitHub Actions+WIF)** で再現性と変更容易性を担保。
- **今後の伸ばし方**: **評価駆動**で継続改善。自動評価（Faithfulness/Relavancy）を基盤に、BigQuery Vector SearchやDataflow移行でスケール&高速化。

---

## 私の設計思想 / 戦略
- **計測→学習→改善** のループを最短に：まずMVP→すぐに自動評価を整備→改善の効果を数値で証明。
- **Simplicity First**：小さく正しく動くことを最優先。複雑さは必要になった瞬間にだけ足す。
- **No snowflake**：**Terraform**で全てをコード化。**GitHub Actions + Workload Identity Federation** で“鍵を置かない”デプロイ。
- **変更容易性と安全性の両立**：**digestデプロイ**で順序保証、`prevent_destroy`で誤破壊を防止。
- **コストと体験のバランス**：デフォルトは **min_instance=0**（節約）。必要に応じて1に切り替え、コールドスタート無し構成へ。
- **観測可能性**：Cloud Run/Loggingでメトリクス・ログを確認できるよう構成。評価スコアもCIで可視化予定。

---

## システム全体像（アーキテクチャ）
```mermaid
flowchart TD
  subgraph Dev[CI/CD & IaC]
    GH[GitHub Actions]--OIDC-->WIF[(Workload Identity<br/>Federation)]
    WIF-->GCP[Google Cloud]
    TF[Terraform]
    GH--deploy-->AR[Artifact Registry]
  end

  subgraph Index[Indexing Pipeline]
    SRC[GCS Source Bucket]
    OCR[Cloud Run: OCR Function]
    EMB[Vertex AI Embeddings]
    OUT[GCS Vector Store (JSONL)]
  end

  subgraph App[Application Pipeline]
    APP[Cloud Run: Streamlit App]
    LLM[Vertex AI Gemini]
  end

  SRC--Object create-->OCR
  OCR--Call-->EMB
  OCR--Write JSONL-->OUT

  APP--Vectorize Query-->EMB
  APP--Load Chunks+Vec-->OUT
  APP--Send context+query-->LLM

  Dev--terraform apply-->Index
  Dev--terraform apply-->App
```

---

## 環境と命名規則
| 項目 | 値 |
|---|---|
| **GCP プロジェクト** | `serious-timer-467517-e1` |
| **リージョン** | `us-central1`（最新モデル/サービス利用のために統一） |
| **Artifact Registry** | リポジトリ: `rag-portfolio-repo` |
| **Cloud Run（staging）** | `ocr-function-staging`, `rag-portfolio-app-staging` |
| **Cloud Run（prod）** | `ocr-function-prod`, `rag-portfolio-app-prod` |
| **GCS（staging）** | `bkt-<PROJECT_ID>-rag-resource-staging` / `bkt-<PROJECT_ID>-rag-output-staging` |
| **GCS（prod）** | `bkt-<PROJECT_ID>-rag-resource-prod` / `bkt-<PROJECT_ID>-rag-output-prod` |
| **Terraform backend** | GCS: `bkt-<PROJECT_ID>-tfstate`（prefix: `terraform/state`） |

> すべて **IaC** で管理。Cloud Runの **env**（`VECTOR_BUCKET_NAME` / `OUTPUT_BUCKET_NAME` など）もTerraformで宣言。

---

## CI/CD パイプライン（digestデプロイ）
| Workflow | トリガー | 役割（要約） |
|---|---|---|
| `pr-staging-infra-deploy.yml` | `pull_request`（`terraform/**`変更）/ 手動 | stagingインフラを `init→plan→apply`。WIFでGCPへ。|
| `pr-staging-apptest-deploy.yml` | `pull_request` | アプリのビルド/簡易テスト。必要に応じてプレビュー。|
| `pr-staging-destroy.yml` | PR close / 手動 | stagingのクリーンアップ（`prevent_destroy` 保護あり）。|
| `merge-prod-infra-deploy.yml` | 手動のみ | 本番インフラの `plan→apply`。多重実行を `concurrency` で抑止。|
| `merge-prod-app-deploy.yml` | `main` への push（`app/**`, `ocr-function/**` 変更時） | Build&Push→**digest**で Cloud Run へデプロイ（順序保証/待ち時間ゼロ）。|

**ポイント**
- `google-github-actions/auth@v2` の **WIF** を使用（秘密鍵を置かない運用）。
- アプリは **タグ**でpushしつつ、デプロイは **digest** 固定で不変参照。

---

## セキュリティと権限設計
- **WIF（OIDC）**：Issuer=`https://token.actions.githubusercontent.com`、`attributeCondition` で `repository=='<owner>/<repo>'` を強制。
- **最小権限**：Actions用SAへ `roles/run.admin` / `roles/artifactregistry.writer` / （必要に応じて）`roles/iam.serviceAccountUser`。
- **公開設定**：PoC段階のため **staging/prod ともに公開**（`roles/run.invoker`=allUsers）。本番運用では Cloud Armor / IAP / OAuth で段階的に制限可能。

---

## 運用 Runbook（抜粋）
- **stagingインフラを適用**：PR作成→`pr-staging-infra-deploy` が自動適用。手動でも実行可。
- **本番インフラ**：`merge-prod-infra-deploy` を **Actionsから手動実行**。
- **本番アプリ**：`main` にpushすると `merge-prod-app-deploy` が **digestデプロイ**（Cloud RunのリビジョンURLを出力）。
- **Destroy（staging）**：`pr-staging-destroy` を手動実行。Cloud Runを完全削除する場合は一時的に `prevent_destroy` を外す。

---

## コスト方針（目安の出し方）
- デフォルトは **`min_instance=0`**（コールドスタート許容で節約）。体験重視時は `1` に変更し、利用状況をみて上下。
- 実コストの把握は **Cloud Billing レポート**＋**リソース別メトリクス**（Cloud Run / Artifact Registry / GCS）で確認。リビジョン別利用やバケットの転送量をモニタリング。

---

## テスト戦略
- **ユニット**：アプリの検索ロジック（例：`find_similar_chunks`）。`pytest`＋最小依存（`numpy` など）を固定。
- **統合**：HTTPでバックエンドを直接叩く簡易テストを追加予定。
- **自動評価**：RAGAs 等で Faithfulness / Answer Relevancy をCIサマリに可視化予定。

---

## 主要なアーキテクチャ判断（ADRダイジェスト）
- **ベクトル格納はGCS(JSONL)**：MVPで速度より “**依存とコストの最小化**” を優先。
- **リージョン統一：`us-central1`**：モデル/サービスの選択肢を最大化。
- **デプロイは digest 固定**：順序保証・ロールバック容易性・再現性確保。
- **既存リソースは import してTF管理**：`destroy → 作り直し` ではなく **非破壊で整合**。
- **公開/非公開の判断**：デモ容易性を優先し全公開。以降は段階的にアクセス制御を導入。

---

## 開発ロードマップ

### Phase 1: MVP（完了）
- RAGのコア機能（投入→ベクトル化→検索→回答）を最小構成で実装。GCS(JSONL)＋Cloud Runで“最短で価値”。

### Phase 2: CI/CD と自動評価（進行中）
- GitHub Actionsの整備、ユニット/統合テスト、LLM-as-a-judgeで自動評価。結果をActionsサマリに出力。

### Phase 3: 性能/拡張性
- ベクトル検索を **BigQuery Vector Search** へ。データ処理は **Cloud Dataflow** 化。

### Phase 4: 機能拡張
- リランキング、会話履歴の永続化、UI E2E（Playwright）など。

---

## 再現手順（開発者向けメモ）
```bash
# 事前: gcloud CLI / Terraform / Docker を用意

# Terraform 初期化（staging）
cd terraform
terraform init -reconfigure -upgrade
terraform workspace select staging || terraform workspace new staging

# 変数（CIと同値）
export TF_VAR_project_id="serious-timer-467517-e1"
export TF_VAR_region="us-central1"
export TF_VAR_environment="staging"
export TF_VAR_source_bucket_name="bkt-serious-timer-467517-e1-rag-resource-staging"
export TF_VAR_output_bucket_name="bkt-serious-timer-467517-e1-rag-output-staging"

# 既存のCloud Runがある場合は初回のみimport
terraform import 'google_cloud_run_v2_service.rag_app' \
  "projects/${TF_VAR_project_id}/locations/${TF_VAR_region}/services/rag-portfolio-app-staging" || true
terraform import 'google_cloud_run_v2_service.ocr_function' \
  "projects/${TF_VAR_project_id}/locations/${TF_VAR_region}/services/ocr-function-staging" || true

# 差分と適用
terraform plan -input=false
terraform apply -auto-approve -input=false
```
