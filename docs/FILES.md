# 下载文件、来源与复现

所有二进制都放在 [v1.0.0 Release](https://github.com/AceInAndroid/Aoc8R1-Root-RK3566/releases/tag/v1.0.0)。Git 仓库只保存教程、整理脚本、测试和脱敏证据。

## 附件用途

| 文件 | 用途 |
| --- | --- |
| `boot-original-verified.img.gz` | 本次原始 boot，解压后 67,108,864 字节；原件备份／匹配固件恢复 |
| `boot-magisk-v31.1.img.gz` | 本次成功的 Magisk boot，解压后 67,108,864 字节 |
| `recovery-original-verified.img.gz` | 本次原始 Recovery，解压后 100,663,296 字节；成功 root 无需写它 |
| `ddr-original.bin` | 从本机原始 IDB 提取，IDB 哈希验证通过的 59,392 字节 DDR 初始化代码 |
| `rk356x_usbplug_v1.17.bin` | 固定提交中的官方原始 USBPlug，98,708 字节，未修改 |
| `ram-only-original-ddr-readlimit-adjusted.bin` | 161,796 字节 RAM 下载容器，含原 DDR 和调整读限制的 USBPlug；只用于 `db` |
| `Magisk-v31.1.apk` | 官方原件，与官方 Release 摘要一致，用作管理器和修补 payload 来源 |
| `rkdeveloptool-macos-arm64` | 本次实际使用的 macOS ARM64 工具；依赖 Homebrew libusb |
| `rkdeveloptool-source.tar.gz` | 与本次工具对应的固定提交源码及 `config.h`；包含上游许可证 |
| `SHA256SUMS` | 与仓库相同的附件 SHA256 清单；从仓库根目录执行核对 |

`manifests/files.json` 同时包含 `.gz` 和解压后 `.img` 的大小／SHA256。`.gz` 是为了发布重新压缩的无时间戳 gzip，解压后与本次读回／刷入镜像逐字节相同。

没有发布完整 super、userdata、metadata、security 分区、整片 eMMC、GPT 原始二进制、无效的 `0xCC` 备份或失败 Recovery 补丁。原本地完整资料仍保留；公开包仅保留复现这条成功路径需要的资料。

## 上游固定版本

- rkdeveloptool：[`rockchip-linux/rkdeveloptool@304f073752fd25c854e1bcf05d8e7f925b1f4e14`](https://github.com/rockchip-linux/rkdeveloptool/tree/304f073752fd25c854e1bcf05d8e7f925b1f4e14)。本次标准工具未修改上游源码；生成的 `config.h` 设置 `PACKAGE_VERSION` 为 `1.32`。
- 官方原 USBPlug：[`rkbin@975e4c3474713fb23e732a7223bb2ef9e95f05be/bin/rk35/rk356x_usbplug_v1.17.bin`](https://github.com/rockchip-linux/rkbin/blob/975e4c3474713fb23e732a7223bb2ef9e95f05be/bin/rk35/rk356x_usbplug_v1.17.bin)。
- Magisk：[`topjohnwu/Magisk v31.1`](https://github.com/topjohnwu/Magisk/releases/tag/v31.1)，APK SHA256 `89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7`。

## 从附件源码编译 macOS 工具

在仓库根目录、已安装 Xcode Command Line Tools／Homebrew libusb／pkg-config 的机器上：

```sh
tar -xzf assets/rkdeveloptool-source.tar.gz -C work
cd work/rkdeveloptool-source
c++ -O2 -std=c++11 $(pkg-config --cflags libusb-1.0) \
  main.cpp RKBoot.cpp RKComm.cpp RKDevice.cpp RKImage.cpp RKLog.cpp RKScan.cpp crc.cpp \
  $(pkg-config --libs libusb-1.0) -o ../rkdeveloptool-rebuilt
```

公开整理时重新编译通过；上游有两个变长数组的 Clang 扩展警告。重新编译的二进制可能因编译器版本等因素与已发布工具哈希不同，不能把同一份源码等同于可重现构建承诺。Linux 的上游 autogen/configure/make 方式见源码 `Readme.txt`。

## 离线复现 RAM 容器

```sh
python3 tools/build_ram_loader.py
```

输入是 `assets/ddr-original.bin` 与 `assets/rk356x_usbplug_v1.17.bin`，均先核对固定哈希；输出为新建的 `work/ram-loader-reproduced.bin`。脚本保留固定容器头／条目、2048 字节对齐、无 flash-loader 条目及 Rockchip CRC，结果必须匹配：

```text
bef69d6d3c513af830182d9689673e5953df6749417508d87f150f90d6fb806d
```

该步骤不访问任何设备，也不会加载 RAM 工具。
