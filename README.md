# Crypto Master Pro - bản Kivy / APK

Gồm: `main.py` (giao diện 7 tab), `core.py` (lõi xử lý + bộ lọc), `buildozer.spec`,
`.github/workflows/build-apk.yml`.

## Cách 1 - Build APK bằng GitHub (không cần máy mạnh)
1. Tạo repo GitHub (Private cũng được), tải toàn bộ thư mục này lên (giữ nguyên `.github/`).
2. Vào tab **Actions** -> **Build APK** -> **Run workflow**. Lần đầu mất khoảng 25-40 phút.
3. Xong, mở lần chạy đó -> mục **Artifacts** -> tải `CryptoMaster-apk` (giải nén ra file `.apk`).
4. Chép sang điện thoại, mở file, cho phép "Cài ứng dụng không rõ nguồn gốc", bấm Cài đặt.

## Cách 2 - Build trên Linux / WSL / Colab
    pip install buildozer "cython<3"
    buildozer android debug        # APK nằm trong thư mục bin/

## Chạy thử trên máy tính (không cần build)
    pip install -r requirements-desktop.txt
    python main.py

## Dữ liệu
Trên Android, `Filter_Setting.json`, `Settings.json`, `Portfolio_Data.json`,
`Performance_Data.json` nằm trong bộ nhớ riêng của ứng dụng (xóa app = mất dữ liệu).
Nếu app tự thoát, xem `crash_log.txt` cùng thư mục đó.

## Lưu ý
- Giám sát 12H và đối soát nền chỉ chạy khi ứng dụng đang mở hoặc ở nền ngắn hạn;
  Android có thể tạm dừng app khi bị thu hồi bộ nhớ. Gửi Telegram cũng theo đó.
- APK là bản debug (ký bằng khóa debug), đủ để cài dùng cá nhân.
