# AI Banking Dispute Automation Taskforce

An autonomous multi-agent expert team for modernizing banking complaint handling under BNM and FMOS regulatory frameworks.

## 类型

Team 型（多角色协作团队）

## 功能

- 监控投诉入口并执行提示词注入检测、PDF/OCR解析与敏感信息加密
- 完成7类银行争议分类、实体抽取、BNM/FMOS合规时限与披露治理
- 对接核心系统进行核验，并为PASS案件生成退款、冲正与会计分录
- 输出最终客户通知、FMOS申诉告知与实时运营看板同步载荷

## 使用示例

- 帮我搭建一条符合BNM与FMOS要求的银行争议自动化处理流水线。
- 设计一条覆盖受理、核验、清算与通知的银行投诉自动化流程。
- 展示这个团队如何处理PASS、FAIL与人工复核三类争议案件。

## 头像

当前包内已预置占位头像文件，可按需替换为自定义头像：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\Admin\.workbuddy-ai\plugins\marketplaces\my-experts\plugins/dispute-automation-expert-team/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python3 scripts/package_expert.py "C:/Users/Admin/.workbuddy-ai/plugins/marketplaces/my-experts/plugins/dispute-automation-expert-team" "C:/Users/Admin/workbuddy-ai/Aduan Flow"
```
