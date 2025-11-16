import ctypes
import sys


def secure_erase(byte_arr: bytearray):
    """Attempt to overwrite the contents of a bytearray in place to minimize memory remnants."""
    for i in range(len(byte_arr)):
        byte_arr[i] = 0


def allocate_secure_bytes(size: int):
    """Return a bytearray intended for temporary sensitive data and attempt to lock pages if possible.

    Note: Python provides limited guarantees. Use this as a best-effort measure.
    """
    arr = bytearray(os.urandom(size))
    try:
        if sys.platform.startswith('linux'):
            libc = ctypes.CDLL('libc.so.6')
            libc.mlock(ctypes.c_void_p(id(arr)), ctypes.c_size_t(len(arr)))
    except Exception:
        pass
    return arr