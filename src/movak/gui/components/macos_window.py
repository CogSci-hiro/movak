from __future__ import annotations

import ctypes
import ctypes.util
import sys

from PyQt6.QtWidgets import QWidget

from ..style.palette import Palette

NS_WINDOW_TITLE_HIDDEN = 1
NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW = 1 << 15


def apply_integrated_macos_chrome(widget: QWidget) -> None:
    """Blend native macOS titlebar chrome into the app while keeping traffic lights."""

    if sys.platform != "darwin":
        return

    objc_path = ctypes.util.find_library("objc")
    if not objc_path:
        return

    objc = ctypes.cdll.LoadLibrary(objc_path)
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.restype = ctypes.c_void_p

    def _selector(name: str) -> ctypes.c_void_p:
        return ctypes.c_void_p(objc.sel_registerName(name.encode("utf-8")))

    def _send(receiver: int, selector: str, *args, restype=ctypes.c_void_p, argtypes=None):
        objc.objc_msgSend.restype = restype
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p] + list(argtypes or [])
        return objc.objc_msgSend(ctypes.c_void_p(receiver), _selector(selector), *args)

    view = int(widget.winId())
    if not view:
        return

    ns_window = _send(view, "window", restype=ctypes.c_void_p)
    if not ns_window:
        return

    style_mask = _send(ns_window, "styleMask", restype=ctypes.c_ulonglong)
    style_mask |= NS_WINDOW_STYLE_MASK_FULL_SIZE_CONTENT_VIEW

    _send(
        ns_window,
        "setStyleMask:",
        ctypes.c_ulonglong(style_mask),
        restype=None,
        argtypes=[ctypes.c_ulonglong],
    )
    _send(
        ns_window,
        "setTitleVisibility:",
        ctypes.c_long(NS_WINDOW_TITLE_HIDDEN),
        restype=None,
        argtypes=[ctypes.c_long],
    )
    _send(
        ns_window,
        "setTitlebarAppearsTransparent:",
        ctypes.c_bool(True),
        restype=None,
        argtypes=[ctypes.c_bool],
    )
    _send(
        ns_window,
        "setMovableByWindowBackground:",
        ctypes.c_bool(False),
        restype=None,
        argtypes=[ctypes.c_bool],
    )

    red, green, blue = _hex_to_rgb(Palette.BACKGROUND)
    ns_color_class = ctypes.c_void_p(objc.objc_getClass(b"NSColor"))
    background_color = _send(
        ns_color_class.value,
        "colorWithSRGBRed:green:blue:alpha:",
        ctypes.c_double(red),
        ctypes.c_double(green),
        ctypes.c_double(blue),
        ctypes.c_double(1.0),
        restype=ctypes.c_void_p,
        argtypes=[ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double],
    )
    _send(
        ns_window,
        "setBackgroundColor:",
        ctypes.c_void_p(background_color),
        restype=None,
        argtypes=[ctypes.c_void_p],
    )


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4))
