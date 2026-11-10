# AOC 8R1 Root · RK3566 · Android 11

本仓库记录一台 **AOC 8R1（RK3566 / Android 11）** 的实际 root 过程：找回开发者选项入口，使用 Rockusb 备份原分区，再写入由本机原始 boot 修补的 **Magisk v31.1 boot**。最终 ADB Shell 返回 `uid=0(root)`，正常重启后仍然有效。

**本次没有清除用户数据，没有执行 Bootloader 解锁、擦除或格式化。最终写入的是 boot，原 Recovery 已恢复并核对 SHA256。** 这是持久 Magisk root；不是内存临时 root，也不是适用于所有 RK3566 固件的一键工具。

## 下载与阅读顺序

- **[v1.0.0 文件下载](https://github.com/AceInAndroid/Aoc8R1-Root-RK3566/releases/tag/v1.0.0)**：原始 boot、Magisk boot、原始 Recovery、RAM USBPlug、原 DDR、官方 Magisk APK、macOS ARM64 版 rkdeveloptool 及对应源码。
- **[完整 root 教程](docs/ROOT_GUIDE.md)**：从打开 USB 调试到重启验证。
- **[恢复原 boot](docs/ROLLBACK.md)**：保留数据的回滚步骤。
- **[原理、踩坑与失败尝试](docs/FINDINGS.md)**：为什么 sideload 没有 shell、为什么早期备份是假的、为何不继续改 Recovery。
- **[文件来源与使用范围](docs/FILES.md)**、[机器可读校验清单](manifests/files.json)、[SHA256SUMS](SHA256SUMS)。

镜像以 `.gz` 放在 Release，避免把大型固件塞入 Git 历史。Clone 仓库不会自动获得镜像；下载、解压、校验方法见教程。完整 `super` 和用户数据没有发布；本仓库不是完整救砖固件。

## 本次验证范围

| 项目 | 实测结果 |
| --- | --- |
| 设备 | AOC 8R1，RK3566，Android 11，ARM64 |
| 内核 | `4.19.193 #606`，构建时间 `2026-05-28` |
| 日期 | 2026-11-10 |
| 开发者选项密码 | 连点“版本号”后输入 **`2204`**，本次有效 |
| Magisk | 官方 `31.1 (31100)` |
| Root | `uid=0(root) gid=0(root) ... context=u:r:magisk:s0` |
| 重启 | 正常重启一次后再次验证 root 成功 |
| SELinux | `Enforcing` |
| Recovery | 最终分区哈希与原始备份一致 |
| 未验证 | 其他固件、其他批次机器、Windows 流程、所有应用的长期兼容性 |

公开证据经过脱敏，见 [evidence](evidence/)。没有发布真实设备序列号、电脑用户名、内网 IP、已安装应用列表或用户截图。

## 使用已有 root

将示例序列号替换为 `adb devices` 中自己的设备：

```sh
export DEVICE_SERIAL='你的设备序列号'
adb -s "$DEVICE_SERIAL" shell su -c id
adb -s "$DEVICE_SERIAL" shell
su
```

Magisk **v31.1 需要在管理器 → 超级用户 → 授予超级用户权限中预先勾选 Shell**。仅有 `magiskd` 进程，或看到管理器显示“已安装”，都不能代替 `su -c id` 的验证。其他应用也需要单独授权。

## 固件匹配与备份

共享镜像仅对应下列原 boot，**同型号但哈希不同不能直接套刷**：

```text
原 boot:      76367bf27f95c77f571990c9be077a37d6dc9ad9dc8c53cbcf072e2ac3e43140
Magisk boot:  170fc7ec42a0201d7719667e941a30c57a788cab2af6d8995d509d088a2dde52
原 Recovery:  ee1a5c4956cff459cf0c88e4f5701ac9a32a2db6d7ea9b03c4395d78d4dc6bde
```

先保存自己的原 boot／Recovery，再尝试写入。刷 boot 失败可能需要按键进入 Loader 才能恢复；本次没有完整 userdata 备份，“没有执行清数据”不等于能够保证任何失败场景都不丢数据。

## 工具与复现状态

`tools/boot_session.py` 是本次固定分区操作脚本的公开整理版：校验镜像、识别唯一 Rockusb 设备、验证容量／GPT／U-Boot、备份、仅写 boot、完整读回并校验，写入失败时尝试恢复原 boot。写入必须显式加 `--allow-write`。**整理版只做了离线模拟测试，没有再次拿实机刷写；本次实机成功用的是整理前的同类脚本。**

```sh
python3 tools/boot_session.py check-files
python3 -m unittest discover -s tests -v
```

文件属于各自作者或厂商；Rockchip、Magisk 与 AOSP 的来源和许可证范围见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
