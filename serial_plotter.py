from datetime import datetime
import sys

import numpy as np
import matplotlib.animation as animation
import csv
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QLineEdit
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from serial_reader import SerialReader
from stress_index_calculator import StressIndexCalculator


class SerialPlotter(QMainWindow):
    def __init__(self):
        super().__init__()

        self.serialReader = SerialReader()

        self.setWindowTitle('ЭКГ монитор')
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.graphics_widget = QWidget()
        self.graphics = QHBoxLayout(self.graphics_widget)
        self.layout.addWidget(self.graphics_widget)

        self.fig_ecg = Figure(figsize=(6, 5), dpi=100)
        self.ax_ecg = self.fig_ecg.add_subplot(1, 1, 1)
        self.ax_ecg.set_xlim([0, 10])
        self.ax_ecg.set_ylim([0, 150])

        self.fig_rr = Figure(figsize=(6, 5), dpi=100)
        self.ax_rr = self.fig_rr.add_subplot(1, 1, 1)
        self.ax_rr.set_xlim([0, 10])
        self.ax_rr.set_ylim([0, 150])

        self.canvas_ecg = FigureCanvas(self.fig_ecg)
        self.graphics.addWidget(self.canvas_ecg)

        self.canvas_rr = FigureCanvas(self.fig_rr)
        self.graphics.addWidget(self.canvas_rr)

        self.label_live = QLabel("ЭКГ:")
        self.layout.addWidget(self.label_live)

        self.combo_ports = QComboBox()
        self.combo_ports.addItem("--Выберите /dev/ttyACM порт--")
        for port in range(19):
            self.combo_ports.addItem(str(port))
        self.layout.addWidget(self.combo_ports)

        self.btn_open_serial = QPushButton("Подключиться к порту")
        self.btn_open_serial.clicked.connect(self.start_serial)
        self.layout.addWidget(self.btn_open_serial)

        self.btn_close_serial = QPushButton("Отключиться от порта")
        self.btn_close_serial.clicked.connect(self.kill_serial)
        self.layout.addWidget(self.btn_close_serial)

        self.connection_label = QLabel("Не подключено")
        self.layout.addWidget(self.connection_label)

        self.btn_start_recording = QPushButton("Начать запись")
        self.btn_start_recording.clicked.connect(self.start_recording)
        self.layout.addWidget(self.btn_start_recording)

        self.btn_stop_recording = QPushButton("Остановить и сохранить запись")
        self.btn_stop_recording.clicked.connect(self.stop_recording)
        self.layout.addWidget(self.btn_stop_recording)

        self.ani_ecg = animation.FuncAnimation(self.fig_ecg, self.animate_ecg, interval=50, cache_frame_data=False)
        self.ani_rr = animation.FuncAnimation(self.fig_rr, self.animate_rr, interval=500, cache_frame_data=False)

        self.recordText = QLabel("Запись выключена")
        self.layout.addWidget(self.recordText)

        self.combo_limit_type = QComboBox()
        self.combo_limit_type.addItem("секунды")
        self.combo_limit_type.addItem("RR интервалы")
        self.layout.addWidget(self.combo_limit_type)

        self.cache_limit_input = QLineEdit("100")
        self.cache_limit_input.setFixedHeight(30)
        self.cache_limit_input.setFixedWidth(100)
        only_int = QIntValidator()
        only_int.setRange(10, 1200)
        self.cache_limit_input.setValidator(only_int)
        self.layout.addWidget(self.cache_limit_input)

        self.stress_index_label = QLabel("Индекс напряжения: ")
        self.stress_index_label.setStyleSheet("color: blue")
        self.layout.addWidget(self.stress_index_label)

        self.latest_rr_label = QLabel("Последний RR интервал: ")
        self.latest_rr_label.setStyleSheet("color: blue")
        self.layout.addWidget(self.latest_rr_label)

        self.stress_index_timer = QTimer(self)
        self.stress_index_timer.timeout.connect(self.update_info)
        self.stress_index_timer.start(1000)

        self.rr_intervals = []
        self.si_history = []

    def closeEvent(self, event):
        self.stop_recording()
        self.kill_serial()

    def start_serial(self):
        if self.serialReader.serialOpen:
            return
        port_index = self.combo_ports.currentIndex()
        if port_index == 0:
            port_index = 1
        port = f'/dev/ttyACM{port_index - 1}'
        if self.serialReader.start_serial(port):
            self.connection_label.setText("Подключено к порту " + port)
            self.connection_label.setStyleSheet("color: green")
        else:
            self.connection_label.setText("Ошибка: какой порт?")
            self.connection_label.setStyleSheet("color: red")

    def kill_serial(self):
        if not self.serialReader.serialOpen:
            return
        self.serialReader.kill_serial()
        self.connection_label.setText("Не подключено")
        self.connection_label.setStyleSheet("color: red")

    def animate_ecg(self, i):
        if len(self.serialReader.serialData) > 70:
            self.serialReader.serialData = self.serialReader.serialData[-70:]
        data = self.serialReader.serialData.copy()
        data = data[-70:]
        x = np.linspace(0, 69, dtype='int', num=70)
        self.ax_ecg.clear()
        self.ax_ecg.plot(x, data)

    def animate_rr(self, i):
        if len(self.rr_intervals) > 0:
            self.ax_rr.clear()
            self.ax_rr.plot(self.rr_intervals)

    def start_recording(self):
        if self.serialReader.recording:
            return
        if self.serialReader.start_recording():
            self.recordText.setText("Запись . . . ")
            self.recordText.setStyleSheet("color: red")
        else:
            QMessageBox.information(self, "Ошибка", "Подключитесь к порту")

    def stop_recording(self):
        if not self.serialReader.recording:
            return
        data = self.serialReader.stop_recording()
        if data is not None:
            self.recordText.setText("Запись выключена  ")
            self.recordText.setStyleSheet("color: black")
            self.process_recording(data)
        else:
            QMessageBox.information(self, "Ошибка", "Сначала начните запись!")

    def process_recording(self, data):
        (rr_intervals, rr_timestamps) = StressIndexCalculator(data).rr_intervals
        stress_indices = []
        si_timestamps = []
        for si_timestamp, stress_index in self.si_history:
            stress_indices.append(stress_index)
            si_timestamps.append(si_timestamp)

        new_data = []
        for i in range(len(data)):
            new_data.append([])
            new_data[i].append(data[i][0])
            new_data[i].append(data[i][1])

        for i in range(len(rr_intervals)):
            curr_time = rr_timestamps[i]
            for j in range(len(new_data)):
                if new_data[j][0] == curr_time:
                    new_data[j].append(rr_intervals[i])
                    break

        for i in range(len(stress_indices)):
            curr_time = si_timestamps[i]
            for j in range(len(new_data)):
                if new_data[j][0] == curr_time:
                    new_data[j].append(stress_indices[i])
                    break

        previous_rr = 0
        previous_si = 0
        for entry in new_data:
            if len(entry) < 3:
                entry.append(previous_rr)
                entry.append(previous_si)
            else:
                if len(entry) < 4:
                    previous_rr = entry[2]
                    entry.append(previous_si)
                else:
                    previous_si = entry[3]
                    previous_rr = entry[2]

        directory, _ = QFileDialog.getSaveFileName(self, "Сохранить ЭКГ", "/home/ralen/Документы", "CSV Files (*.csv);;All Files (*)")
        if directory:
            with open(f"{directory}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv", 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Time', 'Value', 'RR', 'SI'])
                for timestamp, value, rr, si in new_data:
                    writer.writerow([timestamp, value, rr, si])
        self.si_history = []

    def update_info(self):
        time = self.combo_limit_type.currentIndex() == 0
        ecg = self.serialReader.realtime_cache
        text = self.cache_limit_input.text().strip()
        text = 10 if text == "" or int(text) < 10 else int(text)
        limit = int(text)
        limit = min(1200, limit)
        if text > 1200:
            self.cache_limit_input.setText(f"{limit}")
        self.serialReader.cache_limit = limit if time else limit * 2
        try:
            if len(ecg) > 1000:
                calculator = StressIndexCalculator(ecg=ecg)
                calculator.max_rr_count = -1 if time or self.serialReader.recording else limit
                self.rr_intervals = calculator.rr_intervals[0]
                stress_index = f"{calculator.stress_index}"
                if self.serialReader.recording:
                    self.si_history.append((calculator.rr_intervals[1][-1], calculator.stress_index))
                latest_rr = f"{calculator.rr_intervals[0][-1]}"
            else:
                stress_index = "идёт сбор данных..."
                latest_rr = stress_index
        except:
            stress_index = "ошибка"
            latest_rr = stress_index

        self.stress_index_label.setText(f"Индекс напряжения: {stress_index}")
        self.latest_rr_label.setText(f"Последний RR интервал: {latest_rr}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialPlotter()
    window.show()
    sys.exit(app.exec_())
