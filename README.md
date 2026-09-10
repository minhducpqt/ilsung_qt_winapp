# QT Windows App

Ứng dụng desktop offline dùng Python 3.11+ và PySide6 (Qt). Phát triển được trên macOS để kiểm tra giao diện, sau đó build file `.exe` trên Windows.

## Yêu cầu

- Python 3.11 trở lên
- Không cần database ở phiên bản đầu

## 1. Chạy trên macOS

```bash
chmod +x scripts/run.sh
./scripts/run.sh
```

Script tự tạo `.venv` nếu chưa có, cài `requirements.txt`, rồi chạy `main.py`.

## 2. Chạy trên Windows

```bat
scripts\run.bat
```

Script tự tạo `.venv` nếu chưa có, cài `requirements.txt`, rồi chạy `main.py`.

## 3. Build Windows

```bat
scripts\build_windows.bat
```

**Lưu ý quan trọng:** không build file `.exe` Windows trên macOS. PyInstaller tạo binary theo hệ điều hành đang chạy, nên file build trên macOS sẽ không phải `.exe` và không chạy được trên Windows.

Muốn tạo `QTWinApp.exe` thì phải chạy `scripts\build_windows.bat` trên một trong các môi trường sau:

- Máy Windows
- Windows VM
- GitHub Actions Windows runner

## 4. File sau khi build

```text
dist\QTWinApp\QTWinApp.exe
```

Đây là bản folder (không dùng `--onefile`). Copy cả thư mục `dist\QTWinApp\` sang máy Windows khác. Máy đích không cần cài Python.

## Cấu trúc

```text
QT_winapp/
├── main.py
├── requirements.txt
├── QTWinApp.spec
├── README.md
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   ├── config.py
│   ├── styles.py
│   └── resources/
├── scripts/
│   ├── run.sh
│   ├── run.bat
│   └── build_windows.bat
├── build/
└── dist/
```

## Phụ thuộc

- `PySide6-Essentials` (Qt Widgets, đủ cho app này)
- `PyInstaller`
