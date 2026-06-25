[app]
title = CropSurvey GT
package.name = cropsurveygt
package.domain = org.cropsurvey
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer,requests,pillow,geopy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
