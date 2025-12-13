import argparse
import random
import time
import sys
import pyautogui

#!/usr/bin/env python3
"""
new_button.py

Randomly clicks locations on the screen using pyautogui.

Usage examples:
    python new_button.py --min 0.2 --max 1.0            # infinite clicks
    python new_button.py --clicks 100                   # 100 clicks
    python new_button.py --duration 30                  # run for 30 seconds
    python new_button.py --region 100 100 800 600       # restrict to region (left top right bottom)
"""



pyautogui.FAILSAFE = True  # move mouse to a corner to abort
pyautogui.PAUSE = 0

def region_bounds(region):
        if region:
                left, top, right, bottom = region
                if right <= left or bottom <= top:
                        raise ValueError("Invalid region coordinates")
                return left, top, right, bottom
        w, h = pyautogui.size()
        return 0, 0, w - 1, h - 1

def random_points(bounds):
        left, top, right, bottom = bounds
        x = random.randint(left, right)
        y = random.randint(top, bottom)
        return x, y

def main():
        args = parse_args()
        try:
                bounds = region_bounds(args.region)
        except Exception as e:
                print("Region error:", e, file=sys.stderr)
                sys.exit(1)

        end_time = time.time() + args.duration if args.duration > 0 else None
        clicks_remaining = args.clicks if args.clicks > 0 else None

        try:
                while True:
                        if end_time and time.time() >= end_time:
                                break
                        if clicks_remaining is not None and clicks_remaining <= 0:
                                break

                        x, y = random_point(bounds)
                        try:
                                pyautogui.click(x, y, button=args.button)
                        except pyautogui.FailSafeException:
                                print("Fail-safe triggered. Exiting.", file=sys.stderr)
                                break
                        except Exception as e:
                                print("Click error:", e, file=sys.stderr)

                        if clicks_remaining is not None:
                                clicks_remaining -= 1

                        sleep_t = random.uniform(max(0, args.min), max(args.min, args.max))
                        time.sleep(sleep_t)
        except KeyboardInterrupt:
                pass

if __name__ == "__main__":
        main()