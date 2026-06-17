# -*- coding: utf-8 -*-
import zipfile
import os
import sys
import cv2
import pygame
import threading
import time
import numpy as np

# ================= 配置 =================
ZIP_PATH = sys.argv[1] if len(sys.argv) > 1 else "shutanimation.zip"
TEMP_DIR = "shut_temp"
WINDOW_NAME = "Goodbye"
# 音频同步补偿系数（可微调，默认1.0）
AUDIO_SYNC_FACTOR = 1.0
# ========================================

# 修复 Windows 中文路径乱码
if sys.platform.startswith("win"):
    import locale
    locale.setlocale(locale.LC_ALL, 'C')

# 全局状态
system_entered = False
paused = False
restart_all = False
restart_current = False
part_idx = 0
loop_idx = 0
img_idx = 0

# 声音线程控制 + 时间戳同步
audio_playing = True
audio_paused = False
audio_thread = None
audio_start_time = 0.0  # 音频启动时间戳
video_start_time = 0.0  # 视频启动时间戳

# ==========================
# 中文路径安全读取图片
# ==========================
def cv2_imread(path):
    try:
        with open(path, "rb") as f:
            img_data = f.read()
        img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None

# ==========================
# 声音线程（精准同步版）
# ==========================
def audio_thread_func(sound_path):
    global audio_playing, audio_paused
    try:
        pygame.mixer.init(frequency=44100, buffer=512)  # 减小缓冲区降低延迟
        pygame.mixer.music.load(sound_path)
        pygame.mixer.music.play()
        # 记录音频实际启动时间
        global audio_start_time
        audio_start_time = time.time()
        
        while audio_playing:
            if audio_paused:
                pygame.mixer.music.pause()
                pause_start = time.time()
                while audio_paused and audio_playing:
                    time.sleep(0.01)  # 提升暂停响应速度
                # 暂停结束后，补偿音频播放时间
                if audio_playing and not audio_paused:
                    pause_duration = time.time() - pause_start
                    audio_start_time += pause_duration
                    pygame.mixer.music.unpause()
            time.sleep(0.01)  # 降低音频线程延迟
        pygame.mixer.music.stop()
    except Exception as e:
        print(f"音频线程异常: {e}")
        return

def start_audio(sound_path):
    global audio_thread, audio_playing, audio_paused, audio_start_time
    audio_playing = True
    audio_paused = False
    audio_start_time = 0.0
    audio_thread = threading.Thread(target=audio_thread_func, args=(sound_path,), daemon=True)
    audio_thread.start()

def pause_audio():
    global audio_paused
    audio_paused = True

def resume_audio():
    global audio_paused
    audio_paused = False

def stop_audio():
    global audio_playing
    audio_playing = False

# ==========================
# 工具函数
# ==========================
def clean_temp():
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                else:
                    import shutil
                    shutil.rmtree(fp)
            except:
                pass

def extract_zip():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(TEMP_DIR)

def parse_desc():
    desc_path = os.path.join(TEMP_DIR, "desc.txt")
    with open(desc_path, "rb") as f:
        txt = f.read().replace(b"\r\n", b"\n").decode()
    lines = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]
    w, h, fps = map(int, lines[0].split())
    parts = [l.split() for l in lines[1:]]
    return w, h, fps, parts

def find_sound():
    targets = ["shutaudio.mp3" ,"end.wav" ,"shutdown.wav" ,"bootaudio.ogg" ,"shutaudio.wav" ,"end.wav" ,"shutdown.wav" ,"end.ogg" ,"shutdown.ogg"]
    for root, dirs, files in os.walk(TEMP_DIR):
        for f in files:
            if f.lower() in [t.lower() for t in targets]:
                return os.path.join(root, f)
    for root, dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        for f in files:
            if f.lower() in [t.lower() for t in targets]:
                return os.path.join(root, f)
    return None

# ==========================
# 按键
# ==========================
def check_key():
    global paused, system_entered, restart_all, restart_current
    key = cv2.waitKey(1) & 0xFF
    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
        return "exit"
    if key == 27 or key == ord('x'):
        return "exit"
    elif key == ord(' '):
        paused = not paused
        if paused:
            pause_audio()
        else:
            resume_audio()
    elif key == ord('s'):
        system_entered = True
    elif key == ord('r'):
        restart_all = True
    elif key == ord('R'):
        restart_current = True
    return "continue"

# ==========================
# 播放主逻辑（音画同步核心修复）
# ==========================
def play_animation(w, h, fps, parts):
    global paused, restart_all, restart_current
    global part_idx, loop_idx, img_idx, system_entered
    global video_start_time, audio_start_time
    
    frame_interval = 1.0 / fps  # 每帧理论间隔（秒），保留浮点精度
    sound_path = find_sound()

    # 初始化音视频时间戳
    video_start_time = time.time()
    if sound_path:
        start_audio(sound_path)
        print("🔊 声音已加载")
        # 等待音频启动完成，对齐起始时间
        time.sleep(0.05)
        video_start_time = audio_start_time  # 强制音视频起始时间一致

    while True:
        if restart_all:
            # 重启时重置所有时间戳
            part_idx = loop_idx = img_idx = 0
            system_entered = False
            restart_all = False
            stop_audio()
            time.sleep(0.1)
            if sound_path:
                start_audio(sound_path)
                time.sleep(0.05)
                video_start_time = audio_start_time
        if restart_current:
            loop_idx = img_idx = 0
            restart_current = False

        for pi in range(part_idx, len(parts)):
            part = parts[pi]
            ptype, tloop, pause, folder = part[0], int(part[1]), int(part[2]), part[3]
            pth = os.path.join(TEMP_DIR, folder)
            if not os.path.exists(pth):
                continue
            imgs = sorted([f for f in os.listdir(pth) if f.endswith((".png", ".jpg", ".jpeg"))])
            if not imgs:
                continue
            max_loop = tloop if tloop != 0 else 999

            for li in range(loop_idx, max_loop):
                if system_entered and ptype == "p":
                    break
                
                for ii in range(img_idx, len(imgs)):
                    # 1. 按键检测（优先处理退出/暂停）
                    key_state = check_key()
                    if key_state == "exit":
                        stop_audio()
                        cv2.destroyAllWindows()
                        return
                    while paused:
                        if check_key() == "exit":
                            stop_audio()
                            cv2.destroyAllWindows()
                            return
                        time.sleep(0.01)  # 低延迟暂停等待

                    if system_entered and ptype == "p" or restart_all or restart_current:
                        break

                    # 2. 计算当前帧的目标时间（核心同步逻辑）
                    current_frame_idx = (li * len(imgs)) + ii
                    target_time = video_start_time + (current_frame_idx * frame_interval * AUDIO_SYNC_FACTOR)
                    now = time.time()

                    # 3. 读取并显示帧（最小化耗时）
                    img_path = os.path.join(pth, imgs[ii])
                    frame = cv2_imread(img_path)
                    if frame is None:
                        continue
                    # 提前缩放（可选：预加载所有图片进一步降低耗时）
                    frame = cv2.resize(frame, (w, h))
                    cv2.imshow(WINDOW_NAME, frame)

                    # 4. 精准延迟：确保帧显示时间匹配目标时间
                    sleep_time = target_time - now
                    if sleep_time > 0:
                        # 目标时间未到，精准等待（最小1ms避免卡死）
                        time.sleep(max(0.001, sleep_time))
                        # 等待后刷新窗口
                        cv2.waitKey(1)
                    else:
                        # 超时则立即刷新，避免累积延迟
                        cv2.waitKey(1)

                if system_entered and ptype == "p" or restart_all or restart_current:
                    break
                img_idx = 0
            if system_entered and ptype == "p" or restart_all or restart_current:
                break
            loop_idx = 0

        if not restart_all and not restart_current:
            while True:
                if check_key() == "exit":
                    stop_audio()
                    cv2.destroyAllWindows()
                    return
                time.sleep(0.05)
            break

if __name__ == "__main__":
    print("加载：" + ZIP_PATH)
    clean_temp()
    extract_zip()
    try:
        w, h, fps, parts = parse_desc()
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        sys.exit()

    print("=" * 60)
    print(f" 🎬 帧率：{fps} | 音画同步模式已启用")
    print(" 空格 = 暂停/继续  R = 重放  ESC/X = 退出")
    print("=" * 60)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, w, h)
    play_animation(w, h, fps, parts)
    stop_audio()
    clean_temp()
    print("✅ 已退出")