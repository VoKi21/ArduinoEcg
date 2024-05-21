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

        self.setWindowTitle('Heart Rate Monitor')
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.set_xlim([0, 10])
        self.ax.set_ylim([0, 150])

        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

        self.label_live = QLabel("Live Data:")
        self.layout.addWidget(self.label_live)

        self.combo_ports = QComboBox()
        self.combo_ports.addItem("--Select a /dev/ttyACM port--")
        for port in range(19):
            self.combo_ports.addItem(str(port))
        self.layout.addWidget(self.combo_ports)

        self.btn_open_serial = QPushButton("Open Serial")
        self.btn_open_serial.clicked.connect(self.start_serial)
        self.layout.addWidget(self.btn_open_serial)

        self.btn_close_serial = QPushButton("Close Serial")
        self.btn_close_serial.clicked.connect(self.kill_serial)
        self.layout.addWidget(self.btn_close_serial)

        self.recordText = QLabel("Not Recording")
        self.layout.addWidget(self.recordText)

        self.btn_start_recording = QPushButton("Start Recording")
        self.btn_start_recording.clicked.connect(self.start_recording)
        self.layout.addWidget(self.btn_start_recording)

        self.btn_stop_recording = QPushButton("Stop Recording")
        self.btn_stop_recording.clicked.connect(self.stop_recording)
        self.layout.addWidget(self.btn_stop_recording)

        self.ani = animation.FuncAnimation(self.fig, self.animate, interval=50, cache_frame_data=False)

        self.connection_label = QLabel("Not connected")
        self.layout.addWidget(self.connection_label)

        self.cache_limit_input = QLineEdit("30")
        self.cache_limit_input.setFixedHeight(30)
        self.cache_limit_input.setFixedWidth(100)
        only_int = QIntValidator()
        only_int.setRange(10, 1200)
        self.cache_limit_input.setValidator(only_int)
        self.layout.addWidget(self.cache_limit_input)

        self.stress_index_label = QLabel("Stress index: ")
        self.stress_index_label.setStyleSheet("color: blue")
        self.layout.addWidget(self.stress_index_label)

        self.stress_index_timer = QTimer(self)
        self.stress_index_timer.timeout.connect(self.update_stress_index)
        self.stress_index_timer.start(1000)

    def start_serial(self):
        port_index = self.combo_ports.currentIndex()
        if port_index == 0:
            return
        port = f'/dev/ttyACM{port_index - 1}'
        if self.serialReader.start_serial(port):
            self.connection_label.setText("Connected to " + port)
            self.connection_label.setStyleSheet("color: green")
        else:
            self.connection_label.setText("Error: wrong port?")
            self.connection_label.setStyleSheet("color: red")

    def kill_serial(self):
        self.serialReader.kill_serial()
        self.connection_label.setText("Not connected")
        self.connection_label.setStyleSheet("color: red")

    def animate(self, i):
        if len(self.serialReader.serialData) > 70:
            self.serialReader.serialData = self.serialReader.serialData[-70:]
        data = self.serialReader.serialData.copy()
        data = data[-70:]
        x = np.linspace(0, 69, dtype='int', num=70)
        self.ax.clear()
        self.ax.plot(x, data)

    def start_recording(self):
        if self.serialReader.start_recording():
            self.recordText.setText("Recording . . . ")
            self.recordText.setStyleSheet("color: red")
        else:
            QMessageBox.information(self, "Error", "Please start the serial monitor")

    def stop_recording(self):
        data = self.serialReader.stop_recording()
        if data is not None:
            self.recordText.setText("Not Recording  ")
            self.recordText.setStyleSheet("color: black")
            self.process_recording(data)
        else:
            QMessageBox.information(self, "Error", "You weren't recording!")

    def process_recording(self, data):
        directory, _ = QFileDialog.getSaveFileName(self, "Save Data", "", "CSV Files (*.csv);;All Files (*)")
        if directory:
            with open(directory, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Time', 'Value'])
                for timestamp, value in data:
                    writer.writerow([timestamp, value])

    def update_stress_index(self):
        ecg = self.serialReader.realtime_cache
        limit = int(self.cache_limit_input.text())
        limit = max(10, min(1200, limit))
        self.cache_limit_input.setText(f"{limit}")
        self.serialReader.cache_limit = limit
        try:
            if len(ecg) > 1000:
                calculator = StressIndexCalculator(ecg=ecg)
                stress_index = f"{calculator.stress_index}"
            else:
                stress_index = "waiting for more data..."
        except:
            stress_index = "error"

        self.stress_index_label.setText(f"Stress index: {stress_index}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialPlotter()
    window.show()
    sys.exit(app.exec_())
