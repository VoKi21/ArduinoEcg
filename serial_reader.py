import serial
import threading
import time


def trim_cache_time(cache, time_len, destination):
    to_remove = int(len(cache) - (destination * len(cache) / time_len))
    return cache[to_remove:]


class SerialReader:
    def __init__(self):
        self.thread = None
        self.ser = None
        self.serialOpen = False
        self.recording = False
        self.serial_data_recorded = []
        self.serialData = [0] * 70
        self.realtime_cache = []
        self.cache_limit = 30

    def start_serial(self, port):
        try:
            self.ser = serial.Serial(port, 200, timeout=20)
            self.ser.close()
            self.ser.open()
            self.serialOpen = True
            self.thread = threading.Thread(target=self.read_from_port)
            self.thread.start()
            return True
        except serial.SerialException:
            return False

    def kill_serial(self):
        if hasattr(self, 'ser'):
            self.serialOpen = False
            time.sleep(1)
            self.ser.close()

    def read_from_port(self):
        while self.serialOpen:
            (timestamp, reading) = self.ser.readline().strip().split()
            (timestamp, reading) = (float(timestamp), int(reading))
            self.serialData.append(reading)
            if len(self.realtime_cache) > 0:
                time_len = self.realtime_cache[len(self.realtime_cache) - 1][0] - self.realtime_cache[0][0]
                if time_len >= self.cache_limit * 1000 and not self.recording:
                    if float(time_len) / (self.cache_limit * 1000.0) >= 1.25:
                        self.realtime_cache = trim_cache_time(self.realtime_cache, time_len, self.cache_limit * 1000)
                    else:
                        self.realtime_cache.pop(0)
            self.realtime_cache.append((timestamp, reading))
            if self.recording:
                self.serial_data_recorded.append((timestamp, reading))

    def start_recording(self):
        if self.serialOpen:
            self.recording = True
            return True
        return False

    def stop_recording(self):
        if self.recording:
            self.recording = False
            data = self.serial_data_recorded.copy()
            self.serial_data_recorded = []
            return data
        return None
