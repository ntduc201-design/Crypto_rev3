[app]
title = Crypto Master Pro
package.name = cryptomaster
package.domain = org.cryptomaster
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0

# python3 + openssl: bắt buộc để urllib gọi HTTPS; certifi: kho chứng chỉ CA
requirements = python3,kivy==2.3.0,certifi,openssl,pyjnius,android

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
