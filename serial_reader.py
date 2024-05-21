import serial
import threading
import time


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
            if (len(self.realtime_cache) > 0
                    and self.realtime_cache[len(self.realtime_cache) - 1][0] - self.realtime_cache[0][0]
                    >= self.cache_limit * 1000):
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
            data = self.serial_data_recorded
            self.serial_data_recorded = []
            return data
        return None
