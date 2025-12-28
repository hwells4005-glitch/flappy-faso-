[app]
title = Flappy Faso
package.name = flappyfaso
package.domain = org.faso
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,mp3
version = 0.1
requirements = python3,kivy==2.2.0,android

orientation = portrait
fullscreen = 0
android.permissions = INTERNET

# Architecture
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Important pour GitHub Actions
p4a.branch = release-2022.12.20

[buildozer]
log_level = 2
warn_on_root = 1
