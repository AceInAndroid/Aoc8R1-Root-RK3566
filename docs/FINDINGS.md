# 原理与踩坑记录

## ADB 密码的真正位置

密码弹窗出现在“关于设备”连续点击版本号后，是 Settings 的开发者选项入口。`2204` 对应 `enableDevelopmentSettings()`。本次从原 super 的只读副本提取 Settings APK 并分析得到，用户输入后确认有效。并没有修改 Settings APK 或通过 Recovery 删除密码。

## Recovery sideload 不等于 shell

`adb devices` 显示 `sideload` 只表明正在提供 OTA 侧载协议，不提供常规 shell／pull。原厂 Recovery 的 ADB 也可能显示 unauthorized；它与系统里已经批准的正常 ADB 会话并不等同。

## Fastboot 接受内存启动不等于执行成功

Android、FIT、legacy 等临时启动尝试没有得到可用 root ADB，其中一次还使 Fastboot 暂时不响应，需要物理重启。因此没有把 `fastboot boot` 返回 `OKAY` 当作成功证据。

Bootloader Fastboot 曾报告 locked，而系统属性在改 boot 前已经报告 orange / `flash.locked=0`。不同层的报告有冲突；本仓库只声称“本次没有执行解锁命令”，不把结果泛化为所有锁定 RK3566 都接受任何镜像。

## Recovery 实验与恢复

早期在用户许可下只改过 Recovery，目标是获取 root ADB；镜像写入与完整读回一致，但启动后未出现可用 ADB。后来恢复完整原 Recovery，读回校验通过，用户确认回到正常桌面。最终 Magisk root 后再次读取 Recovery 分区，仍匹配原始哈希。

该失败补丁没有作为可用工具发布。成功方法只需 boot，不要求重复这段 Recovery 实验。

## 32 MiB 读取限制

原 Loader／原 USBPlug 对超过绝对 LBA `65536`（32 MiB）范围的读请求会返回 `0xCC` 填充值，工具仍可能报告成功。boot 从 LBA `55296` 开始，64 MiB 的完整读取跨过限制；仅检查 `ANDROID!` 文件头、文件长度或退出码会误判为完整备份。

最终使用本机原始 DDR 与官方 `rk356x_usbplug_v1.17.bin` 组装 RAM 下载容器，在 USBPlug 偏移 `0x975c` 将：

```text
28 00 a0 52  →  08 00 80 12
mov w8, #0x10000  →  mov w8, #-1
```

限制值存入全局地址 `0x459684`，静态分析中读处理路径比较这个界限并填充 `0xCC`。只改 RAM 读取界限，没有改写入处理器，也没有把此工具烧入闪存。下载容器含一个 471 DDR、一个 472 USBPlug，flash-loader 条目数为零，Rockchip CRC 解析通过。

公开的 [build_ram_loader.py](../tools/build_ram_loader.py) 能用原 DDR 和固定上游 USBPlug **离线复现逐字节相同的 RAM 容器**。它不访问 USB 或分区；依赖文件和预期哈希见 [清单](../manifests/files.json)。

修正 RAM 读取后，boot 两次独立读取匹配，ramdisk 解压／CPIO 解析通过；Recovery 同样能完整解析。之后刷写时全分区读回匹配，root 成功后又从 Android 块设备核对，形成了交叉验证。

## 为什么没有使用漏洞列表里的“一键 root”

曾阅读 [rootWithoutUnlockBootloaderList](https://github.com/lokey0905/rootWithoutUnlockBootloaderList/blob/main/README.en.md)。列表是研究入口，不能证明某个 payload 适合这台 RK3566。Qualcomm／MediaTek 专用路径与硬件不符，Dirty Pipe 的上游引入版本也不匹配未改动的 4.19 基线。内核旧版本号或陈旧安全补丁属性均不足以证明具体漏洞可用，厂商可能回移修复。

本次没有执行列表里的内核漏洞程序；最终走的是用户批准的原 boot 修补路线。没有对未知漏洞是否能适配本机作成功承诺。

## Magisk 管理器的两个容易误判之处

首先，刷入后 `magiskd` 以 root 运行，只能说明核心已经起来，不能说明 ADB Shell 获得授权。其次，v31.1 官方改为提前授予超级用户权限，不再依赖旧版交互请求弹窗。本次完成环境修复、在“授予超级用户权限”列表勾选 Shell 后，`su -c id` 才返回 UID 0。

最终验证包括正常启动、一次额外重启后的 root、SELinux 状态和 boot／Recovery 的完整 SHA256；没有逐一回归设备上的所有应用。
