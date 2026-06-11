# runtime_hook.py
# Runs BEFORE main.py in PyInstaller exe only.
import os

# Force Qt to not apply DPI scaling — matches script-mode behavior.
# Without this, PyInstaller's bootloader sets DPI awareness differently
# than a normal python process, causing figure bottom to be clipped.
os.environ['QT_SCALE_FACTOR'] = '1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'

import matplotlib
matplotlib.rcParams['figure.autolayout'] = False
matplotlib.rcParams['figure.constrained_layout.use'] = False
matplotlib.rcParams['figure.dpi'] = 100

print("[runtime_hook] applied")
