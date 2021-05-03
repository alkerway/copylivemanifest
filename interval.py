from threading import Timer
import time
from log import log

class RepeatedTimer(object):
    def __init__(self, function, onStop, interval, durationSeconds):
        self._timer     = None
        self._startTime = self._getTimeSeconds()
        self.function   = function
        self.onStop = onStop
        self.interval   = interval
        self.durationSeconds = durationSeconds
        self.is_running = False
        self.start()
    
    def _getTimeSeconds(self):
        return int(round(time.time()))
    

    def _run(self):
        if self.getActiveTime() >= self.durationSeconds:
            self.stop()
            self.onStop()
        else:
            self.is_running = False
            self.start()
            self.function()

    def getActiveTime(self):
        return self._getTimeSeconds() - self._startTime

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        log('timer stop fn')
        self._timer.cancel()
        self.is_running = False
        self.onStop()
    