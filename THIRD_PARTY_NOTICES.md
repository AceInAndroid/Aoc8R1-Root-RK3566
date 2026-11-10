# 文件来源与许可证范围

本仓库包含实测记录、整理脚本和厂商／开源软件生成的镜像。**没有为所有文件统一声明 MIT 或其他重许可。** 第三方文件保留原作者权利，公开整理脚本的原始改写部分采用 GPL-3.0-or-later；上游代码仍受各自许可证约束。

| 内容 | 来源 | 许可证／归属 |
| --- | --- | --- |
| Magisk 31.1 APK 和 boot 中的 Magisk 文件 | [官方 Release](https://github.com/topjohnwu/Magisk/releases/tag/v31.1)、[官方源码](https://github.com/topjohnwu/Magisk/tree/v31.1) | Magisk，GPL-3.0；源码与对应上游许可见官方仓库 |
| rkdeveloptool macOS ARM64 和对应源码附件 | [rockchip-linux/rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool/tree/304f073752fd25c854e1bcf05d8e7f925b1f4e14) | Rockchip，GPL-2.0-or-later；源码附件含 `license.txt` 和构建配置 |
| USBPlug 1.17 与派生 RAM 容器 | [rockchip-linux/rkbin](https://github.com/rockchip-linux/rkbin/tree/975e4c3474713fb23e732a7223bb2ef9e95f05be) | Rockchip 二进制，适用上游授权；本仓库不为其重许可 |
| 原 boot、原 Recovery、原 DDR 与 Magisk boot 中的原始固件部分 | 本次 AOC 8R1 实机只读备份 | 厂商及各组成部分的原权利人；不是官方发布的完整固件 |
| Settings 密码逻辑节选 | 本次固件 Settings APK 的 JADX 反编译片段 | AOSP Settings 与厂商修改；仅保留解释密码判断所需的短片段 |

Release 中镜像的名称只描述本次样本。它们不是 AOC 官方升级包，也没有取得其他固件版本的兼容性认证。
