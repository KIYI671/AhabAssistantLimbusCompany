"""假光标（fake cursor）注入后端。

Limbus Company 是 Unity 游戏，指针位置来自 `GetCursorPos()`，而不是
`WM_MOUSEMOVE` 的 lParam。所以想在不移动系统光标的前提下点准坐标，就必须让
游戏进程自己"读到一个假坐标"。

本模块往目标进程注入一小段桩代码，并把 `GetCursorPos` 的头 5 个字节改成
一条相对跳转：

    GetCursorPos:
        jmp stub
    stub:
        mov r11, <控制块>
        mov eax, [r11]        ; x
        mov [rcx], eax
        mov eax, [r11+4]      ; y
        mov [rcx+4], eax
        mov eax, 1            ; TRUE
        ret

坐标放在桩旁边的控制块里，用 `WriteProcessMemory` 更新，因此注入之后每次移动
鼠标只是两次 4 字节写入，不需要重复注入。

关于安全性：

* 只覆盖函数头 5 个字节，不解析指令；被覆盖的字节在挂钩期间永远不会被执行
  （跳转先发生），卸载时按原样写回，所以即使切断了一条指令也是安全的。
* 挂/脱钩期间短暂挂起目标进程的其他线程，避免有线程正好停在被打补丁的字节上。
* 目标函数头不做"是否已被挂钩"的预判：`user32!GetCursorPos` 在很多 Windows
  版本上本身就是一条 `E9` 跳板（跳到 win32u），首字节 E9 是正常实现。即使真的
  被第三方工具挂过，我们也只是临时覆盖前 5 字节，卸载时按原样写回。
* 任何一步失败都只记录日志并返回 False，调用方退回 `SetCursorPos`，行为与
  原来的后台模式一致。

已知限制：脚本被强杀（任务管理器结束进程）时来不及脱钩，游戏会一直读到最后一
个假坐标，重开游戏即可恢复。正常停止/暂停都会走 `detach()`。
"""

from __future__ import annotations

import atexit
import ctypes
import struct
import sys
import threading
from ctypes import wintypes

import win32api
import win32process

from ...game_and_screen import screen
from ...logger import log

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

# 进程访问权限：读、写、查询、操作
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_ACCESS = (
    PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION
)

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
MEM_FREE = 0x10000
PAGE_EXECUTE_READWRITE = 0x40

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
TH32CS_SNAPTHREAD = 0x00000004
THREAD_SUSPEND_RESUME = 0x0002
LIST_MODULES_ALL = 0x03

GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS = 0x00000004

# 控制块在注入块里的偏移
CTL_OFFSET = 0x40
BLOCK_SIZE = 0x100

_SUSPEND_LOCK = threading.RLock()


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("_alignment", wintypes.DWORD),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", ctypes.c_void_p),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
    ]


def _bind_signatures() -> None:
    """显式声明 64 位签名，否则 ctypes 会把指针截成 int。"""
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.VirtualAllocEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_size_t,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel32.VirtualAllocEx.restype = ctypes.c_void_p
    kernel32.VirtualFreeEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_size_t,
        wintypes.DWORD,
    ]
    kernel32.VirtualFreeEx.restype = wintypes.BOOL
    kernel32.VirtualQueryEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    kernel32.WriteProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.WriteProcessMemory.restype = wintypes.BOOL
    kernel32.FlushInstructionCache.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_size_t,
    ]
    kernel32.FlushInstructionCache.restype = wintypes.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Module32FirstW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MODULEENTRY32W),
    ]
    kernel32.Module32FirstW.restype = wintypes.BOOL
    kernel32.Module32NextW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MODULEENTRY32W),
    ]
    kernel32.Module32NextW.restype = wintypes.BOOL
    kernel32.Thread32First.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(THREADENTRY32),
    ]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(THREADENTRY32),
    ]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.SuspendThread.argtypes = [wintypes.HANDLE]
    kernel32.SuspendThread.restype = wintypes.DWORD
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.GetModuleHandleExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    kernel32.GetModuleHandleExW.restype = wintypes.BOOL
    kernel32.GetModuleFileNameW.argtypes = [
        ctypes.c_void_p,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    kernel32.GetModuleFileNameW.restype = wintypes.DWORD
    kernel32.IsWow64Process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel32.IsWow64Process.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    user32.GetCursorPos.argtypes = [ctypes.c_void_p]
    user32.GetCursorPos.restype = wintypes.BOOL
    psapi.EnumProcessModulesEx.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_void_p),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.DWORD,
    ]
    psapi.EnumProcessModulesEx.restype = wintypes.BOOL
    psapi.GetModuleBaseNameW.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    psapi.GetModuleBaseNameW.restype = wintypes.DWORD


_bind_signatures()


def _build_stub(ctl_addr: int) -> bytes:
    """生成 28 字节的桩：写入假坐标并返回 TRUE。"""
    code = b""
    code += b"\x49\xBB" + struct.pack("<Q", ctl_addr)  # mov r11, ctl
    code += b"\x41\x8B\x03"  # mov eax, [r11]      ; x
    code += b"\x89\x01"  # mov [rcx], eax
    code += b"\x41\x8B\x43\x04"  # mov eax, [r11+4]    ; y
    code += b"\x89\x41\x04"  # mov [rcx+4], eax
    code += b"\xB8\x01\x00\x00\x00"  # mov eax, 1
    code += b"\xC3"  # ret
    return code


def _suspend_other_threads(pid: int) -> list[int]:
    """挂起目标进程里除自己以外的所有线程，返回句柄列表用于恢复。"""
    handles: list[int] = []
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == wintypes.HANDLE(-1).value:
        return handles
    try:
        entry = THREADENTRY32()
        entry.dwSize = ctypes.sizeof(THREADENTRY32)
        me = kernel32.GetCurrentThreadId()
        if not kernel32.Thread32First(snap, ctypes.byref(entry)):
            return handles
        while True:
            if entry.th32OwnerProcessID == pid and entry.th32ThreadID != me:
                handle = kernel32.OpenThread(
                    THREAD_SUSPEND_RESUME, False, entry.th32ThreadID
                )
                if handle:
                    if kernel32.SuspendThread(handle) != 0xFFFFFFFF:
                        handles.append(handle)
                    else:
                        kernel32.CloseHandle(handle)
            ok = kernel32.Thread32Next(snap, ctypes.byref(entry))
            if not ok:
                break
    finally:
        kernel32.CloseHandle(snap)
    return handles


def _resume_threads(handles: list[int]) -> None:
    for handle in handles:
        try:
            kernel32.ResumeThread(handle)
        finally:
            kernel32.CloseHandle(handle)


def _local_module_of(address: int) -> tuple[int, str] | None:
    """返回本进程里 address 所属模块的 (基址, 模块名)。"""
    module = ctypes.c_void_p()
    if not kernel32.GetModuleHandleExW(
        GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
        ctypes.cast(address, wintypes.LPCWSTR),
        ctypes.byref(module),
    ):
        return None
    buf = ctypes.create_unicode_buffer(32768)
    if not kernel32.GetModuleFileNameW(module, buf, len(buf)):
        return None
    return module.value, buf.value.split("\\")[-1].lower()


def _remote_module_base_psapi(handle: int, module_name: str) -> int | None:
    count = 512
    loaded = 0
    for _ in range(4):
        array = (ctypes.c_void_p * count)()
        needed = wintypes.DWORD(0)
        if not psapi.EnumProcessModulesEx(
            handle, array, ctypes.sizeof(array), ctypes.byref(needed), LIST_MODULES_ALL
        ):
            return None
        loaded = needed.value // ctypes.sizeof(ctypes.c_void_p)
        if loaded <= count:
            break
        count = loaded + 64
    buf = ctypes.create_unicode_buffer(260)
    for index in range(min(loaded, count)):
        module = array[index]
        if not module:
            continue
        if psapi.GetModuleBaseNameW(handle, ctypes.c_void_p(module), buf, len(buf)):
            if buf.value.lower() == module_name:
                return module
    return None


def _remote_module_base(handle: int, pid: int, module_name: str) -> int | None:
    """在目标进程的模块列表里找同名模块的基址。

    优先 psapi：`CreateToolhelp32Snapshot` 在受限环境下会直接
    返回 `ACCESS_DENIED`。两条都失败时返回 None。
    """
    base = _remote_module_base_psapi(handle, module_name)
    if base:
        return base
    return _remote_module_base_toolhelp(pid, module_name)


def _remote_module_base_toolhelp(pid: int, module_name: str) -> int | None:
    """toolhelp 兜底实现。"""
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == wintypes.HANDLE(-1).value:
        return None
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not kernel32.Module32FirstW(snap, ctypes.byref(entry)):
            return None
        while True:
            if entry.szModule.lower() == module_name:
                return entry.modBaseAddr or 0
            if not kernel32.Module32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return None


def _alloc_near(handle: int, target: int, size: int) -> int | None:
    """在目标 ±1GB 范围内找一块空闲内存，保证 5 字节相对跳转够得着。"""
    gran = 0x10000
    low = max(target - 0x40000000, 0x10000)
    # 64 位用户态地址上限（不是 32 位的 0x7FFF0000）
    high = min(target + 0x40000000, 0x7FFFFFFF0000)
    addr = low & ~(gran - 1)
    mbi = MEMORY_BASIC_INFORMATION()
    for _ in range(4096):
        if addr >= high:
            break
        if not kernel32.VirtualQueryEx(
            handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
        ):
            break
        base = mbi.BaseAddress or 0
        size_region = mbi.RegionSize or 0
        if mbi.State == MEM_FREE and size_region >= size:
            hint = (base + gran - 1) & ~(gran - 1)
            allocated = kernel32.VirtualAllocEx(
                handle,
                ctypes.c_void_p(hint),
                size,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_EXECUTE_READWRITE,
            )
            if allocated:
                return allocated
        nxt = base + size_region
        if nxt <= addr:
            break
        addr = nxt
    return None


class _HookSession:
    """一次注入的完整生命周期。"""

    def __init__(self, pid: int):
        self.pid = pid
        self.handle: int | None = None
        self.target: int = 0
        self.block: int = 0
        self.ctl: int = 0
        self.stub: int = 0
        self.original = b""
        self.hooked = False

    # --- 注入 ---
    def attach(self) -> bool:
        self.handle = kernel32.OpenProcess(PROCESS_ACCESS, False, self.pid)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "OpenProcess 失败")

        is_wow64 = wintypes.BOOL()
        if kernel32.IsWow64Process(self.handle, ctypes.byref(is_wow64)) and is_wow64.value:
            raise OSError("目标进程是 32 位，假光标只支持 64 位进程")

        local_addr = ctypes.cast(user32.GetCursorPos, ctypes.c_void_p).value
        info = _local_module_of(local_addr)
        if not info:
            raise OSError("无法定位 GetCursorPos 所在模块")
        local_base, module_name = info
        remote_base = _remote_module_base(self.handle, self.pid, module_name)
        if not remote_base:
            raise OSError(f"目标进程里找不到 {module_name}")
        self.target = remote_base + (local_addr - local_base)

        # 读函数头。注意：user32 里的 GetCursorPos 在很多 Windows 版本上
        # 本身就是一条 5 字节的 `E9` 跳板（跳到 win32u），首字节 E9 属于
        # 正常实现，不能据此判断"被别的工具挂过"。真被第三方 hook 时，我们
        # 也只是临时覆盖前 5 字节，卸载时按原样写回，同样安全。
        head = self._read(self.target, 16)
        self.original = head[:5]
        log.debug(
            f"GetCursorPos 入口字节: {head[:8].hex(' ')}"
            + ("（jmp 跳板）" if head[0:1] == b"\xE9" else "")
        )

        self.block = _alloc_near(self.handle, self.target, BLOCK_SIZE)
        if not self.block:
            raise OSError("目标进程附近找不到可分配的内存")
        self.ctl = self.block + CTL_OFFSET
        self.stub = self.block
        self._write(self.block, _build_stub(self.ctl).ljust(CTL_OFFSET, b"\x90"))
        # 坐标先用真光标位置兜底，避免注入瞬间游戏指针跳到左上角
        real = win32api.GetCursorPos()
        self._write(self.ctl, struct.pack("<ii", int(real[0]), int(real[1])))

        rel = self.stub - (self.target + 5)
        if not -(2**31) <= rel < 2**31:
            raise OSError("桩与控制目标距离超过 2GB，无法相对跳转")
        self._patch(b"\xE9" + struct.pack("<i", rel))
        return True

    def _patch(self, payload: bytes) -> None:
        with _SUSPEND_LOCK:
            suspended = _suspend_other_threads(self.pid)
            try:
                self._write(self.target, payload)
                kernel32.FlushInstructionCache(
                    self.handle, ctypes.c_void_p(self.target), len(payload)
                )
                self.hooked = True
            finally:
                _resume_threads(suspended)

    def _read(self, address: int, size: int) -> bytes:
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buf,
            size,
            ctypes.byref(read),
        ):
            raise OSError(ctypes.get_last_error(), "ReadProcessMemory 失败")
        return buf.raw[: read.value]

    def _write(self, address: int, payload: bytes) -> None:
        buf = ctypes.create_string_buffer(payload, len(payload))
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            buf,
            len(payload),
            ctypes.byref(written),
        ):
            raise OSError(ctypes.get_last_error(), "WriteProcessMemory 失败")

    # --- 使用 ---
    def set_point(self, x: int, y: int) -> bool:
        if not self.hooked:
            return False
        self._write(self.ctl, struct.pack("<ii", int(x), int(y)))
        return True

    def detach(self) -> None:
        if self.handle is None:
            return
        try:
            if self.hooked:
                with _SUSPEND_LOCK:
                    suspended = _suspend_other_threads(self.pid)
                    try:
                        self._write(self.target, self.original)
                        kernel32.FlushInstructionCache(
                            self.handle, ctypes.c_void_p(self.target), len(self.original)
                        )
                    finally:
                        _resume_threads(suspended)
                self.hooked = False
            if self.block:
                kernel32.VirtualFreeEx(
                    self.handle, ctypes.c_void_p(self.block), 0, MEM_RELEASE
                )
                self.block = 0
        except Exception as exc:  # 进程可能已经退出
            log.debug(f"假光标卸载失败（可能游戏已退出）: {exc}")
        finally:
            if self.handle:
                kernel32.CloseHandle(self.handle)
            self.handle = None


_REGISTERED: list["FakeCursor"] = []


def _detach_at_exit() -> None:
    for instance in list(_REGISTERED):
        try:
            instance.detach()
        except Exception:
            pass


class FakeCursor:
    """进程级假光标。失败时自动退回 `SetCursorPos`。"""

    def __init__(self) -> None:
        self._session: _HookSession | None = None
        self._pid = 0
        self._warned = False
        self._lock = threading.RLock()
        _REGISTERED.append(self)
        if len(_REGISTERED) == 1:
            atexit.register(_detach_at_exit)

    @property
    def active(self) -> bool:
        return bool(self._session and self._session.hooked)

    def move(self, x: int, y: int) -> bool:
        """把假光标移到屏幕坐标 (x, y)。"""
        with self._lock:
            if self._ensure_session() and self._session is not None:
                try:
                    if self._session.set_point(x, y):
                        return True
                except Exception as exc:
                    log.debug(f"假光标写入失败，重新注入: {exc}")
                    self._drop()
            # 降级路径：保持和原来的后台模式一致
            try:
                win32api.SetCursorPos((int(x), int(y)))
            except Exception as exc:
                log.debug(f"降级 SetCursorPos 也失败了: {exc}")
            return False

    def _ensure_session(self) -> bool:
        hwnd = screen.handle.hwnd
        if not hwnd:
            return False

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return False
        if self._session is not None and self._session.hooked and pid == self._pid:
            return True
        self._drop()
        if not (sys.maxsize > 2**32):
            self._warn("当前 Python 是 32 位，无法给 64 位游戏注入假光标", once=True)
            return False
        session = _HookSession(pid)
        try:
            session.attach()
        except Exception as exc:
            session.detach()
            self._warn(f"假光标注入失败，已退回 SetCursorPos：{exc}", once=True)
            return False
        self._session = session
        self._pid = pid
        log.info(
            f"假光标已注入 pid={pid}: GetCursorPos 0x{self._session.target:X} -> "
            f"stub 0x{self._session.stub:X}"
        )
        return True

    def _warn(self, message: str, once: bool = False) -> None:
        if once and self._warned:
            return
        if once:
            self._warned = True
        log.warning(message)

    def _drop(self) -> None:
        if self._session is not None:
            self._session.detach()
            self._session = None

    def detach(self) -> None:
        """卸载注入，游戏恢复读真光标。"""
        with self._lock:
            self._drop()
            self._pid = 0
