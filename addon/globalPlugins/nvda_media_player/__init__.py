import os
import random
import wx
import builtins
import addonHandler
import globalPluginHandler
import ui
import gui
import scriptHandler
import threading
import config
from scriptHandler import script
import logHandler

# Use standard logHandler
log = logHandler.log

# Initialize translation
addonHandler.initTranslation()
try:
    _ = builtins._
except AttributeError:
    _ = lambda x: x
    builtins._ = _

log.info("### NVDA MEDIA PLAYER: PLUGIN LOADING ###")

# Define configuration spec
config.conf.spec["nvdaMediaPlayer"] = {
    "lastPath": "string(default='')",
    "lastPos": "integer(default=0)",
    "volume": "float(default=1.0, min=0.0, max=1.0)",
    "seekIntervalIndex": "integer(default=1, min=0, max=6)"
}

# Supported extensions
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.wma')

# Late import helper for audio engine
BassEngine = None
def get_engine_class():
    global BassEngine
    if BassEngine is None:
        try:
            from . import audio_engine
            BassEngine = audio_engine.BassEngine
            log.info("### NVDA MEDIA PLAYER: AUDIO ENGINE IMPORTED ###")
        except Exception as e:
            log.error(f"### NVDA MEDIA PLAYER: IMPORT ERROR: {e} ###")
    return BassEngine

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "NVDA Media Player"

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        
        self.engine = None
        self.handle = None
        self.playlist = []
        self.current_index = -1
        self.autoplay = True
        self.shuffle = False
        self.seek_intervals = [5, 15, 30, 60, 300, 1800, 3600]
        self.current_interval_index = config.conf["nvdaMediaPlayer"]["seekIntervalIndex"]
        
        # Initialize timer early
        self.timer = wx.Timer()
        self.timer.Notify = self.on_timer
        
        # Use a background thread for BASS loading to avoid watchdog freeze
        threading.Thread(target=self._backgroundInit, daemon=True).start()

    def _backgroundInit(self):
        log.info("### NVDA MEDIA PLAYER: BACKGROUND INIT START ###")
        try:
            if self._ensure_engine():
                log.info("### NVDA MEDIA PLAYER: BASS INITIALIZED IN BACKGROUND ###")
                wx.CallAfter(lambda: ui.message("Media Player Ready"))
        except Exception as e:
            log.error(f"### NVDA MEDIA PLAYER: BACKGROUND INIT FAILED: {e} ###")
        
        # Start timer on main thread
        wx.CallAfter(self.timer.Start, 1000)

    def _ensure_engine(self):
        if self.engine is None:
            engine_class = get_engine_class()
            if engine_class:
                try:
                    self.engine = engine_class()
                    return True
                except Exception as e:
                    log.error(f"### NVDA MEDIA PLAYER: BASS INIT FAILED: {e} ###")
            else:
                log.error("### NVDA MEDIA PLAYER: NO ENGINE CLASS ###")
        return self.engine is not None

    def on_timer(self):
        if not self.engine or not self.handle:
            return
        
        try:
            if not self.engine.is_playing(self.handle):
                current_pos = self.engine.get_position(self.handle)
                length = self.engine.get_length(self.handle)
                # If within 1 second of end, go to next
                if current_pos >= length - self.engine.seconds_to_bytes(self.handle, 1) and self.autoplay:
                    wx.CallAfter(self.next_track)
            
            # Save position periodically
            if self.engine.is_playing(self.handle):
                config.conf["nvdaMediaPlayer"]["lastPath"] = self.playlist[self.current_index]
                config.conf["nvdaMediaPlayer"]["lastPos"] = int(self.engine.get_position(self.handle))
        except:
            pass

    def _populate_playlist(self, start_file):
        """Discovers all audio files in the same folder as start_file."""
        folder = os.path.dirname(start_file)
        try:
            files = [os.path.join(folder, f) for f in os.listdir(folder) 
                     if f.lower().endswith(AUDIO_EXTENSIONS)]
            files.sort(key=lambda x: x.lower())
            self.playlist = files
            try:
                self.current_index = self.playlist.index(start_file)
            except ValueError:
                self.current_index = 0
            log.info(f"### NVDA MEDIA PLAYER: DISCOVERED {len(self.playlist)} TRACKS IN {folder} ###")
        except Exception as e:
            log.error(f"### NVDA MEDIA PLAYER: PLAYLIST DISCOVERY FAILED: {e} ###")
            self.playlist = [start_file]
            self.current_index = 0

    def play_file(self, file_path, start_pos=0):
        # Move playback start to a thread if it causes hangs
        threading.Thread(target=self._backgroundPlay, args=(file_path, start_pos), daemon=True).start()

    def _backgroundPlay(self, file_path, start_pos=0):
        if not self._ensure_engine():
            wx.CallAfter(lambda: ui.message("Error: Audio engine not available."))
            return
        
        if self.handle:
            try:
                self.engine.stop(self.handle)
            except:
                pass
            
        try:
            log.info(f"### NVDA MEDIA PLAYER: LOADING FILE {file_path} @ {start_pos} ###")
            self.handle = self.engine.load_stream(file_path)
            if start_pos > 0:
                self.engine.set_position(self.handle, start_pos)
            
            # Apply persistent volume
            vol = config.conf["nvdaMediaPlayer"]["volume"]
            self.engine.set_volume(self.handle, vol)
            
            self.engine.play(self.handle)
            wx.CallAfter(lambda: ui.message(f"Playing {os.path.basename(file_path)}"))
        except Exception as e:
            err_msg = str(e)
            log.error(f"### NVDA MEDIA PLAYER: PLAY ERROR: {err_msg} ###")
            wx.CallAfter(lambda m=err_msg: ui.message(f"Play error: {m}"))

    def next_track(self):
        if not self.playlist: 
            ui.message("Playlist empty")
            return
        
        if self.shuffle:
            if len(self.playlist) > 1:
                new_index = self.current_index
                while new_index == self.current_index:
                    new_index = random.randint(0, len(self.playlist) - 1)
                self.current_index = new_index
            else:
                self.current_index = 0
        else:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            
        self.play_file(self.playlist[self.current_index])

    def prev_track(self):
        if not self.playlist:
            ui.message("Playlist empty")
            return
            
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.play_file(self.playlist[self.current_index])

    @script(description="Toggle autoplay", gesture=("kb:NVDA+Shift+V", "kb:NVDA+Shift+vk:0x56"))
    def script_toggleAutoplay(self, gesture):
        self.autoplay = not self.autoplay
        ui.message(f"Autoplay {'on' if self.autoplay else 'off'}")

    @script(description="Open audio file", gesture=("kb:NVDA+Alt+O", "kb:NVDA+Alt+vk:0x4F"))
    def script_openFile(self, gesture):
        wx.CallAfter(self._doOpenFile)

    def _doOpenFile(self):
        parent = gui.mainFrame
        with wx.FileDialog(parent, "Open audio file", 
                           wildcard="Audio Files (*.mp3;*.wav;*.ogg;*.flac)|*.mp3;*.wav;*.ogg;*.flac|All Files (*.*)|*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW) as fd:
            if fd.ShowModal() == wx.ID_OK:
                path = fd.GetPath()
                self._populate_playlist(path)
                self.play_file(path)

    @script(description="Previous track", gesture=("kb:NVDA+Shift+,", "kb:NVDA+Shift+vk:0xBC"))
    def script_prevTrack(self, gesture):
        self.prev_track()

    @script(description="Next track", gesture=("kb:NVDA+Shift+/", "kb:NVDA+Shift+vk:0xBF"))
    def script_nextTrack(self, gesture):
        self.next_track()

    @script(description="Play/Pause", gesture=("kb:NVDA+Shift+.", "kb:NVDA+Shift+vk:0xBE"))
    def script_playPause(self, gesture):
        if not self.engine or not self.handle:
            ui.message("No audio loaded")
            return
        if self.engine.is_playing(self.handle):
            self.engine.pause(self.handle)
            ui.message("Paused")
        else:
            self.engine.play(self.handle)
            ui.message("Resumed")

    @script(description="Toggle shuffle", gesture=("kb:NVDA+Shift+S", "kb:NVDA+Shift+vk:0x53"))
    def script_toggleShuffle(self, gesture):
        self.shuffle = not self.shuffle
        ui.message(f"Shuffle {'on' if self.shuffle else 'off'}")

    @script(description="Resume playback", gesture=("kb:NVDA+Shift+R", "kb:NVDA+Shift+vk:0x52"))
    def script_resumePlayback(self, gesture):
        if self.handle:
            ui.message("Playback already active")
            return
        
        last_path = config.conf["nvdaMediaPlayer"]["lastPath"]
        if not last_path or not os.path.exists(last_path):
            ui.message("No resume track found")
            return
            
        last_pos = config.conf["nvdaMediaPlayer"]["lastPos"]
        ui.message("Resuming track")
        self._populate_playlist(last_path)
        self.play_file(last_path, start_pos=last_pos)

    @script(description="Rewind", gesture=("kb:NVDA+Shift+;", "kb:NVDA+Shift+vk:0xBA"))
    def script_rewind(self, gesture):
        if not self.engine or not self.handle: return
        interval = self.seek_intervals[self.current_interval_index]
        seek = self.engine.seconds_to_bytes(self.handle, interval)
        self.engine.set_position(self.handle, max(0, self.engine.get_position(self.handle) - seek))
        ui.message(f"Rewind {interval}s")

    @script(description="Fast forward", gesture=("kb:NVDA+Shift+'", "kb:NVDA+Shift+vk:0xDE"))
    def script_fastForward(self, gesture):
        if not self.engine or not self.handle: return
        interval = self.seek_intervals[self.current_interval_index]
        seek = self.engine.seconds_to_bytes(self.handle, interval)
        self.engine.set_position(self.handle, min(self.engine.get_length(self.handle), self.engine.get_position(self.handle) + seek))
        ui.message(f"Forward {interval}s")

    @script(description="Cycle interval", gesture=("kb:NVDA+Shift+J", "kb:NVDA+Shift+vk:0x4A"))
    def script_cycleInterval(self, gesture):
        self.current_interval_index = (self.current_interval_index + 1) % len(self.seek_intervals)
        config.conf["nvdaMediaPlayer"]["seekIntervalIndex"] = int(self.current_interval_index)
        ui.message(f"Interval {self.seek_intervals[self.current_interval_index]}s")

    @script(description="Volume Up", gesture=("kb:Alt+NVDA+'", "kb:Alt+NVDA+vk:0xDE"))
    def script_volumeUp(self, gesture):
        if not self.handle or not self.engine:
            ui.message("No audio active")
            return
        current_vol = self.engine.get_volume(self.handle)
        new_vol = min(1.0, current_vol + 0.05)
        self.engine.set_volume(self.handle, new_vol)
        config.conf["nvdaMediaPlayer"]["volume"] = float(new_vol)
        ui.message(f"Volume {int(new_vol * 100)}%")

    @script(description="Volume Down", gesture=("kb:Alt+NVDA+;", "kb:Alt+NVDA+vk:0xBA"))
    def script_volumeDown(self, gesture):
        if not self.handle or not self.engine:
            ui.message("No audio active")
            return
        current_vol = self.engine.get_volume(self.handle)
        new_vol = max(0.0, current_vol - 0.05)
        self.engine.set_volume(self.handle, new_vol)
        config.conf["nvdaMediaPlayer"]["volume"] = float(new_vol)
        ui.message(f"Volume {int(new_vol * 100)}%")
