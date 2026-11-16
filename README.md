# NLP 流水线（实体识别 / 词向量 / 情感分类）

![License](https://img.shields.io/badge/License-MIT--No--Attribution-green.svg)
![Huawei Cloud](https://img.shields.io/badge/华为云-ModelArts--OBS-red.svg)
![Verify](https://img.shields.io/badge/verify-PASS-brightgreen.svg)

## 1. 简介

基于 ModelArts 与 OBS 构建三条 NLP 能力：自定义实体识别（BERT-NER）、Word2Vec 词向量（gensim）、负面情感分类（fastText），适用于电信推文语料等文本分析场景。

本实践提供一套完整的 NLP 训练流水线，将三个 Jupyter Notebook 部署到华为云 ModelArts 运行，数据统一存放在 OBS 对象存储。训练产物可进一步部署为在线推理端点，或封装为 FunctionGraph 函数通过 APIG 对外提供 REST 接口。

**适用场景**：需要从自有语料训练自定义实体识别、词向量或文本分类模型的团队。

## 2. 目录

- [1. 简介](#1-简介)
- [2. 目录](#2-目录)
- [3. 架构图](#3-架构图)
- [4. 方案亮点](#4-方案亮点)
- [5. 涉及云服务](#5-涉及云服务)
- [6. 前置条件](#6-前置条件)
- [7. 快速开始](#7-快速开始)
- [8. 分步部署](#8-分步部署)
- [9. 使用方法/验证](#9-使用方法验证)
- [10. 清理资源](#10-清理资源)
- [11. 详细说明](#11-详细说明)
- [12. 依赖与致谢](#12-依赖与致谢)
- [13. FAQ/故障排除](#13-faq故障排除)
- [14. 贡献指南](#14-贡献指南)
- [15. 许可证](#15-许可证)
- [16. 联系方式/维护者](#16-联系方式维护者)

## 3. 架构图

```mermaid
flowchart TB
    subgraph 训练态
        NB1["NB1 实体识别<br/>CSV→CoNLL → BERT-NER"]
        NB2["NB2 词向量<br/>gensim Word2Vec"]
        NB3["NB3 情感分类<br/>fastText 分类器"]
    end

    NB1 --> OBS["OBS 对象存储<br/>entity_list.csv / 模型产物"]
    NB2 --> OBS
    NB3 --> OBS

    IAM["IAM 委托<br/>modelarts → OBS OperateAccess"]
    OBS -.-> IAM

    subgraph 推理态（可选）
        EP["ModelArts 在线端点"]
        FG["FunctionGraph + APIG<br/>REST 分类接口"]
    end

    OBS --> EP
    OBS --> FG
```

**数据流**：本地语料 → 上传 OBS → ModelArts Notebook 训练 → 模型产物存 OBS → 部署推理端点

## 4. 方案亮点

- **Serverless 训练**：ModelArts Notebook 按需启动，训练完即停，无常驻资源
- **数据面统一**：训练数据、CoNLL 标注、模型产物统一存放 OBS，权限通过 IAM 委托管理
- **一键基础设施**：Terraform 交付 OBS 桶 + IAM 委托，两条命令完成
- **灵活上线**：训练产物可部署为 ModelArts 在线端点，或封装为 FunctionGraph 函数
- **凭据安全**：AK/SK 仅通过环境变量注入，不落盘、不入镜像

## 5. 涉及云服务

| 华为云服务 | 用途 |
|---|---|
| ModelArts | Notebook 训练 / 在线推理端点 |
| OBS | 数据 / 模型产物存储 |
| IAM | 委托授权（ModelArts → OBS） |
| FunctionGraph（可选） | 推理函数封装 |
| APIG（可选） | REST 接口暴露 |

> 部署完成后可随时释放资源。

## 6. 前置条件

- 华为云账号已实名认证，具备 OBS、ModelArts、IAM 权限
- 获取访问密钥（AK/SK），通过环境变量注入，不落盘
- Terraform ≥ 1.5（[下载地址](https://developer.huaweicloud.com/develop/terraform)）
- Python ≥ 3.8（Notebook 运行环境由 ModelArts 提供）
- 区域：`cn-north-4`（默认，可修改 `infra/variables.tf`）

## 7. 快速开始

```bash
# 1. 设置凭据（仅运行时注入）
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"
export HW_PROJECT_ID="<项目ID>"
export HW_REGION="cn-north-4"

# 2. 基础设施（OBS 桶 + IAM 委托）
cd infra
terraform init
terraform apply -auto-approve

# 3. 上传数据（数据自备，格式见 src/scripts/csv_to_conll.py 说明）
cd ../src
pip install -r requirements.txt
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <本地实体列表.csv> custom-nlp-pipeline/entity/telco_entity.csv

# 4. 训练：在 ModelArts Notebook 中依次运行 src/notebooks/ 下三个 Notebook
```

> 详细步骤见[分步部署](#8-分步部署)。

## 8. 分步部署

### 步骤 1：基础设施

```bash
cd infra
terraform init
terraform plan
terraform apply -auto-approve
```

**预期输出**：
```
Apply complete! Resources: 2 added
Outputs:
obs_bucket = "custom-nlp-pipeline-demo"
modelarts_agency_name = "custom-nlp-pipeline-modelarts-obs"
```

### 步骤 2：数据上传

准备实体列表与推文语料（CSV 格式，实体列表为 `Text,Type` 两列），上传到 OBS：

```bash
cd src
pip install -r requirements.txt

# 上传实体列表
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <实体列表.csv> custom-nlp-pipeline/entity/telco_entity.csv

# 上传推文语料（如有）
python scripts/upload_to_obs.py custom-nlp-pipeline-demo \
    <推文语料.csv> custom-nlp-pipeline/corpus/tweet_telco.csv
```

**预期输出**：`[OK] <本地文件> -> obs://custom-nlp-pipeline-demo/custom-nlp-pipeline/entity/telco_entity.csv`

### 步骤 3：模型训练（ModelArts Notebook）

1. 进入 [ModelArts 控制台](https://console.huaweicloud.com/modelarts/) → **开发环境 → Notebook**
2. 创建 Notebook（建议 GPU 实例或 8C16G 以上 CPU，磁盘 ≥ 20GB）
3. 设置自动停止（1 小时）
4. 将 `src/notebooks/` 下三个 Notebook 与 `src/scripts/` 上传到 Notebook 工作目录
5. 按顺序执行：

| 顺序 | Notebook | 说明 | 产物 |
|------|----------|------|------|
| 1 | `1-Custom-Entity-Recognizer-ModelArts.ipynb` | CSV → CoNLL → BERT-NER 微调 | `ner_model/` |
| 2 | `2-Word2Vec-Telco-ModelArts.ipynb` | gensim Word2Vec（sg=1, 100 维） | `vectors.bin` |
| 3 | `3-Negative-Classifier-ModelArts.ipynb` | fastText 负面情感分类 | `negative_classifier.bin` |

6. 训练完成后**立即停止 Notebook 实例**（控制台操作）

### 步骤 4：推理验证

三个 Notebook 内均含验证代码段，可直接在 Notebook 中运行：

```python
# 实体识别
predict_entities("I just bought a new iPhone X ...")  # → 输出 DEVICE 实体

# 词向量
model.wv.most_similar('iphone')  # → 相似词列表

# 情感分类
model.predict("This product is terrible")  # → ('__label__NEGATIVE', 0.9)
```

## 9. 使用方法/验证

### 验证 1：基础设施

```bash
# 确认 OBS 桶已创建
python -c "from huaweicloudsdkobs.v3.obs_client import ObsClient; \
  c = ObsClient(access_key_id='$HW_ACCESS_KEY', secret_access_key='$HW_SECRET_KEY', \
  server='https://obs.cn-north-4.myhuaweicloud.com'); \
  print(c.headBucket(bucketName='custom-nlp-pipeline-demo').status)"
# 预期输出：200
```

### 验证 2：训练产物

在 ModelArts Notebook 中执行三个 Notebook 后，确认模型产物已生成：
- `ner_model/` 目录存在且含 `pytorch_model.bin`
- `vectors.bin` 词向量文件存在
- `negative_classifier.bin` 分类器模型存在

### 验证 3：在线推理（可选）

部署 ModelArts 在线端点后，调用推理 API 确认返回结果。

> 请在部署完成后按上述步骤自行验证，确认业务功能可用后再投入使用。若验证输出与本文不符，请先排查环境配置（凭据 / 区域 / ModelArts 实例规格）后重试。

## 10. 清理资源

```bash
# 1. 停止并删除 ModelArts Notebook 实例（控制台操作）
# 2. 删除 OBS 桶中的训练产物（如需）
# 3. 删除基础设施
cd infra
terraform destroy -auto-approve
```

## 11. 详细说明

### 能力说明

| 能力 | 华为云实现 | 说明 |
|------|-----------|------|
| 自定义实体识别 | ModelArts + transformers BERT-NER（CSV → CoNLL 转换） | 需自行管理训练管线 |
| Word2Vec 词向量 | gensim（sg=1, vector_size=100, window=5, epochs=5） | 超参可配置 |
| 负面情感分类 | fastText（epoch=25, wordNgrams=2）+ 可选在线端点 | 轻量可复现 |
| 数据存储 | OBS（private） | 统一存放数据与产物 |
| 权限管理 | IAM 委托（modelarts → OBS OperateAccess） | 免密钥访问 |

### 业务场景详解

#### 1. 自定义实体识别（BERT-NER）

**业务价值**：帮助电信运营商从海量用户推文中自动识别提及的设备品牌和型号，支持以下场景：

- **设备市场份额分析**：统计各品牌（Apple、Samsung、Android）在用户讨论中的占比，辅助市场决策
- **竞品监控**：实时追踪竞争对手产品（iPhone、Galaxy、Pixel）在用户反馈中的提及情况
- **故障关联分析**：将设备型号与网络质量问题关联（如"某型号手机在特定区域频繁掉线"）

**技术实现**：

- 输入：设备名称列表（CSV：`Text,Type`）+ 原始推文语料
- 处理：CSV 标注 → CoNLL 序列标注格式 → BERT 微调（Token Classification）
- 输出：支持识别自定义实体类型的 NER 模型

**典型输出示例**：
```
输入文本: "I just bought a new iPhone X and my Samsung Galaxy is amazing!"
输出实体: [("iPhone X", "DEVICE"), ("Samsung Galaxy", "DEVICE")]
```

> **注意**：本示例仅使用设备名称作为实体种子进行演示。生产环境建议补充带上下文的标注语料以提升模型效果。

---

#### 2. Word2Vec 词向量（gensim）

**业务价值**：训练领域特定的词向量模型，为下游 NLP 任务提供语义特征：

- **相似词推荐**：基于词向量相似度，为客服系统推荐相似问题解答
- **文本聚类**：将相似主题的推文聚类，发现用户讨论的热点话题
- **特征增强**：将词向量作为下游分类模型的输入特征，提升模型效果

**技术实现**：

- 输入：领域语料（电信推文）
- 处理：gensim Word2Vec（skip-gram 模式，100 维向量）
- 输出：词向量模型（`vectors.bin`）

**典型输出示例**：
```python
# 查询与 "iphone" 最相似的词
model.wv.most_similar('iphone', topn=5)
# 输出: [('iphone4s', 0.89), ('android', 0.85), ('smartphone', 0.82), ...]
```

> **适用场景**：当通用词向量（如预训练模型）无法覆盖领域特定词汇（如电信行业术语、产品型号）时，可使用本流水线训练领域词向量。

---

#### 3. 负面情感分类（fastText）

**业务价值**：自动识别用户反馈中的负面情感，支撑以下业务场景：

- **舆情预警**：实时监控社交媒体上的负面投诉，快速响应客户问题
- **服务质量评估**：按时间/区域统计负面反馈占比，评估网络质量和服务水平
- **客服工单分流**：将高危负面反馈自动升级，优先处理

**技术实现**：

- 输入：推文语料 + 关键词规则打标（负面关键词：`cheated/annoyed/frustrated` 等；正面关键词：`Awesome/Hero/Yay` 等）
- 处理：fastText 文本分类（wordNgrams=2，epoch=25）
- 输出：二分类模型（NEGATIVE / POSITIVE）

**典型输出示例**：
```python
model.predict("Terrible service, my phone has no signal for 3 days!")
# 输出: ('__label__NEGATIVE', 0.94)

model.predict("Awesome network speed at the stadium!")
# 输出: ('__label__POSITIVE', 0.91)
```

> **注意**：本示例使用关键词规则自动打标，适用于冷启动阶段。生产环境建议使用人工标注数据或结合情感词典提升准确率。

---

### 能力对比与选型建议

| 能力 | 适用场景 | 模型规模 | 推理延迟 | 推荐场景 |
|------|---------|---------|---------|---------|
| BERT-NER | 实体抽取、槽位填充 | 110M 参数 | 高（GPU） | 需要高精度的实体识别 |
| Word2Vec | 词特征、相似度计算 | 中（词表规模） | 低 | 作为下游任务的特征输入 |
| fastText | 文本分类、情感判断 | 轻量（~10MB） | 极低 | 大规模分类、实时推理 |

**组合使用建议**：可构建串联 pipeline——先用 BERT-NER 抽取实体，再用 Word2Vec 获取词特征，最后用 fastText 判断情感，形成完整的文本分析闭环。

### 组件与职责

| 组件 | 用途 | 说明 |
|------|------|------|
| ModelArts Notebook | 训练与验证 | 三个 Notebook 分别承载训练；支持 GPU/CPU |
| OBS | 数据与模型产物存储 | 训练数据、模型产物统一存放，桶 ACL private |
| IAM 委托 | 权限面 | `modelarts` 服务委托代理 OBS，训练作业免密钥访问 |
| ModelArts 在线端点（可选） | 在线推理 | 分类器部署为在线端点，提供 REST 调用 |
| FunctionGraph + APIG（可选） | 轻量上线 | fastText 封装为函数，APIG 暴露 REST 接口 |

### Terraform 输出

| 输出 | 说明 |
|------|------|
| `obs_bucket` | OBS 桶名（数据与模型产物存储位置） |
| `modelarts_agency_name` | IAM 委托名称（Notebook 挂载时引用） |

### 目录结构

```
├── README.md / README.en.md    # 中英文说明
├── docs/
│   ├── architecture.md         # 架构说明
│   └── deployment-guide.md     # 部署指导书
├── infra/
│   └── main.tf                 # OBS 桶 + IAM 委托 IaC
├── src/
│   ├── requirements.txt        # 脚本依赖
│   ├── notebooks/              # 三个训练 Notebook
│   └── scripts/                # 数据转换与上传脚本
└── others/                     # 过程产物与审计文件
```

## 12. 依赖与致谢

**主要依赖**：
- [transformers](https://github.com/huggingface/transformers)（BERT-NER 微调）
- [gensim](https://github.com/RaRe-Technologies/gensim)（Word2Vec 训练）
- [fastText](https://github.com/facebookresearch/fastText)（文本分类）
- [esdk-obs-python](https://github.com/huaweicloud/esdk-obs-python)（OBS SDK）

**致谢**：感谢华为云开发者社区与开源社区（Hugging Face、gensim、fastText）提供的生态支持。

## 13. FAQ/故障排除

| 问题 | 处理 |
|------|------|
| Notebook 无法访问 OBS | 检查 IAM 委托是否正确创建，Notebook 挂载委托是否选择正确 |
| BERT-NER 训练慢 | 换 GPU 实例；或减小 `num_train_epochs` |
| 实体识别效果差 | 标注数据太少（仅设备名）；补充带上下文的标注语料 |
| fastText 依赖安装失败 | `pip install fasttext` 需 C++ 编译环境，或使用 `fasttext-wheel` |
| Notebook 实例意外运行 | 检查自动停止设置与实例状态，训练完立即停止 |
| `terraform init` 超时 | 国内网络访问 GitHub Releases 超时，参考 `docs/deployment-guide.md` 的离线安装方案 |

## 14. 贡献指南

欢迎提交 Issue 与 Pull Request。提交前请确保：

1. 新增/修改脚本通过本地运行验证，Notebook 可在 ModelArts 环境复现
2. 文档改动保持中英双语同步（README.md / README.en.md）
3. 新增依赖同步更新 `src/requirements.txt`

## 15. 许可证

本实践采用 [MIT No Attribution](LICENSE) 许可证。

## 16. 联系方式/维护者

- **提交者**：尚冬冬
- **问题反馈**：[华为云工单系统](https://console.huaweicloud.com/ticket/)

---

> 📖 更多文档：`docs/architecture.md`（架构说明）、`docs/deployment-guide.md`（部署指导书）
