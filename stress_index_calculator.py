import csv
import numpy as np


def read_csv(file_path):
    timestamps = []
    ecg_values = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            timestamps.append(float(row[0]))
            ecg_values.append(float(row[1]))
    return timestamps, ecg_values


def read_list(ecg):
    timestamps = []
    ecg_values = []
    for entry in ecg:
        timestamps.append(entry[0])
        ecg_values.append(entry[1])
    return timestamps, ecg_values


def remove_outstanding_intervals(intervals):
    count = round(len(intervals) * 0.01)
    rr_intervals = [interval for interval in intervals if 400 < interval < 1500]
    rr_intervals = sorted(rr_intervals)
    if count != 0:
        rr_intervals = rr_intervals[count:-count]
    return np.array(rr_intervals)


class StressIndexCalculator:
    def __init__(self, ecg=None, path_to_csv=None):
        self._stress_index = None
        self._range = None
        self._amo = None
        self._length_of_longest = None
        self._mo = None
        self._longest_group = None
        self._groups = None
        self._count_of_intervals = None
        self._max_rr = None
        self._min_rr = None
        self._processed_rr_intervals = None
        self.max_rr_count = -1
        self._rr_intervals = None
        self._peaks = None

        if path_to_csv is not None:
            self.timestamps, self.ecg_values = read_csv(path_to_csv)
        elif ecg is not None:
            (self.timestamps, self.ecg_values) = read_list(ecg)
        else:
            raise ValueError("Either path_to_csv or ecg must be provided.")

    def find_peaks(self, threshold):
        peaks = []
        for i in range(1, len(self.ecg_values) - 1):
            if (self.ecg_values[i] > threshold
                    and self.ecg_values[i] > self.ecg_values[i - 1] and
                    self.ecg_values[i] >= self.ecg_values[i + 1]):
                peaks.append(i)
        return peaks

    @property
    def peaks(self):
        if self._peaks is None:
            mean_ecg = np.mean(self.ecg_values)
            std_ecg = np.std(self.ecg_values)
            threshold = mean_ecg + 2 * std_ecg
            peaks = self.find_peaks(threshold)
            self._peaks = [self.timestamps[i] for i in peaks]
        return self._peaks

    @property
    def rr_intervals(self):
        if self._rr_intervals is None:
            self._rr_intervals = np.diff(self.peaks)
            if self.max_rr_count > 0:
                self._rr_intervals = self._rr_intervals[len(self.rr_intervals) - self.max_rr_count:]
        return self._rr_intervals, self.peaks[:-1]

    @property
    def processed_rr_intervals(self):
        if self._processed_rr_intervals is None:
            intervals = sorted(self.rr_intervals[0])
            intervals = remove_outstanding_intervals(intervals) / 1000
            self._processed_rr_intervals = intervals
        return self._processed_rr_intervals

    @property
    def count_of_intervals(self):
        if self._count_of_intervals is None:
            self._count_of_intervals = len(self.processed_rr_intervals)
        return self._count_of_intervals

    @property
    def min_rr(self):
        if self._min_rr is None:
            self._min_rr = self.processed_rr_intervals[0]
        return self._min_rr

    @property
    def max_rr(self):
        if self._max_rr is None:
            self._max_rr = self.processed_rr_intervals[-1]
        return self._max_rr

    @property
    def range(self):
        if self._range is None:
            self._range = self.max_rr - self.min_rr
        return self._range

    @property
    def groups(self):
        if self._groups is None:
            groups = [[] for _ in range(10)]
            for interval in self.processed_rr_intervals:
                index = int(10 * ((interval - self.min_rr) / (self.max_rr + 0.001 - self.min_rr)))
                groups[index].append(interval)
            self._groups = groups
        return self._groups

    @property
    def longest_group(self):
        if self._longest_group is None:
            self._longest_group = max(self.groups, key=len)
        return self._longest_group

    @property
    def length_of_longest(self):
        if self._length_of_longest is None:
            self._length_of_longest = len(self.longest_group)
        return self._length_of_longest

    @property
    def mo(self):
        if self._mo is None:
            self._mo = self.longest_group[self.length_of_longest // 2]
        return self._mo

    @property
    def amo(self):
        if self._amo is None:
            self._amo = self.length_of_longest / self.count_of_intervals
        return self._amo

    @property
    def stress_index(self):
        if self._stress_index is None:
            self._stress_index = 100 * self.amo / (2 * self.mo * self.range)
        return self._stress_index
