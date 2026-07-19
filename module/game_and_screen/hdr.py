"""Windows HDR display detection through DXGI."""

import ctypes
from dataclasses import dataclass

from module.logger import log

HDR_COLOR_SPACE = 12  # DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020

COINIT_APARTMENTTHREADED = 0x2
S_OK = 0
S_FALSE = 1

_LPVOIDP = ctypes.POINTER(ctypes.c_void_p)


@dataclass(frozen=True)
class HdrDisplayInfo:
    monitor_handle: int
    color_space: int

    @property
    def hdr_enabled(self) -> bool:
        return self.color_space == HDR_COLOR_SPACE


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class DXGI_OUTPUT_DESC1(ctypes.Structure):
    """Description returned by IDXGIOutput6::GetDesc1."""

    _fields_ = [
        ("DeviceName", ctypes.c_wchar * 32),
        ("DesktopCoordinates", RECT),
        ("AttachedToDesktop", ctypes.c_int),
        ("Rotation", ctypes.c_uint),
        ("Monitor", ctypes.c_void_p),
        ("BitsPerColor", ctypes.c_uint),
        ("ColorSpace", ctypes.c_int),
        ("RedPrimary", ctypes.c_float * 2),
        ("GreenPrimary", ctypes.c_float * 2),
        ("BluePrimary", ctypes.c_float * 2),
        ("WhitePoint", ctypes.c_float * 2),
        ("MinLuminance", ctypes.c_float),
        ("MaxLuminance", ctypes.c_float),
        ("MaxFullFrameLuminance", ctypes.c_float),
    ]


IID_IDXGIFactory1 = GUID(
    0x770AAE78,
    0xF26F,
    0x4DBA,
    (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87),
)

IID_IDXGIOutput6 = GUID(
    0x068346E8,
    0xAAEC,
    0x4B84,
    (ctypes.c_ubyte * 8)(0xAD, 0xD7, 0x13, 0x7F, 0x51, 0x3F, 0x77, 0xA1),
)

_QueryInterface = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
)

_Release = ctypes.WINFUNCTYPE(
    ctypes.c_ulong,
    ctypes.c_void_p,
)

_EnumAdapters1 = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_void_p),
)

_EnumOutputs = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_void_p),
)

_GetDesc1 = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_void_p,
    ctypes.POINTER(DXGI_OUTPUT_DESC1),
)

_ole32 = ctypes.windll.ole32
_ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
_ole32.CoInitializeEx.restype = ctypes.c_long
_ole32.CoUninitialize.argtypes = []
_ole32.CoUninitialize.restype = None

_dxgi = ctypes.windll.dxgi
_dxgi.CreateDXGIFactory1.argtypes = [
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]
_dxgi.CreateDXGIFactory1.restype = ctypes.c_long


def _vtable_func(com_ptr: int, index: int, prototype):
    vtable = ctypes.cast(com_ptr, _LPVOIDP).contents
    func_ptr = ctypes.cast(vtable, _LPVOIDP)[index]
    return prototype(func_ptr)


def _release(com_ptr) -> None:
    if not com_ptr:
        return
    _vtable_func(com_ptr, 2, _Release)(com_ptr)


def _query_output6(output_ptr: int) -> int | None:
    output6 = ctypes.c_void_p()
    query_interface = _vtable_func(output_ptr, 0, _QueryInterface)
    hr = query_interface(
        output_ptr,
        ctypes.byref(IID_IDXGIOutput6),
        ctypes.byref(output6),
    )
    return output6.value if hr == S_OK else None


def _create_factory() -> int | None:
    factory = ctypes.c_void_p()
    hr = _dxgi.CreateDXGIFactory1(
        ctypes.byref(IID_IDXGIFactory1),
        ctypes.byref(factory),
    )
    return factory.value if hr == S_OK else None


def _enumerate_output_descs(factory_ptr: int) -> list[DXGI_OUTPUT_DESC1]:
    results: list[DXGI_OUTPUT_DESC1] = []
    enum_adapters = _vtable_func(factory_ptr, 12, _EnumAdapters1)

    adapter_index = 0
    while True:
        adapter = ctypes.c_void_p()
        if enum_adapters(factory_ptr, adapter_index, ctypes.byref(adapter)) != S_OK:
            break

        try:
            enum_outputs = _vtable_func(adapter.value, 7, _EnumOutputs)
            output_index = 0
            while True:
                output = ctypes.c_void_p()
                if (
                    enum_outputs(
                        adapter.value,
                        output_index,
                        ctypes.byref(output),
                    )
                    != S_OK
                ):
                    break

                try:
                    output6_ptr = _query_output6(output.value)
                    if output6_ptr is not None:
                        try:
                            desc = DXGI_OUTPUT_DESC1()
                            get_desc = _vtable_func(output6_ptr, 27, _GetDesc1)
                            if get_desc(output6_ptr, ctypes.byref(desc)) == S_OK:
                                results.append(desc)
                        finally:
                            _release(output6_ptr)
                finally:
                    _release(output.value)
                output_index += 1
        finally:
            _release(adapter.value)
        adapter_index += 1

    return results


def enumerate_hdr_displays() -> list[HdrDisplayInfo]:
    """Return HDR color-space information for current display outputs."""
    hr = _ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    if hr not in (S_OK, S_FALSE):
        log.warning(f"COM 初始化失败，跳过 HDR 检测: 0x{hr & 0xFFFFFFFF:08X}")
        return []

    try:
        factory_ptr = _create_factory()
        if factory_ptr is None:
            log.warning("CreateDXGIFactory1 失败，跳过 HDR 检测")
            return []
        try:
            descs = _enumerate_output_descs(factory_ptr)
        finally:
            _release(factory_ptr)
    except Exception as exc:
        log.warning(f"查询显示器 HDR 状态失败: {exc}")
        return []
    finally:
        _ole32.CoUninitialize()

    return [
        HdrDisplayInfo(
            monitor_handle=int(desc.Monitor or 0),
            color_space=desc.ColorSpace,
        )
        for desc in descs
    ]


def get_monitor_hdr_info(hmonitor: int) -> HdrDisplayInfo | None:
    """Return HDR information for the selected Windows monitor."""
    return next(
        (
            info
            for info in enumerate_hdr_displays()
            if info.monitor_handle == int(hmonitor)
        ),
        None,
    )
