import ctypes
import sys
import numpy as np

# --- 1. 載入系統底層庫 ---
try:
    _lib = ctypes.CDLL('libhackrf.so.0')
except OSError:
    try:
        _lib = ctypes.CDLL('libhackrf.so')
    except OSError:
        print("錯誤: 找不到 libhackrf.so。請確保已執行 'sudo apt install libhackrf-dev'")
        sys.exit(1)

# --- 2. 定義常數與結構 ---
HACKRF_SUCCESS = 0
HACKRF_TRUE = 1
HACKRF_FALSE = 0

class HackrfTransfer(ctypes.Structure):
    _fields_ = [
        ("device", ctypes.c_void_p),
        ("buffer", ctypes.POINTER(ctypes.c_byte)),
        ("buffer_length", ctypes.c_int),
        ("valid_length", ctypes.c_int),
        ("rx_ctx", ctypes.c_void_p),
        ("tx_ctx", ctypes.c_void_p),
    ]

# 定義 Callback 函式型別
HackrfCallback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(HackrfTransfer))

# --- 3. 設定 C 函式參數 ---
_lib.hackrf_init.restype = ctypes.c_int
_lib.hackrf_exit.restype = ctypes.c_int

_lib.hackrf_open.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
_lib.hackrf_open.restype = ctypes.c_int

_lib.hackrf_close.argtypes = [ctypes.c_void_p]
_lib.hackrf_close.restype = ctypes.c_int

# Sample rate 在 C 中是 double，所以 float 其實是可以的，但為了保險我們不做 int 轉換
_lib.hackrf_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_double]
_lib.hackrf_set_sample_rate.restype = ctypes.c_int

# Freq 在 C 中是 uint64，絕對不能傳 float
_lib.hackrf_set_freq.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
_lib.hackrf_set_freq.restype = ctypes.c_int

_lib.hackrf_set_amp_enable.argtypes = [ctypes.c_void_p, ctypes.c_uint8]
_lib.hackrf_set_amp_enable.restype = ctypes.c_int

_lib.hackrf_set_lna_gain.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_lib.hackrf_set_lna_gain.restype = ctypes.c_int

_lib.hackrf_set_vga_gain.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_lib.hackrf_set_vga_gain.restype = ctypes.c_int

_lib.hackrf_start_rx.argtypes = [ctypes.c_void_p, HackrfCallback, ctypes.c_void_p]
_lib.hackrf_start_rx.restype = ctypes.c_int

_lib.hackrf_stop_rx.argtypes = [ctypes.c_void_p]
_lib.hackrf_stop_rx.restype = ctypes.c_int

# --- 4. 封裝成好用的 Class ---

class HackRF:
    def __init__(self):
        self.device = ctypes.c_void_p(None)
        self._callback_ref = None 
        
        if _lib.hackrf_init() != HACKRF_SUCCESS:
            raise RuntimeError("HackRF Init Failed")

    def open(self):
        ret = _lib.hackrf_open(ctypes.byref(self.device))
        if ret != HACKRF_SUCCESS:
            raise RuntimeError(f"無法開啟 HackRF (Error {ret})。請檢查 USB 連接或權限。")

    def close(self):
        if self.device:
            _lib.hackrf_stop_rx(self.device)
            _lib.hackrf_close(self.device)
            self.device = None
        _lib.hackrf_exit()

    def set_sample_rate(self, rate_hz):
        # Sample rate 接受 double，所以我們轉 float
        _lib.hackrf_set_sample_rate(self.device, float(rate_hz))

    def set_freq(self, freq_hz):
        # --- 關鍵修正：強制轉 int ---
        # 如果 freq_hz 是 920e6 (float)，這裡會變成 920000000 (int)
        _lib.hackrf_set_freq(self.device, int(freq_hz))

    def set_gains(self, lna=32, vga=20, amp=True):
        # Gain 也必須是整數
        _lib.hackrf_set_lna_gain(self.device, int(lna))
        _lib.hackrf_set_vga_gain(self.device, int(vga))
        _lib.hackrf_set_amp_enable(self.device, 1 if amp else 0)

    def start_rx(self, python_callback):
        def c_callback_wrapper(transfer_ptr):
            if not transfer_ptr: return 0
            transfer = transfer_ptr.contents
            valid_length = transfer.valid_length
            
            # 轉換 buffer
            buffer = np.ctypeslib.as_array(transfer.buffer, shape=(valid_length,))
            
            python_callback(buffer)
            return 0 

        self._callback_ref = HackrfCallback(c_callback_wrapper)
        
        ret = _lib.hackrf_start_rx(self.device, self._callback_ref, None)
        if ret != HACKRF_SUCCESS:
            raise RuntimeError(f"Start RX Failed: {ret}")

    def stop_rx(self):
        if self.device:
            _lib.hackrf_stop_rx(self.device)

            
if __name__ == "__main__":
    # 簡單測試 HackRF 是否能正常工作
    hackrf = HackRF()
    try:
        hackrf.open()
        hackrf.set_sample_rate(2e6)
        hackrf.set_freq(915e6)
        hackrf.set_gains(lna=32, vga=20, amp=True)
        print("HackRF 已成功初始化並設定參數。")
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        hackrf.close()