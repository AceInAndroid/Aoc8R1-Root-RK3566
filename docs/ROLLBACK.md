# 恢复原 boot，保留用户数据

本次 root 已成功，因此没有回滚 boot。下列恢复功能继承了本次写入工具的逻辑，公开整理版只完成离线测试。原 Recovery 已在早期实验后实机恢复，最终哈希仍与原件一致。

## 系统还能启动、有 ADB

保留自己的 `work/boot-original-local.img` 及备份回执，在系统内执行：

```sh
export DEVICE_SERIAL='你的设备序列号'
adb -s "$DEVICE_SERIAL" reboot loader
assets/rkdeveloptool-macos-arm64 ld
assets/rkdeveloptool-macos-arm64 rd 3
```

待 `ld` 确认 Maskrom 后：

```sh
assets/rkdeveloptool-macos-arm64 db assets/ram-only-original-ddr-readlimit-adjusted.bin
python3 tools/boot_session.py restore-original --tool assets/rkdeveloptool-macos-arm64 --allow-write
assets/rkdeveloptool-macos-arm64 rd
```

脚本只写 boot LBA `55296`，完整读回 64 MiB，要求原 boot 的 SHA256 为：

```text
76367bf27f95c77f571990c9be077a37d6dc9ad9dc8c53cbcf072e2ac3e43140
```

这只恢复 boot。Magisk 自己在 `/data/adb` 创建的配置和管理器 APK 不会因此自动删除；不要为了“清理”而擦除 userdata 或 metadata。若要进一步卸载，待正常启动后另行处理。

## 卡开机、没有 ADB

本次机器有音量＋和电源键；USB 连接时按住音量＋配合短按电源启动，曾进入 bootloader／Loader。不同当前模式和按键时序的表现不稳定，不保证固定长按秒数就一定进入 Loader。持续按键可能循环重启；应以电脑 `ld` 的实际枚举为准。

进入 Loader／Maskrom 后按上面的 RAM 加载和恢复步骤操作。Fastboot 与 Rockusb Loader 不是同一协议，`fastboot devices` 有设备不代表 `rkdeveloptool` 可以使用。无法进入任何可写模式时，停止继续刷写，保留备份查明硬件恢复入口。

Recovery 菜单只选择 `Reboot system now` 等正常重启项；不要选择 wipe／factory reset。当前 Recovery 是原始版本，不需要因为 Magisk root 再次修改 Recovery。

## 缺少本机备份时

公开脚本要求 `work/` 中存在先前备份和回执，避免把共享镜像当成自己机器的原件。缺失时不要伪造回执或跳过检查。Release 提供本次原始 boot／Recovery用于研究和匹配固件恢复；必须先独立确认是完全相同的固件与分区布局，再决定如何恢复。

所有带 `loader-masked` 名称的历史读出文件都不是有效备份，仓库没有发布这些文件。尤其不能把早期读出的全 `0xCC` 内容写回设备。
