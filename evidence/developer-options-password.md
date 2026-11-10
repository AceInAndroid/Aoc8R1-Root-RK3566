# 开发者选项密码证据

原路径：`/system_ext/priv-app/Settings/Settings.apk`。

原 APK SHA256：`d7643677a0e67a7b3f6eaed2e4909eae7f1672161dd846b6fff2a3bc491a13ce`。

JADX 反编译类：`com.android.settings.deviceinfo.BuildNumberPreferenceController`，`PasswordDialog()` 的确认按钮监听器。原本地反编译文件约第 212 行，关键判断节选：

```java
if (BuildNumberPreferenceController.this.myEditText.getText().toString().equals("2204")) {
    BuildNumberPreferenceController.this.passwordDialog.dismiss();
    BuildNumberPreferenceController buildNumberPreferenceController = BuildNumberPreferenceController.this;
    buildNumberPreferenceController.passwordDialog = null;
    buildNumberPreferenceController.mMetricsFeatureProvider.action(
        ((AbstractPreferenceController) BuildNumberPreferenceController.this).mContext,
        847, Pair.create(848, 1));
    BuildNumberPreferenceController.this.enableDevelopmentSettings();
    return;
}
```

`enableDevelopmentSettings()` 调用 `DevelopmentSettingsEnabler.setDevelopmentSettingsEnabled(context, true)`。用户在本次设备输入 `2204` 后确认密码通过、USB 调试开启；随后 ADB 授权连接，初始 `id` 为普通 Shell，见 `stock-adb-checks.json`。

该密码不代表所有 AOC／RK3566 固件的通用密码。本仓库没有发布完整 Settings APK，也没有重新打包或替换它。
