# 🎵 Lyric Particle Clock（音樂粒子時鐘）

**全螢幕、會隨音樂跳動的粒子時鐘，並且在你自己的電腦上自動辨識、同步顯示歌詞。** 當螢幕保護程式很酷。

[English](README.md) · [線上展示](https://mint-hub-hash.github.io/lyric-particle-clock/) · MIT 授權

!\[demo](docs/demo.gif)

## 功能

* **粒子時鐘**：3200 個粒子每秒重新組成 `HH:MM:SS`，純 HTML5 Canvas，不用安裝或建置。
* **隨聲音反應**：麥克風、本機音樂檔或內建演示節拍；鼓點會讓粒子炸開並換色。
* **10 種上下起伏模式**：按 `1`–`9`、`0` 切換，或自動輪播（正弦波浪、頻譜柱、鏡像展開、中心漣漪、呼吸縮放、彈跳、瀑布、隨機顫動、雙螺旋、帘幕下垂）。
* **自動同步歌詞**：

  1. **本機 AI（建議）**：`lyrics\\\_server.py` 自動下載輕量 Whisper 模型（faster-whisper）在你的電腦上辨識歌詞，辨識到哪就顯示到哪，音訊不會上傳。
  2. **LRCLIB 查詢**：沒有本機服務時，依標籤／檔名到 [LRCLIB](https://lrclib.net) 查找逐句歌詞（GitHub Pages 版本可用）。
  3. **手動**：選歌時一起選同名 `.lrc`。
* 螢幕保護程式手感：按鈕自動隱藏、`F` 全螢幕、空白鍵暫停、`\\\[` `]` 微調歌詞快慢。

## 快速開始

```bash
git clone https://github.com/mint-hub-hash/lyric-particle-clock
cd lyric-particle-clock
# 直接用瀏覽器開 index.html，或用上面的線上展示

# 想要本機 AI 自動歌詞（Python 3.9+）：
python lyrics\\\_server.py --model medium --lang zh --trad
```

首次執行會自動安裝 faster-whisper 並下載模型（medium 約 1.5GB）。RTX 3050 6GB 這類顯卡跑 `small`／`medium` 都沒問題；沒有 NVIDIA 顯卡會自動改用 CPU（較慢）。

只想要 `.lrc` 檔：`python lyrics\\\_server.py --lrc "歌曲.mp3"`

## 已知限制

* 唱歌比說話難辨識，伴奏很大聲時可能漏字或錯字，可用 `\\\[` `]` 微調或載入手製 `.lrc`。
* 網頁無法直接擷取系統播放的聲音，需用「立體聲混音」之類的裝置當麥克風。
* 目前介面為中文，歡迎協助翻譯。

## 授權與致謝

MIT。感謝 faster-whisper、OpenAI Whisper、LRCLIB、OpenCC。專案不內建任何有版權的歌詞。

