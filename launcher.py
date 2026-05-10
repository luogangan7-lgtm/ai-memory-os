#!/usr/bin/env python3
import os, sys, platform, subprocess, time, webbrowser

RED = "\033[31m" if os.name != "nt" else ""
GREEN = "\033[32m" if os.name != "nt" else ""
YELLOW = "\033[33m" if os.name != "nt" else ""
CYAN = "\033[36m" if os.name != "nt" else ""
RESET = "\033[0m" if os.name != "nt" else ""

BASE = os.path.dirname(os.path.abspath(__file__))