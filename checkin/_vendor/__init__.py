"""隨程式附上的第三方套件（只在主機沒有安裝時才用）。

- segno：產生打卡網址的 QR Code（純 Python、BSD-3 授權，原始碼 https://github.com/heuer/segno ，
  版本 1.6.7.dev、commit b11dc29；只放產生 QR Code 需要的檔案，不含 cli.py、helpers.py；
  utils.py 的 `from segno import encoder` 改成相對匯入）。主機有安裝 segno 時優先用已安裝的版本。
"""
