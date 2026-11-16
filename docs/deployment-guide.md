# 部署指导书 — 自定义 NLP 流水线

> 本文档指导在华为云 `cn-north-4` 从零部署本实践。

## 一、前置条件

| 项 | 说明 |
|----|------|
| 华为云账号 | 开通 OBS、ModelArts 服务 |
| 访问密钥 | 从 IAM 用户获取 AK/SK，通过环境变量注入（`HW_ACCESS_KEY` / `HW_SECRET_KEY`），不落盘 |
| 工具 | Terraform ≥ 1.5、Python 3、ModelArts Notebook（或本地替代） |
| 数据 | 自备实体列表与推文语料（CSV 格式见 `src/scripts/csv_to_conll.py` 说明） |

## 二、基础设施部署（Terraform）

```bash
export HW_ACCESS_KEY="<AK>"
export HW_SECRET_KEY="<SK>"

cd infra
terraform init
terraform plan
terraform apply -auto-approve
```

> apply 前请查看 `terraform plan` 的资源变更清单：本 IaC 仅创建 OBS 桶（对象存储按量计费，空桶无资源占用）与 IAM 委托（免费）。

apply 完成后记录输出：`obs_bucket`、`modelarts_agency_name`。

### 2.1 Provider 离线安装（网络受限时）

`terraform init` 默认从 GitHub Releases 拉取 huaweicloud Provider，国内网络常超时。
两种已验证的解决方式：

**方式 A：本地插件镜像（filesystem_mirror）**

```bash
# 1. 从华为云镜像下载 Provider（替代 GitHub，速度快且稳定）
curl -L -o hw_provider.zip \
  "https://mirrors.huaweicloud.com/terraform/registry.terraform.io/huaweicloud/huaweicloud/terraform-provider-huaweicloud_1.94.0_windows_amd64.zip"

# 2. 解压到本地镜像目录（Windows: %APPDATA%\terraform.d\plugin-mirror）
mkdir -p "$APPDATA/terraform.d/plugin-mirror/registry.terraform.io/huaweicloud/huaweicloud/1.94.0/windows_amd64"
unzip -o hw_provider.zip -d "$APPDATA/terraform.d/plugin-mirror/registry.terraform.io/huaweicloud/huaweicloud/1.94.0/windows_amd64/"

# 3. 配置 CLI 使用本地镜像（~/.terraformrc）
cat > ~/.terraformrc << 'EOF'
provider_installation {
  filesystem_mirror {
    path    = "C:/Users/<user>/AppData/Roaming/terraform.d/plugin-mirror"
    include = ["huaweicloud/huaweicloud"]
  }
  direct {
    exclude = ["huaweicloud/huaweicloud"]
  }
}
EOF

# 4. init
terraform init
```

**方式 B：dev_overrides（仅验证用，跳过 init）**

```bash
cat > ~/.terraformrc << 'EOF'
provider_installation {
  dev_overrides {
    "huaweicloud/huaweicloud" = "C:/Users/<user>/AppData/Roaming/terraform.d/plugin-mirror"
  }
  direct {}
}
EOF
# dev_overrides 模式跳过 terraform init，直接 validate/plan/apply
# 注意：该模式不检查版本约束，仅用于本地验证
```

> 版本约束：`main.tf` 声明 `~> 1.70`，镜像站当前提供 1.94.0（满足约束）。
> Linux 同理，镜像路径改为 `~/.terraform.d/plugin-mirror/`。

## 三、数据准备

```bash
# 1. 准备实体列表与语料（自备 CSV 文件）
#    entity_list.csv      —— 实体列表（Text,Type）
#    tweet_telco.csv      —— 推文语料（每行一句）

# 2. （可选）上传到 OBS，供 ModelArts 训练作业/Notebook 读取
python3 src/scripts/upload_to_obs.py <bucket> \
    <entity_list.csv> custom-nlp-pipeline/entity/telco_entity.csv
python3 src/scripts/upload_to_obs.py <bucket> \
    <tweet_telco.csv> custom-nlp-pipeline/corpus/tweet_telco.csv
```

## 四、模型训练（ModelArts Notebook）

在 ModelArts 控制台创建 Notebook（建议 GPU 实例或 8C16G 以上 CPU 实例，磁盘 ≥ 20GB），
将 `src/notebooks/` 下三个 Notebook 与自备数据、`src/scripts/` 一并上传后顺序执行：

| Notebook | 内容 | 产物 |
|----------|------|------|
| `1-Custom-Entity-Recognizer-ModelArts.ipynb` | CSV→CoNLL → BERT-NER 微调 | `ner_model/` |
| `2-Word2Vec-Telco-ModelArts.ipynb` | gensim Word2Vec（skip-gram, 100 维） | `vectors.bin` / `vectors.txt` |
| `3-Negative-Classifier-ModelArts.ipynb` | fastText 负面情感分类器 | `negative_classifier.bin` |

> 实例管理提示：ModelArts Notebook 按实例规格 × 时长计费（保底型）。请设置**自动停止**
> （控制台 Notebook 详情 → 自动停止，建议 1 小时），训练完成立即停止实例。

## 五、推理验证

三个 Notebook 内均含推理验证代码段：

- **实体识别**：`predict_entities("I just bought a new iPhone X ...")` → 输出 DEVICE 实体
- **词向量**：`model.wv.most_similar('iphone')` → 相似词
- **情感分类**：`model.predict(txt)` → `('__label__NEGATIVE', 0.9)`

## 六、上线（可选）

### 方案 A：ModelArts 在线推理端点

1. 将 `ner_model/`（或 `negative_classifier.bin`）上传 OBS
2. ModelArts 控制台 → 模型管理 → 导入模型（选择 OBS 中的模型目录，指定推理脚本/镜像）
3. 部署为在线服务（选择规格、设置实例数），获取推理 API

### 方案 B：FunctionGraph + APIG（轻量 REST 接口）

将 fastText 分类逻辑封装为 Python 函数：

```python
import fasttext, json

model = fasttext.load_model('/opt/function/code/negative_classifier.bin')

def handler(event, context):
    text = json.loads(event.get('body', '{}')).get('text', '')
    label, prob = model.predict(text, k=1)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'label': label[0], 'probability': prob[0]}),
    }
```

APIG 创建 API 指向该函数，即获得 REST 分类接口。

## 七、清理

```bash
# 停止 ModelArts Notebook 实例（控制台操作）
# 删除 OBS 桶中的训练产物（如需）
cd infra && terraform destroy -auto-approve
```

## 八、常见问题

| 现象 | 处理 |
|------|------|
| Notebook 无法访问 OBS | 检查 IAM 委托是否正确创建，Notebook 挂载委托是否选择正确 |
| BERT-NER 训练慢 | 换 GPU 实例；或减小 `num_train_epochs` |
| 实体识别效果差 | 标注数据太少（仅设备名）；补充带上下文的标注语料 |
| fastText 依赖安装失败 | `pip install fasttext` 需 C++ 编译环境，或使用 `fasttext-wheel` |
| 实例持续运行 | 检查 Notebook 自动停止设置与实例状态，训练完立即停止 |
