import ctypes
import os
import time
import logHandler
import addonHandler

from logHandler import log

# BASS Constants
BASS_SAMPLE_FLOAT = 256
BASS_STREAM_AUTOFREE = 0x40000
BASS_POS_BYTE = 0
BASS_ACTIVE_PLAYING = 1

class BassEngine:
    def __init__(self, dll_path=None):
        if dll_path is None:
            # More robust architecture check
            arch = "x64" if ctypes.sizeof(ctypes.c_void_p) == 8 else "x86"
            try:
                addon_root = addonHandler.getAddonPath(__file__)
                dll_path = os.path.join(addon_root, "lib", arch, "bass.dll")
            except Exception as e:
                log.debug(f"NVDA Media Player: addonHandler failed, using fallback path: {e}")
                base_dir = os.path.dirname(__file__)
                # Assuming structure: globalPlugins/nvda_media_player/audio_engine.py
                # Path to lib is ../../lib/
                dll_path = os.path.join(base_dir, "..", "..", "lib", arch, "bass.dll")
            
        log.info(f"NVDA Media Player: Attempting to load BASS from {dll_path}")
        if not os.path.exists(dll_path):
            log.error(f"NVDA Media Player: BASS DLL not found at {dll_path}")
            raise FileNotFoundError(f"BASS DLL not found at {dll_path}")
            
        try:
            self.bass = ctypes.WinDLL(dll_path)
            self._setup_signatures()
            log.info("NVDA Media Player: BASS loaded and signatures defined")
        except Exception as e:
            log.error(f"NVDA Media Player: Failed to load BASS DLL: {e}")
            raise
        self.init_bass()

    def _setup_signatures(self):
        # Explicitly define argument and return types for 32-bit compatibility
        # Especially crucial for QWORD (c_uint64) parameters
        self.bass.BASS_ErrorGetCode.restype = ctypes.c_int
        self.bass.BASS_Init.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
        self.bass.BASS_Init.restype = ctypes.c_bool
        
        # HSTREAM BASS_StreamCreateFile(BOOL mem, const void *file, QWORD offset, QWORD length, DWORD flags);
        self.bass.BASS_StreamCreateFile.argtypes = [ctypes.c_bool, ctypes.c_wchar_p, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint32]
        self.bass.BASS_StreamCreateFile.restype = ctypes.c_uint32 # HSTREAM
        
        self.bass.BASS_ChannelPlay.argtypes = [ctypes.c_uint32, ctypes.c_bool]
        self.bass.BASS_ChannelPlay.restype = ctypes.c_bool
        
        self.bass.BASS_ChannelPause.argtypes = [ctypes.c_uint32]
        self.bass.BASS_ChannelPause.restype = ctypes.c_bool
        
        self.bass.BASS_ChannelStop.argtypes = [ctypes.c_uint32]
        self.bass.BASS_ChannelStop.restype = ctypes.c_bool
        
        self.bass.BASS_ChannelGetPosition.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        self.bass.BASS_ChannelGetPosition.restype = ctypes.c_uint64 # QWORD
        
        self.bass.BASS_ChannelSetPosition.argtypes = [ctypes.c_uint32, ctypes.c_uint64, ctypes.c_uint32]
        self.bass.BASS_ChannelSetPosition.restype = ctypes.c_bool
        
        self.bass.BASS_ChannelGetLength.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        self.bass.BASS_ChannelGetLength.restype = ctypes.c_uint64 # QWORD
        
        self.bass.BASS_ChannelIsActive.argtypes = [ctypes.c_uint32]
        self.bass.BASS_ChannelIsActive.restype = ctypes.c_uint32
        
        self.bass.BASS_ChannelSeconds2Bytes.argtypes = [ctypes.c_uint32, ctypes.c_double]
        self.bass.BASS_ChannelSeconds2Bytes.restype = ctypes.c_uint64 # QWORD
        
        self.bass.BASS_ChannelBytes2Seconds.argtypes = [ctypes.c_uint32, ctypes.c_uint64]
        self.bass.BASS_ChannelBytes2Seconds.restype = ctypes.c_double
        
        self.bass.BASS_ChannelSetAttribute.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_float]
        self.bass.BASS_ChannelSetAttribute.restype = ctypes.c_bool
        
        self.bass.BASS_ChannelGetAttribute.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
        self.bass.BASS_ChannelGetAttribute.restype = ctypes.c_bool

    def init_bass(self):
        if not self.bass.BASS_Init(-1, 44100, 0, 0, None):
             error = self.bass.BASS_ErrorGetCode()
             if error != 14: # BASS_ERROR_ALREADY
                 raise Exception(f"BASS_Init failed with error code {error}")

    def load_stream(self, file_path):
        # Ensure path is absolute and uses backslashes
        file_path = os.path.abspath(file_path)
        log.info(f"### NVDA MEDIA PLAYER: OPENING FILE: {file_path} ###")
        
        # BASS with BASS_UNICODE (0x80000000) expects a pointer to a UTF-16 string
        # file_path is already a string in Python 3 (UTF-16 compatible)
        # We need to pass it as a wide-char pointer
        handle = self.bass.BASS_StreamCreateFile(False, file_path, 0, 0, 0x80000000)
        if not handle:
            error_code = self.bass.BASS_ErrorGetCode()
            log.error(f"### NVDA MEDIA PLAYER: BASS_StreamCreateFile FAILED: {error_code} ###")
            raise Exception(f"BASS Error {error_code}")
        return handle

    def play(self, handle):
        self.bass.BASS_ChannelPlay(handle, False)

    def pause(self, handle):
        self.bass.BASS_ChannelPause(handle)

    def stop(self, handle):
        self.bass.BASS_ChannelStop(handle)

    def get_position(self, handle):
        return self.bass.BASS_ChannelGetPosition(handle, BASS_POS_BYTE)

    def set_position(self, handle, pos):
        self.bass.BASS_ChannelSetPosition(handle, pos, BASS_POS_BYTE)

    def set_volume(self, handle, volume):
        """Sets volume from 0.0 to 1.0."""
        # BASS_ATTRIB_VOL is 2
        return self.bass.BASS_ChannelSetAttribute(handle, 2, ctypes.c_float(volume))

    def get_volume(self, handle):
        """Gets volume from 0.0 to 1.0."""
        vol = ctypes.c_float()
        if self.bass.BASS_ChannelGetAttribute(handle, 2, ctypes.byref(vol)):
            return vol.value
        return 1.0

    def get_length(self, handle):
        return self.bass.BASS_ChannelGetLength(handle, BASS_POS_BYTE)

    def seconds_to_bytes(self, handle, seconds):
        return self.bass.BASS_ChannelSeconds2Bytes(handle, ctypes.c_double(seconds))

    def bytes_to_seconds(self, handle, bytes_pos):
        self.bass.BASS_ChannelBytes2Seconds.restype = ctypes.c_double
        return self.bass.BASS_ChannelBytes2Seconds(handle, bytes_pos)

    def is_playing(self, handle):
        return self.bass.BASS_ChannelIsActive(handle) == BASS_ACTIVE_PLAYING

    def free(self):
        self.bass.BASS_Free()
