"""演示数据初始化脚本（幂等，可重复执行）

用途：给系统填充 3 个演示知识库 + 每个库 3 条 FAQ + 1 个示例文档，
      方便面试演示 / 新环境快速体验（企业里类似的操作叫 seed 数据初始化）。

用法（backend 目录）：
    .venv/Scripts/python scripts/seed_demo.py [后端地址，默认 http://localhost:8000]

幂等设计：同名知识库已存在则复用，不会重复创建。
"""
import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
API = f"{BASE}/api/v1"
ADMIN_USER, ADMIN_PASS = "admin", "admin123"

# 3 个演示知识库：客服系统最常见的业务场景
DEMO_KBS = [
    {
        "name": "售后政策库",
        "description": "退款、换货、保修等售后政策问答",
        "faqs": [
            ("退款政策是什么？", "支持 7 天无理由退货；退款将在收到退货商品并质检通过后 3-5 个工作日内原路退回。"),
            ("商品坏了怎么保修？", "整机保修一年，主要部件保修三年；凭购买凭证在官网申请售后，工程师上门或寄修。"),
            ("可以换货吗？", "签收 15 天内出现质量问题可申请换货，往返运费由商家承担；外观完好不影响二次销售即可。"),
        ],
    },
    {
        "name": "产品使用指南库",
        "description": "安装、使用、故障排查指南",
        "faqs": [
            ("产品怎么安装？", "扫描包装盒二维码下载 App，按引导连接 Wi-Fi 并绑定设备，全程约 3 分钟；也可参考说明书第 2 章。"),
            ("设备无法开机怎么办？", "先确认电源适配器连接正常并长按电源键 10 秒；仍无法开机请联系客服报修，保修期内免费维修。"),
            ("支持哪些手机系统？", "App 支持 iOS 13 及以上、Android 9 及以上系统，可在应用商店搜索产品名下载。"),
        ],
    },
    {
        "name": "企业人事制度库",
        "description": "请假、报销、考勤等行政制度问答",
        "faqs": [
            ("请假流程是什么？", "提前 1 天在 OA 系统提交请假申请，直属上级审批；3 天以上需部门负责人加签，紧急情况可电话报备后补流程。"),
            ("差旅报销标准？", "交通实报实销（高铁二等座/经济舱），住宿一线城市 500 元/晚、其他 350 元/晚，餐补每天 100 元；发票需当月提交。"),
            ("考勤迟到怎么处理？", "每月累计迟到 30 分钟内不扣款；超出部分每次扣半天工资；全年累计超过 10 次影响年终绩效评定。"),
        ],
    },
]

# 演示文档：仓库里现成的部署测试文档，上传后走 RAG 检索链路
DEMO_DOC = Path(__file__).resolve().parents[1] / "deploy_test.docx"


def main() -> None:
    client = httpx.Client(timeout=60)

    # 1. 管理员登录
    r = client.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    r.raise_for_status()
    token = r.json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[1/4] 管理员登录成功")

    # 2. 查询已有知识库（幂等：同名跳过）
    existing = client.get(f"{API}/knowledge-bases", headers=headers).json()["data"]
    name_to_id = {kb["name"]: kb["id"] for kb in existing}

    # 3. 逐个创建知识库 + FAQ
    for kb_def in DEMO_KBS:
        name = kb_def["name"]
        if name in name_to_id:
            kb_id = name_to_id[name]
            print(f"[2/4] 知识库「{name}」已存在（id={kb_id}），跳过创建")
        else:
            r = client.post(
                f"{API}/knowledge-bases",
                json={"name": name, "description": kb_def["description"]},
                headers=headers,
            )
            kb_id = r.json()["data"]["id"]
            print(f"[2/4] 知识库「{name}」已创建（id={kb_id}）")

        # 为每个库创建 FAQ（后端会同步做 embedding 写入 FAQ 向量 collection）
        existing_faqs = client.get(
            f"{API}/faqs/knowledge-bases/{kb_id}/faqs", headers=headers
        ).json()["data"]
        existing_questions = {f["question"] for f in existing_faqs}
        for question, answer in kb_def["faqs"]:
            if question in existing_questions:
                print(f"      FAQ「{question}」已存在，跳过")
                continue
            client.post(
                f"{API}/faqs/knowledge-bases/{kb_id}/faqs",
                json={"question": question, "answer": answer},
                headers=headers,
            )
            print(f"      FAQ「{question}」已创建（向量化完成）")

    # 4. 上传示例文档到「产品使用指南库」（异步处理，之后可看到状态流转）
    guide_id = name_to_id.get("产品使用指南库")
    if guide_id is None:  # 本次新建的情况，重新查一次
        guide_id = {kb["name"]: kb["id"] for kb in client.get(
            f"{API}/knowledge-bases", headers=headers
        ).json()["data"]}["产品使用指南库"]
    if DEMO_DOC.exists():
        docs = client.get(
            f"{API}/knowledge-bases/{guide_id}/documents", headers=headers
        ).json()["data"]
        if any(d["filename"] == DEMO_DOC.name for d in docs):
            print(f"[3/4] 文档「{DEMO_DOC.name}」已存在，跳过上传")
        else:
            with open(DEMO_DOC, "rb") as f:
                r = client.post(
                    f"{API}/knowledge-bases/{guide_id}/documents",
                    files={"file": (DEMO_DOC.name, f)},
                    headers=headers,
                )
            print(f"[3/4] 示例文档「{DEMO_DOC.name}」已上传，后台向量化处理中")
    else:
        print(f"[3/4] 示例文档不存在：{DEMO_DOC}，跳过")

    print("[4/4] 初始化完成！打开 http://localhost 体验：")
    print("      FAQ 秒回：试聊中问「退款政策是什么？」")
    print("      RAG 流式：问文档相关的问题，观察逐字输出与引用来源")


if __name__ == "__main__":
    main()
