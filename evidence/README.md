# 证据说明

这些记录来自 2026-11-10 的实际样本，公开前去掉了真实序列号，并将两次内核 boot ID 分别替换为 `BOOT_SESSION_A_REDACTED`／`BOOT_SESSION_B_REDACTED`。没有重写命令输出中的成功／失败结果。

| 文件 | 记录阶段 |
| --- | --- |
| `stock-adb-checks.json` | 密码已解决、boot 未修改时，普通 Shell 和 adb root 失败 |
| `developer-options-password.md` | 原 Settings APK 内固定密码判断的最小节选 |
| `original-image-headers.json` | 原 boot／Recovery 的解析结果 |
| `magisk-preparation.json` | 官方 APK、各 payload 哈希与修补环境 |
| `candidate-verification.json` | 刷入前的静态比对；其中 NOT BOOTED 字段只描述当时阶段 |
| `ram-readlimit-patch.json` | RAM USBPlug 读限制调整的偏移、原指令和校验值 |
| `root-before-reboot.json` | 管理器环境修复及授权 Shell 后的 root 与分区哈希 |
| `root-after-reboot.json` | 额外正常重启后的 root、启动状态、SELinux 和分区哈希 |

原始完整操作日志仅留在本地；公开版没有设备截图、应用列表、电脑绝对路径、原始设备身份或完整系统备份。
