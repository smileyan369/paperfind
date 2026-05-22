"""论文搜搜 — 本地启动入口。显示启动动画，服务就绪后自动进入应用。"""
import ctypes
import os
import sys
import logging
import threading
import time

if getattr(sys, 'frozen', False):
    # Suppress all console/log output when running as packaged .exe
    logging.basicConfig(level=logging.CRITICAL, handlers=[])

import uvicorn
import webview

SERVER_URL = "http://127.0.0.1:8001"

SPLASH_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    user-select: none;
    -webkit-user-select: none;
  }
  .splash { text-align: center; }
  .logo {
    width: 80px; height: 77px;
    margin: 0 auto;
    animation: pulse 1.8s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.65; transform: scale(0.92); }
  }
  h2 {
    color: #e8e8f0;
    font-size: 26px;
    margin-top: 22px;
    font-weight: 600;
    letter-spacing: 6px;
  }
  .dots { margin-top: 26px; display: flex; gap: 10px; justify-content: center; }
  .dots span {
    width: 9px; height: 9px; border-radius: 50%;
    background: #7e14ff;
    animation: bounce 1.3s ease-in-out infinite;
  }
  .dots span:nth-child(2) { animation-delay: 0.16s; }
  .dots span:nth-child(3) { animation-delay: 0.32s; }
  .dots span:nth-child(4) { animation-delay: 0.48s; }
  @keyframes bounce {
    0%, 100% { transform: translateY(0); opacity: 0.35; }
    50% { transform: translateY(-14px); opacity: 1; }
  }
  .status { color: #777; font-size: 13px; margin-top: 20px; letter-spacing: 1px; }
</style>
</head>
<body>
<div class="splash">
  <div class="logo">
    <svg width="80" height="77" viewBox="0 0 48 46" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path fill="#7e14ff" d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z"/>
    </svg>
  </div>
  <h2>论文搜搜</h2>
  <div class="dots"><span></span><span></span><span></span><span></span></div>
  <p class="status">正在启动服务...</p>
</div>
<script>
  var attempts = 0;
  function check() {
    attempts++;
    fetch('http://127.0.0.1:8001/api/keywords')
      .then(function(r) {
        if (r.ok) {
          document.querySelector('.status').textContent = '启动成功，即将进入...';
          setTimeout(function() { window.location.href = 'http://127.0.0.1:8001'; }, 400);
        } else if (attempts < 60) {
          setTimeout(check, 300);
        }
      })
      .catch(function() {
        if (attempts < 60) setTimeout(check, 300);
        else document.querySelector('.status').textContent = '启动超时，请重启应用';
      });
  }
  setTimeout(check, 600);
</script>
</body>
</html>
"""


def _start_uvicorn():
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8001,
        log_level="warning",
    )


def _set_window_icon():
    """Background thread: wait for GUI window to appear, then set its title-bar icon."""
    WINDOW_TITLE = "论文搜搜"
    for _ in range(50):  # poll up to 5 seconds
        time.sleep(0.1)
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if hwnd:
            WM_SETICON = 0x0080
            ICON_BIG = 0
            ICON_SMALL = 1
            # Load icon from .exe (frozen) or local file (dev)
            if getattr(sys, 'frozen', False):
                icon_src = sys.executable
                hicon = ctypes.windll.user32.LoadImageW(
                    None, icon_src, 1, 32, 32, 0x00000010
                )
            else:
                icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
                if not os.path.exists(icon_path):
                    break
                hicon = ctypes.windll.user32.LoadImageW(
                    None, icon_path, 1, 32, 32, 0x00000010
                )
            if hicon:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
            break


def main():
    # Start backend server in daemon thread
    threading.Thread(target=_start_uvicorn, daemon=True).start()

    # Start icon-setter thread (polls for the window HWND)
    threading.Thread(target=_set_window_icon, daemon=True).start()

    # Show desktop window: splash first, auto-navigates to app when ready
    window = webview.create_window(
        title="论文搜搜",
        html=SPLASH_HTML,
        width=1280,
        height=800,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
