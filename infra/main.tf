# ============================================================================
# 华为云 自定义 NLP 流水线 Terraform 骨架
# 用途：自定义 NLP 流水线实践的基础设施
#   OBS 桶（数据/模型产物）+ IAM 委托（ModelArts 训练/推理访问 OBS）
# 说明：ModelArts 训练作业与推理端点通常由 SDK/控制台创建（教学样例），
#       本 IaC 只负责数据面与权限面，保持最小可运行。
# ============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.70"
    }
  }

  backend "local" {
    # 生产环境建议改为 OBS 远端状态：
    # backend "s3" {
    #   endpoint = "https://obs.cn-north-4.myhuaweicloud.com"
    #   bucket   = "your-tfstate-bucket"
    #   key      = "custom-nlp-pipeline/terraform.tfstate"
    #   region   = "cn-north-4"
    # }
  }
}

provider "huaweicloud" {
  region = var.region
  # AK/SK 从环境变量读取，不硬编码：
  # export HW_ACCESS_KEY="<AK>"
  # export HW_SECRET_KEY="<SK>"
}

# ============================================================================
# 变量定义
# ============================================================================

variable "region" {
  description = "华为云区域"
  type        = string
  default     = "cn-north-4"
}

variable "project_name" {
  description = "项目名称，用于资源命名前缀"
  type        = string
  default     = "custom-nlp-pipeline"
}

variable "obs_bucket_name" {
  description = "OBS 桶名（全局唯一，请按需修改）"
  type        = string
  default     = "custom-nlp-pipeline-demo"
}

# ============================================================================
# 数据与存储层：OBS 桶
# ============================================================================

resource "huaweicloud_obs_bucket" "data" {
  bucket        = var.obs_bucket_name
  acl           = "private"
  force_destroy = true

  lifecycle {
    prevent_destroy = false
  }
}

# ============================================================================
# 权限层：ModelArts 委托（训练作业/Notebook 访问 OBS）
# 华为云通过 IAM 委托（agency）授予 ModelArts 服务访问 OBS 的权限。
# ============================================================================

resource "huaweicloud_identity_agency" "modelarts_obs" {
  name                  = "${var.project_name}-modelarts-obs"
  description           = "Allow ModelArts to access OBS for training data and model artifacts"
  delegated_service_name = "modelarts"

  domain_roles = [
    "OBS OperateAccess",
  ]
}

# ============================================================================
# 输出
# ============================================================================

output "obs_bucket" {
  description = "OBS 桶名（数据与模型产物存储位置）"
  value       = huaweicloud_obs_bucket.data.bucket
}

output "modelarts_agency_name" {
  description = "ModelArts 委托名称（训练/推理时在控制台或 SDK 中引用）"
  value       = huaweicloud_identity_agency.modelarts_obs.name
}
