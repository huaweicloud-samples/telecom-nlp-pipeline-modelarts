#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS 数据上传工具

将本地数据文件上传到华为云 OBS 桶，供 ModelArts 训练/推理使用。
依赖：huaweicloudsdkobs 或 obs SDK（如 esdk-obs-python）。

用法：
    export HW_ACCESS_KEY="<AK>"
    export HW_SECRET_KEY="<SK>"
    python3 upload_to_obs.py <bucket> <local_file> <obs_key>

示例：
    python3 upload_to_obs.py custom-nlp-pipeline-demo \
        ../../data/entity_list.csv custom-nlp-pipeline/entity/telco_entity.csv
"""

import os
import sys

# 方式一：使用华为云 OBS Python SDK（推荐，官方 esdk-obs-python）
try:
    from obs import ObsClient
    HAS_OBS_SDK = True
except ImportError:
    HAS_OBS_SDK = False


def upload_with_sdk(bucket: str, local_file: str, obs_key: str) -> None:
    """使用 esdk-obs-python 上传。region 默认可从桶所在区域推导（此处显式给出）。"""
    ak = os.environ.get("HW_ACCESS_KEY", "")
    sk = os.environ.get("HW_SECRET_KEY", "")
    region = os.environ.get("HW_REGION", "cn-north-4")
    endpoint = f"https://obs.{region}.myhuaweicloud.com"

    client = ObsClient(
        access_key_id=ak,
        secret_access_key=sk,
        server=endpoint,
    )
    resp = client.putFile(bucketName=bucket, objectKey=obs_key, filePath=local_file)
    if resp.status < 300:
        print(f"[OK] {local_file} -> obs://{bucket}/{obs_key}")
    else:
        print(f"[FAIL] {resp.status} {resp.errorCode} {resp.errorMessage}")
        sys.exit(1)


def upload_with_obsutil(bucket: str, local_file: str, obs_key: str) -> None:
    """兜底：调用 obsutil 命令行工具（需已配置 AK/SK）。"""
    cmd = (
        f'obsutil cp "{local_file}" "obs://{bucket}/{obs_key}" -f '
        "--acl=private"
    )
    print(f"[CMD] {cmd}")
    ret = os.system(cmd)
    if ret != 0:
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    bucket, local_file, obs_key = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.isfile(local_file):
        print(f"ERROR: 本地文件不存在: {local_file}")
        sys.exit(1)

    if HAS_OBS_SDK:
        upload_with_sdk(bucket, local_file, obs_key)
    else:
        upload_with_obsutil(bucket, local_file, obs_key)


if __name__ == "__main__":
    main()
