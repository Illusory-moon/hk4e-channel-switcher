# hk4e-channel-switcher

在**官方启动器体系内**切换《原神》国服客户端的登录渠道（官服 ⇄ B服）。

全程只使用官方分发的组件与官方 CDN：不修改游戏本体、不破解任何保护、**不附带任何第三方二进制文件**。

> 本仓库只包含操作说明与辅助脚本。所有文件都由你在本机从官方渠道自行获取。
> **请先阅读文末的[免责声明](#免责声明)。**

---

## 为什么写这个

网上流传的换服教程大多有两个问题：

1. 要么只让你「把 `channel` 改成 14」——改完启动会报 `二级地址解析失败 / Not match region`；
2. 要么让你去**网盘下载一个 `PCGameSDK.dll` 塞进游戏目录**——来路不明的 DLL 会接管登录流程，风险极高。

这个仓库记录的是**实测走通**的官方路径：用 B 站官方分发的《原神》PC 安装器（本质是米哈游启动器的渠道版），让它以「接管已有游戏」的方式完成渠道初始化。不需要下载完整游戏，不需要任何第三方文件。

---

## 原理

《原神》国服 PC 端的游戏**本体是同一套**（官方 API 对官服和 B 服返回的下载包地址完全一致），渠道差异只体现在配置与渠道 SDK 上。

渠道信息记录在三个位置：

| 位置 | 作用 |
|---|---|
| `<启动器根目录>\config.ini` | 启动器自己的渠道身份 |
| `<游戏目录>\config.ini` | 游戏启动时读取的渠道配置 |
| `HKCU\Software\miHoYo\HYP\...` | 各渠道实例的游戏路径记录 |

官服与 B 服的实测差异：

| 字段 | 官服（天空岛） | B 服（世界树） |
|---|---|---|
| `channel` | `1` | `14` |
| `sub_channel` | `1` | `0` |
| `cps` | `hyp_mihoyo` | `bilibili` |
| 启动器 `primary_game` | `hyp_cn` | `hk4e_cn` |

**关键点：手工只改 `config.ini` 是不够的。**

游戏启动时要加载对应渠道的登录/分发逻辑，缺失时会连到错误的 dispatch 服务器，随后在登录页报：

```
二级地址解析失败
Not match region
```

所以必须让**渠道版启动器**来完成初始化（它会补上 `plugin_sdk_version` 等运行时信息）。

---

## 前置条件

- Windows 10/11 x64
- 已通过米哈游启动器安装好**官服**《原神》（本文假设在 `E:\miHoYo Launcher`，请按实际路径替换）
- 7-Zip（用于解包安装器）
- Python 3（可选，用提供的辅助脚本时）

---

## 步骤

### 1. 获取官方安装器地址

B 站游戏中心的详情接口会返回当前版本的 PC 安装器直链：

```bash
curl "https://line3-h5-pc-api.biligame.com/game/detail/gameinfo?game_base_id=105667" \
  -H "Referer: https://www.biligame.com/" \
  -H "User-Agent: Mozilla/5.0"
```

> 注意：该接口需要带 `Referer`，否则返回 403。
> 也可以直接用脚本：`python scripts/fetch_installer_url.py`

返回内容里的 `pc_download_link` 形如：

```
https://pkg.biligame.com/games/yuanshen_setup_YYYYMMDD/HHMMSS/yuanshen_setup_YYYYMMDD.exe
```

### 2. 下载安装器

```bash
curl -L \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  -H "Referer: https://www.biligame.com/" \
  -H "Origin: https://www.biligame.com" \
  -o genshin-bili-setup.exe "<上一步拿到的 pc_download_link>"
```

体积约 220–230 MB。**这是启动器安装包，不是完整游戏。**

### 3. 解包（不提权、不安装）

安装器是一个 PE 文件，真实的启动器文件以 **7z 内嵌**的形式附加在 PE 段之后。

```bash
python scripts/extract_launcher.py genshin-bili-setup.exe -o bili-launcher
```

脚本会：定位 7z 签名 → 切出 payload → 调用 `7z x` 解压到 `bili-launcher/`。

解压后目录结构是：

```
bili-launcher/
  1.19.0.382/
    HYP.exe
    launcher.exe
    ...
```

### 4. 摆正目录结构

启动器入口 `launcher.exe` 需要在**版本目录的上一级**：

```
bili-launcher/
  config.ini            ← 首次运行后自动生成
  launcher.exe          ← 从 1.19.0.382/ 复制一份上来
  1.19.0.382/
    HYP.exe
    ...
```

```bash
cp bili-launcher/1.19.0.382/launcher.exe bili-launcher/launcher.exe
```

### 5. 运行 B 服启动器并「定位游戏」

双击 `bili-launcher/launcher.exe`。首次启动会：

- 生成 `config.ini`（`channel=14 / sub_channel=0 / cps=bilibili`）
- 在 `HKCU\Software\miHoYo\HYP\standalone\14_0\hk4e_cn\<launcher_id>` 下登记实例

此时界面右下角显示 **「获取游戏」** 与 **「已安装？定位游戏」**。

点 **「已安装？定位游戏」**，选择**官服客户端根目录**（如 `E:\miHoYo Launcher`）。

启动器会读取已有游戏、匹配版本，并写入渠道运行时信息（`plugin_sdk_version`）。因为两边游戏包同源，**不会重新下载完整客户端**。

### 6. 开始游戏

定位完成后按钮变为「开始游戏」，点击即可。

此时游戏目录下的 `config.ini` 应类似：

```ini
[General]
game_version=7.1.0
channel=14
sub_channel=0
cps=bilibili
uapc={"hk4e_cn":{"uapc":""},"hyp":{"uapc":""}}
wpf_version=7.1.0.48145775
plugin_sdk_version=5.0.4
```

---

## 切回官服

用原官服启动器（`E:\miHoYo Launcher\launcher.exe`）启动即可，它会重新按官服身份初始化配置。

若出现异常，把备份好的官服 `config.ini` 覆盖回 `<游戏目录>\config.ini` 后再启动。

---

## 常见问题

**Q：改完 `config.ini` 直接双击 `YuanShen.exe`，报「二级地址解析失败 / Not match region」？**
A：正常现象。手工改配置缺少渠道 SDK 初始化。请走**步骤 5**，让渠道版启动器接管后再启动。

**Q：启动器显示「获取游戏」，认不出已安装的游戏？**
A：点「已安装？定位游戏」，选择官服根目录（`E:\miHoYo Launcher`），不要选到 `games` 子目录。

**Q：启动器提示要下载几十 GB？**
A：说明选择的目录不对，或版本不匹配。官方两种渠道的游戏包是同一套，正常情况下只会补差异文件。请检查路径后重试，**不要盲目确认大体积下载**。

**Q：为什么不用网上流传的 `PCGameSDK.dll`？**
A：那是 B 站渠道 SDK，来源不明的版本无法校验完整性，且会接管账号登录流程。本方法通过官方启动器获取，全程走官方 CDN。

**Q：更新游戏后失效？**
A：版本更新后安装器 URL 会变，重新执行步骤 1–5 即可。渠道配置若被覆盖，重复步骤 5。

---

## 已验证信息（供参考）

| 项 | 官服 | B 服 |
|---|---|---|
| 启动器 `launcher_id` | `jGHBHlcOq1` | `umfgRO5gh5` |
| 游戏 `game_id`（hyp-connect） | `1Z8W5NHUQb` | `T2S0Gz4Dr2` |

验证环境：Windows 11，米哈游启动器 `1.19.0.382`，游戏 `7.1.0`。

> 以上 ID 可能随版本变化，脚本会动态获取，不要硬编码。

---

## 免责声明

- 本项目为**技术学习与交流**用途，仅包含文档与脚本，**不包含任何米哈游 / 哔哩哔哩的版权文件**。
- 所有游戏、启动器、安装包均由使用者**自行从官方渠道下载**，请遵守相关用户协议。
- 使用方法可能随官方更新而失效。使用造成的任何后果（包括但不限于账号、数据、设备问题）由使用者自行承担。
- 本项目与米哈游（miHoYo / HoYoverse）、哔哩哔哩（bilibili）无任何关联。
- 请勿将本项目用于商业用途，或将解包出的文件二次分发。

---

## 参考

- [《计算机软件保护条例》第十七条（反向工程的合理使用边界）](https://www.gov.cn/gongbao/content/2013/content_2339471.htm)
- 同类开源项目：[GISS（Genshin Impact Server-Switching）](https://github.com/ELPSI/GISS)
