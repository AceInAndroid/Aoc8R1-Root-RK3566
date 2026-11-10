下载 Release 附件到此目录。该目录只跟踪本说明，镜像和工具不会进入 Git 历史。

从仓库根目录执行：

```sh
gh release download v1.0.0 --repo AceInAndroid/Aoc8R1-Root-RK3566 --dir assets
gzip -dk assets/boot-original-verified.img.gz
gzip -dk assets/boot-magisk-v31.1.img.gz
gzip -dk assets/recovery-original-verified.img.gz
python3 tools/boot_session.py check-files
```

Release 的 `SHA256SUMS` 核对压缩包、工具与 APK；`manifests/files.json` 同时提供解压后镜像的校验值。重复下载时自行处理已存在文件，不要覆盖自己机器的原始备份。
