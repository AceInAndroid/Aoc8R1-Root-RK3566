# 完整 root 教程

## 适用条件

这是实测记录，操作主机为 macOS ARM64。目标是 AOC 8R1 / RK3566 / Android 11，内核 `4.19.193 #606`。其他机器必须先确认分区表、容量、U-Boot 和原 boot 的哈希。整理脚本会拒绝不匹配的固件；不要为了继续而删除这些检查。

本次路线为：**打开 ADB → Loader → Maskrom → RAM USBPlug → 完整备份 → 修补 boot → 只写 boot → 安装管理器并授权 Shell → 重启验证**。无需厂商 update 包。本次没有执行解锁、清数据、格式化或修改 vbmeta。

## 1. 打开开发者选项与 USB 调试

进入设置 → 关于设备，连续点击“版本号”。本次弹出的“请输入密码”使用 **`2204`**，通过后打开开发者选项 → USB 调试，允许电脑连接。

这是开发者选项入口密码；不是 ADB RSA 授权码。不同版本可能修改此密码。来源是本机原始 Settings APK 的反编译逻辑，见 [密码证据](../evidence/developer-options-password.md)。

```sh
adb devices
export DEVICE_SERIAL='你的设备序列号'
adb -s "$DEVICE_SERIAL" shell id
adb -s "$DEVICE_SERIAL" shell uname -a
```

本机最初是 `uid=2000(shell)`；`adb root` 返回 `adbd cannot run as root in production builds`。能打开 USB 调试并不意味着已经 root。

## 2. 准备工具与下载文件

需要 Android SDK Platform Tools、Python 3、Git、libusb 和 rkdeveloptool。Release 提供本次使用的 macOS ARM64 二进制，其依赖为 Homebrew libusb；Linux 应从上游编译，Linux 硬件流程本次未验证。

```sh
brew install libusb pkg-config
gh release download v1.0.0 --repo AceInAndroid/Aoc8R1-Root-RK3566 --dir assets
shasum -a 256 -c SHA256SUMS
gzip -dk assets/boot-original-verified.img.gz
gzip -dk assets/boot-magisk-v31.1.img.gz
gzip -dk assets/recovery-original-verified.img.gz
chmod +x assets/rkdeveloptool-macos-arm64
python3 tools/boot_session.py check-files
```

上面 `SHA256SUMS` 的路径以仓库根目录为基准。没有 `gh` 时可从 [Release 页面](https://github.com/AceInAndroid/Aoc8R1-Root-RK3566/releases/tag/v1.0.0) 手动下载全部附件到 `assets/`。

需要自行编译 rkdeveloptool 时，参考 [工具来源](FILES.md)；源码固定在上游提交 `304f073752fd25c854e1bcf05d8e7f925b1f4e14`。不要使用曾用于实验的 `rkdeveloptool-direct-read` 变体。

## 3. 进入 Loader，再加载 RAM 读取工具

断开其他 Rockchip USB 设备。ADB 可以工作时，本机执行下列命令直接进入 Loader，不需要继续尝试按键组合：

```sh
adb -s "$DEVICE_SERIAL" reboot loader
assets/rkdeveloptool-macos-arm64 ld
```

本次显示唯一 Rockusb 设备，VID:PID 为 `2207:350a`，模式 Loader。Rockusb 阶段没有 ADB 序列号可选；不能用 `adb -s` 来选择 Rockusb 目标。

确认目标后，实测流程是先从 Loader 转到 Maskrom：

```sh
assets/rkdeveloptool-macos-arm64 rd 3
assets/rkdeveloptool-macos-arm64 ld
```

待确认 **Maskrom** 后，仅下载下列文件到 RAM：

```sh
assets/rkdeveloptool-macos-arm64 db assets/ram-only-original-ddr-readlimit-adjusted.bin
assets/rkdeveloptool-macos-arm64 ld
```

该 `.bin` **只用于 `db`，不能用 `wl` 或其他升级 Loader 命令写入闪存**。它使用本机原 DDR 和官方 USBPlug 1.17，仅在 RAM 里调整读限制；容器没有 flash-loader 条目。详见 [RAM 工具说明](FINDINGS.md#32-mib-读取限制)。其他板子的 DDR 配置可能不同。

每次重启后，这个 RAM 工具都需要重新加载，脚本不会自动切换模式。

成功运行 RAM USBPlug 后，`ld` 可能仍显示 Maskrom。本次实际写入前的枚举日志就是如此；应以高地址读取正确、容量和分区指纹通过为准，不能只依赖模式名称。公开脚本会检查 Recovery 高地址扇区，拒绝 `0xCC` 填充读取。

## 4. 备份自己的原 boot 与 Recovery

以下在已运行正确 RAM USBPlug 的前提下执行：

```sh
python3 tools/boot_session.py backup --tool assets/rkdeveloptool-macos-arm64
```

整理脚本先检查唯一设备、容量、GPT CRC／分区位置和 U-Boot 哈希，再读取完整 boot（64 MiB）与 Recovery（96 MiB），写到 `work/`。两者必须与已验证原镜像匹配；同型号但不匹配时停止。

将 `work/boot-original-local.img`、`work/recovery-original-local.img` 和备份回执额外复制到可靠存储。**这不是 userdata 备份。** 本次完整 userdata 约 58.7 GB，未完成全量备份。

## 5. Magisk boot 的来源与修补

Release 中的 `boot-magisk-v31.1.img.gz` 已在本次机器上成功验证，仅在原 boot 哈希完全一致时使用。若原 boot 不同，需要用自己机器的原始 boot 重新分析和修补；本仓库的脚本不会支持直接跨版本写入。

本次使用官方 [Magisk v31.1](https://github.com/topjohnwu/Magisk/releases/tag/v31.1) APK。将 APK 的 `assets/boot_patch.sh` 及 ARM64 所需原生文件提取到可执行目录，按官方脚本修补原 boot。原生文件包括 `magiskboot`、`magiskinit`、`magisk`、`init-ld`，具体 APK 路径见 [补丁参数](../evidence/magisk-preparation.json)。本次在 ADB Shell 的独立临时目录完成修补，然后拉回电脑，删除临时准备目录。

修补时使用下列环境，而没有执行管理器“直接安装”来刷写：

```sh
export SOURCEDMODE=true BOOTMODE=false
export KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false
export RECOVERYMODE=false LEGACYSAR=false PREINITDEVICE=metadata
ui_print() { echo "$@"; }
abort() { echo "$@" >&2; exit 1; }
. ./boot_patch.sh ./boot.img
```

仓库提供 [prepare-magisk.sh](../tools/prepare-magisk.sh) 作为当时设备端修补命令的整理副本，必须从已经准备好官方文件和 `boot.img` 的目录执行；它只生成 `new-boot.img`，不会刷分区。这不是完整的自动下载安装器。

修补后比较了 Android v2 boot 头、SHA1、kernel、DTB、second/resource、cmdline、fstab 和 ramdisk；原有条目除 init 外保持一致，原 init 已在补丁内备份。见 [补丁验证](../evidence/candidate-verification.json)。

## 6. 只写 boot 并完整读回

确认第 4 步的本机备份存在，正确 RAM USBPlug 仍在运行，再执行：

```sh
python3 tools/boot_session.py write-candidate --tool assets/rkdeveloptool-macos-arm64 --allow-write
```

脚本固定使用 boot 起始 LBA `55296`、长度 `131072` 扇区（512 字节／扇区），仅允许已知哈希的 64 MiB 镜像。写前比较当前 boot 和本机原始备份；写后完整读回并核对 SHA256。写入或读回失败时尝试写回本机原 boot，并核对恢复结果。USB 断连等情况可能让自动回滚无法完成，此时转到 [恢复说明](ROLLBACK.md)。

成功后重启：

```sh
assets/rkdeveloptool-macos-arm64 rd
adb -s "$DEVICE_SERIAL" wait-for-device
adb -s "$DEVICE_SERIAL" shell getprop sys.boot_completed
```

`wait-for-device` 只代表 ADB 连接，并不表示桌面启动完毕；等待 `sys.boot_completed=1`。

## 7. 安装官方管理器与授权 Shell

```sh
adb -s "$DEVICE_SERIAL" install -r assets/Magisk-v31.1.apk
adb -s "$DEVICE_SERIAL" shell am start -n com.topjohnwu.magisk/.ui.MainActivity
```

本次首次启动提示“需要修复运行环境”，确认后完成环境补全并自动重启。看到管理器正常识别 31.1 后：

1. 进入 **超级用户**。
2. 点击 **授予超级用户权限**。
3. 勾选 **Shell / com.android.shell / SharedUID**。
4. 返回，再执行验证命令。

Magisk v31.1 已改为提前授权，不能一直等待旧版 `su` 弹窗。首次未授权时，`/debug_ramdisk/su -c id` 返回 `Permission denied`，并不表示 boot 一定失败。

## 8. 验证 root 与正常重启

```sh
adb -s "$DEVICE_SERIAL" shell su -c id
adb -s "$DEVICE_SERIAL" shell getenforce
adb -s "$DEVICE_SERIAL" shell su -c 'sha256sum /dev/block/by-name/boot /dev/block/by-name/recovery'
```

本次结果为 `uid=0(root)`，SELinux `Enforcing`。boot 哈希匹配补丁，Recovery 匹配原始备份。

```sh
adb -s "$DEVICE_SERIAL" reboot
adb -s "$DEVICE_SERIAL" wait-for-device
# 等待 sys.boot_completed=1 后：
adb -s "$DEVICE_SERIAL" shell su -c id
```

重启后再次得到 `uid=0(root)` 才能确认持久 root。早期首次安装阶段 PATH 没有 su 时，本次可使用 `/debug_ramdisk/su`；环境修复完成后 `su` 已可直接调用。真实结果见 [重启后证据](../evidence/root-after-reboot.json)。
