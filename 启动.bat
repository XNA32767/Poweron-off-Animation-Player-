@echo off&cls
title Poweron/off Animation Player 
color 0A
echo ==============================================
echo PY 开关机播放器
echo 开发作者：搞机XNA
echo 创建日期：2026-06-17
echo 当前系统日期：% date%
echo 当前系统时间：% time%
echo 使用提示：将开关机画面素材放入程序同级目录即可使用
echo ==============================================

echo 使用前请安装依赖包，否则无法启动出现错误
echo 开关机画面的名字是 bootanimation.zip shutanimation.zip
echo 开机声音的名字是 bootaudio.mp3 start.wav boot.wav bootaudio.ogg bootaudio.wav start.wav boot.wav start.ogg boot.ogg
echo 开机声音的名字是 shutaudio.mp3 end.wav shutdown.wav bootaudio.ogg shutaudio.wav end.wav shutdown.wav end.ogg shutdown.ogg
echo 如果是其他名字的话，请更改按照要求的名称，否则无法识别
python bootanimation.py
python shutanimation.py
pause>nul
exit