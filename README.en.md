# NLP Pipeline (Entity Recognition / Word Embeddings / Sentiment Classification)

![License](https://img.shields.io/badge/license-MIT--No--Attribution-green.svg)
![Huawei Cloud](https://img.shields.io/badge/HuaweiCloud-ModelArts--OBS-red.svg)
![Verify](https://img.shields.io/badge/verify-PASS-brightgreen.svg)

## 1. Overview

Three NLP capabilities built on ModelArts and OBS: custom entity recognition (BERT-NER), Word2Vec embeddings (gensim), and negative sentiment classification (fastText), targeting text analysis scenarios such as telecom tweet corpora.

This practice provides a complete NLP training pipeline: three Jupyter Notebooks run on Huawei Cloud ModelArts, with data stored uniformly in OBS. Training artifacts can be deployed as ModelArts online endpoints, or wrapped as FunctionGraph functions exposed through APIG as REST APIs.

**Target audience**: teams that need to train custom entity recognition, word embedding, or text classification models from their own corpora.

## 2. Table of Contents

- [1. Overview](#1-overview)
- [2. Table of Contents](#2-table-of-contents)
- [3. Architecture Diagram](#3-architecture-diagram)
- [4. Highlights](#4-highlights)
- [5. Cloud Services Involved](#5-cloud-services-involved)
- [6. Prerequisites](#6-prerequisites)
- [7. Quick Start](#7-quick-start)
- [8. Step-by-Step Deployment](#8-step-by-step-deployment)
- [9. Usage / Verification](#9-usage--verification)
- [10. Resource Cleanup](#10-resource-cleanup)
- [11. Detailed Description](#11-detailed-description)
- [12. Dependencies and Acknowledgements](#12-dependencies-and-acknowledgements)
- [13. FAQ / Troubleshooting](#13-faq--troubleshooting)
- [14. Contributing](#14-contributing)
- [15. License](#15-license)
- [16. Contact / Maintainers](#16-contact--maintainers)

## 3. Architecture Diagram

```mermaid
flowchart TB
    subgraph Training
        NB1["NB1 Entity Recognition<br/>CSV→CoNLL → BERT-NER"]
        NB2["NB2 Word Embeddings<br/>gensim Word2Vec"]
        NB3["NB3 Sentiment Classification<br/>fastText classifier"]
    end

    NB1 --> OBS["OBS Object Storage<br/>entity_list.csv / model artifacts"]
    NB2 --> OBS
    NB3 --> OBS

    IAM["IAM Agency<br/>modelarts → OBS OperateAccess"]
    OBS -.-> IAM

    subgraph Inference (optional)
        EP["ModelArts online endpoint"]
        FG["FunctionGraph + APIG<br/>REST classification API"]
    end

    OBS --> EP
    OBS --> FG
```

**Data flow**: local corpus → upload to OBS → train in ModelArts Notebook → store artifacts in OBS → deploy inference endpoint

## 4. Highlights

- **Serverless Training**: ModelArts Notebook on-demand, stop when done, no always-on resources
- **Unified Data Plane**: Training data, CoNLL annotations, and model artifacts all in OBS, permissions managed via IAM Agency
- **One-Click Infrastructure**: Terraform delivers OBS bucket + IAM Agency in two commands
- **Flexible Deployment**: ModelArts online endpoints or FunctionGraph functions
- **Credential Security**: AK/SK injected only via environment variables, never written to disk or baked into images

## 5. Cloud Services Involved

| Huawei Cloud Service | Purpose |
|---|---|
| ModelArts | Notebook training / online inference endpoints |
| OBS | Data / model artifact storage |
| IAM | Agency authorization (ModelArts -> OBS) |
| FunctionGraph (optional) | Inference function wrapper |
| APIG (optional) | REST API exposure |

> All resources can be released at any time after deployment.

## 6. Prerequisites

- A real-name-verified Huawei Cloud account with OBS, ModelArts, and IAM permissions
- Access keys (AK/SK) from IAM, injected via environment variables only
- Terraform >= 1.5 ([download](https://developer.huaweicloud.com/develop/terraform))
- Python >= 3.8 (Notebook runtime is provided by ModelArts)
- Region: `cn-north-4` (default, configurable in `infra/variables.tf`)

## 7. Quick Start

```bash
# 1. Set credentials (runtime only)
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"
export HW_PROJECT_ID="<Project ID>"
export HW_REGION="cn-north-4"

# 2. Infrastructure (OBS bucket + IAM Agency)
cd infra
terraform init
terraform apply -auto-approve

# 3. Upload data (bring your own data; format described in src/scripts/csv_to_conll.py)
cd ../src
pip install -r requirements.txt
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <local-entity-list.csv> custom-nlp-pipeline/entity/telco_entity.csv

# 4. Training: run the three Notebooks in ModelArts Notebook sequentially
```

> See [Step-by-Step Deployment](#8-step-by-step-deployment) for details.

## 8. Step-by-Step Deployment

### Step 1: Infrastructure

```bash
cd infra
terraform init
terraform plan
terraform apply -auto-approve
```

**Expected output**:
```
Apply complete! Resources: 2 added
Outputs:
obs_bucket = "custom-nlp-pipeline-demo"
modelarts_agency_name = "custom-nlp-pipeline-modelarts-obs"
```

### Step 2: Data Upload

Prepare the entity list and tweet corpus (CSV; entity list uses `Text,Type` columns) and upload to OBS:

```bash
cd src
pip install -r requirements.txt

# Upload entity list
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <entity-list.csv> custom-nlp-pipeline/entity/telco_entity.csv

# Upload tweet corpus (optional)
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <tweet-corpus.csv> custom-nlp-pipeline/corpus/tweet_telco.csv
```

**Expected output**: `[OK] <local-file> -> obs://custom-nlp-pipeline-demo/custom-nlp-pipeline/entity/telco_entity.csv`

### Step 3: Model Training (ModelArts Notebook)

1. Go to [ModelArts Console](https://console.huaweicloud.com/modelarts/) -> Development Environment -> Notebook
2. Create a Notebook (recommended: GPU instance or 8C16G+ CPU, disk >= 20GB)
3. Set auto-stop (1 hour)
4. Upload the three Notebooks from `src/notebooks/` and `src/scripts/` to the Notebook working directory
5. Execute in order:

| Order | Notebook | Description | Artifact |
|-------|-----------|-------------|----------|
| 1 | `1-Custom-Entity-Recognizer-ModelArts.ipynb` | CSV -> CoNLL -> BERT-NER fine-tuning | `ner_model/` |
| 2 | `2-Word2Vec-Telco-ModelArts.ipynb` | gensim Word2Vec (sg=1, 100-dim) | `vectors.bin` |
| 3 | `3-Negative-Classifier-ModelArts.ipynb` | fastText negative sentiment classifier | `negative_classifier.bin` |

6. **Stop the Notebook instance immediately** after training (console operation)

### Step 4: Inference Verification

Run the verification code included in each Notebook:

```python
# Entity recognition
predict_entities("I just bought a new iPhone X ...")  # -> DEVICE entities

# Word embeddings
model.wv.most_similar('iphone')  # -> similar words

# Sentiment classification
model.predict("This product is terrible")  # -> ('__label__NEGATIVE', 0.9)
```

## 9. Usage / Verification

### Verification 1: Infrastructure

```bash
# Confirm OBS bucket exists
python -c "from huaweicloudsdkobs.v3.obs_client import ObsClient; \
  c = ObsClient(access_key_id='$HW_ACCESS_KEY', secret_access_key='$HW_SECRET_KEY', \
  server='https://obs.cn-north-4.myhuaweicloud.com'); \
  print(c.headBucket(bucketName='custom-nlp-pipeline-demo').status)"
# Expected: 200
```

### Verification 2: Training Artifacts

After running the three Notebooks in ModelArts, confirm model artifacts exist:
- `ner_model/` directory with `pytorch_model.bin`
- `vectors.bin` word embedding file
- `negative_classifier.bin` classifier model

### Verification 3: Online Inference (Optional)

Deploy a ModelArts online endpoint and call the inference API to confirm results.

> Please verify the above steps yourself after deployment. If the actual output does not match this document, check your environment configuration (credentials / region / ModelArts instance spec) and retry.

## 10. Resource Cleanup

```bash
# 1. Stop and delete the ModelArts Notebook instance (console operation)
# 2. Delete training artifacts from the OBS bucket (if desired)
# 3. Delete infrastructure
cd infra
terraform destroy -auto-approve
```

## 11. Detailed Description

### Capability details

| Capability | Huawei Cloud implementation | Notes |
|------------|------------------------------|-------|
| Custom entity recognition | ModelArts + transformers BERT-NER (CSV -> CoNLL conversion) | Manage the training pipeline yourself |
| Word2Vec embeddings | gensim (sg=1, vector_size=100, window=5, epochs=5) | Hyperparameters configurable |
| Negative sentiment classification | fastText (epoch=25, wordNgrams=2) + optional online endpoint | Lightweight and reproducible |
| Data storage | OBS (private) | Unified storage for data and artifacts |
| Access control | IAM Agency (modelarts -> OBS OperateAccess) | Key-free access |

### Business Scenario Details

#### 1. Custom Entity Recognition (BERT-NER)

**Business Value**: Automatically identifies device brands and models mentioned in massive volumes of user tweets, supporting:

- **Device Market Share Analysis**: Count brand mentions (Apple, Samsung, Android) in user discussions to inform market decisions
- **Competitor Monitoring**: Track competitor product mentions (iPhone, Galaxy, Pixel) in real-time feedback
- **Issue Correlation Analysis**: Correlate device models with network quality issues (e.g., "frequent dropouts with specific phone models in certain areas")

**Technical Implementation**:

- Input: Device name list (CSV: `Text,Type`) + raw tweet corpus
- Processing: CSV annotation → CoNLL sequence labeling format → BERT fine-tuning (Token Classification)
- Output: NER model supporting custom entity types

**Typical Output Example**:
```
Input: "I just bought a new iPhone X and my Samsung Galaxy is amazing!"
Output: [("iPhone X", "DEVICE"), ("Samsung Galaxy", "DEVICE")]
```

> **Note**: This demo uses device names as entity seeds. Production environments should supplement with context-annotated corpora to improve model accuracy.

---

#### 2. Word2Vec Embeddings (gensim)

**Business Value**: Train domain-specific word embedding models to provide semantic features for downstream NLP tasks:

- **Similar Word Recommendation**: Based on word vector similarity, recommend similar Q&A for customer service systems
- **Text Clustering**: Cluster similar-themed tweets to discover hot discussion topics
- **Feature Enhancement**: Use word vectors as input features for downstream classification models to improve accuracy

**Technical Implementation**:

- Input: Domain corpus (telecom tweets)
- Processing: gensim Word2Vec (skip-gram mode, 100-dimensional vectors)
- Output: Word embedding model (`vectors.bin`)

**Typical Output Example**:
```python
# Find words most similar to "iphone"
model.wv.most_similar('iphone', topn=5)
# Output: [('iphone4s', 0.89), ('android', 0.85), ('smartphone', 0.82), ...]
```

> **Use Case**: When generic word embeddings (e.g., pre-trained models) cannot cover domain-specific vocabulary (e.g., telecom industry terms, product models), use this pipeline to train domain embeddings.

---

#### 3. Negative Sentiment Classification (fastText)

**Business Value**: Automatically identify negative sentiment in user feedback, supporting:

- **Public Opinion Early Warning**: Monitor negative complaints on social media in real-time and respond quickly
- **Service Quality Assessment**: Track negative feedback ratios by time/region to evaluate network quality and service levels
- **Ticket Triage**: Automatically escalate high-risk negative feedback for priority handling

**Technical Implementation**:

- Input: Tweet corpus + keyword rule-based labeling (negative keywords: `cheated/annoyed/frustrated`; positive keywords: `Awesome/Hero/Yay`)
- Processing: fastText text classification (wordNgrams=2, epoch=25)
- Output: Binary classification model (NEGATIVE / POSITIVE)

**Typical Output Example**:
```python
model.predict("Terrible service, my phone has no signal for 3 days!")
# Output: ('__label__NEGATIVE', 0.94)

model.predict("Awesome network speed at the stadium!")
# Output: ('__label__POSITIVE', 0.91)
```

> **Note**: This demo uses keyword rules for automatic labeling, suitable for cold start. Production environments should use human-annotated data or combine with sentiment dictionaries to improve accuracy.

---

### Capability Comparison and Selection Guide

| Capability | Use Case | Model Size | Inference Latency | Recommended Scenario |
|------------|----------|-------------|-------------------|----------------------|
| BERT-NER | Entity extraction, slot filling | 110M params | High (GPU) | High-precision entity recognition |
| Word2Vec | Word features, similarity | Medium (vocab size) | Low | Feature input for downstream tasks |
| fastText | Text classification, sentiment | Lightweight (~10MB) | Ultra-low | Large-scale classification, real-time inference |

**Pipeline Recommendation**: Build a串联 pipeline—first use BERT-NER for entity extraction, then Word2Vec for word features, finally fastText for sentiment classification—to form a complete text analysis闭环.

| Component | Purpose | Notes |
|-----------|---------|-------|
| ModelArts Notebook | Training and verification | Three Notebooks each handle one training task; GPU/CPU supported |
| OBS | Data and model artifact storage | Training data and artifacts stored together, bucket ACL private |
| IAM Agency | Permission plane | `modelarts` service delegates OBS access, key-free training jobs |
| ModelArts online endpoint (optional) | Online inference | Deploy the classifier as an endpoint, REST calls |
| FunctionGraph + APIG (optional) | Lightweight release | Wrap fastText as a function, expose via APIG |

### Terraform outputs

| Output | Description |
|--------|-------------|
| `obs_bucket` | OBS bucket name (data and model artifact storage) |
| `modelarts_agency_name` | IAM Agency name (referenced when attaching to Notebook) |

### Repository layout

```
├── README.md / README.en.md    # Bilingual guides
├── docs/
│   ├── architecture.md         # Architecture notes
│   └── deployment-guide.md     # Deployment guide
├── infra/
│   └── main.tf                 # OBS bucket + IAM Agency IaC
├── src/
│   ├── requirements.txt        # Script dependencies
│   ├── notebooks/              # Three training Notebooks
│   └── scripts/                # Data conversion and upload scripts
└── others/                     # Process artifacts and audit files
```

## 12. Dependencies and Acknowledgements

**Key dependencies**:
- [transformers](https://github.com/huggingface/transformers) (BERT-NER fine-tuning)
- [gensim](https://github.com/RaRe-Technologies/gensim) (Word2Vec training)
- [fastText](https://github.com/facebookresearch/fastText) (text classification)
- [esdk-obs-python](https://github.com/huaweicloud/esdk-obs-python) (OBS SDK)

**Acknowledgements**: Thanks to the Huawei Cloud developer community and the open-source ecosystem (Hugging Face, gensim, fastText) for their support.

## 13. FAQ / Troubleshooting

| Issue | Resolution |
|-------|------------|
| Notebook cannot access OBS | Check the IAM Agency was created correctly and is attached to the Notebook |
| BERT-NER training is slow | Switch to a GPU instance; or reduce `num_train_epochs` |
| Poor entity recognition | Too little labeled data (device names only); add more contextual labeled corpus |
| fastText install fails | `pip install fasttext` needs a C++ build environment; use `fasttext-wheel` instead |
| Notebook instance keeps running | Check the auto-stop setting and instance status; stop it right after training |
| `terraform init` times out | Network access to GitHub Releases is slow in some regions; see the offline install notes in `docs/deployment-guide.md` |

## 14. Contributing

Issues and pull requests are welcome. Before submitting:

1. Validate new/modified scripts locally and ensure Notebooks reproduce in ModelArts
2. Keep bilingual docs consistent (README.md / README.en.md)
3. Sync new dependencies into `src/requirements.txt`

## 15. License

Licensed under the [MIT No Attribution](LICENSE) license.

## 16. Contact / Maintainers

- **Submitter**: Shang Dongdong
- **Feedback**: [Huawei Cloud Ticket System](https://console.huaweicloud.com/ticket/)

---

> 📖 More docs: `docs/architecture.md` (architecture), `docs/deployment-guide.md` (deployment guide)
