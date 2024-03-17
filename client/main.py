import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Union

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
import zroya
from filelock import FileLock
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5 import uic
from PyQt5.QtCore import (QBuffer, QObject, QRect, QRunnable, Qt, QThreadPool,
                          QTimer, pyqtSignal, pyqtSlot)
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtMultimedia import QCamera, QCameraImageCapture, QCameraInfo
from PyQt5.QtMultimediaWidgets import QCameraViewfinder
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton

APPID = 'is119.ihunch-escape.client.0-dev'
API_HOST = 'api.ihunch.koyo.io'
DATETIME_FORMAT = '%Y%m%d-%H%M%S'

BASE_DIR = Path(__file__).resolve(strict=True).parent
DATA_DIR = BASE_DIR / 'data'
PHOTOS_DIR = BASE_DIR / 'photos'

RecordType = Dict[str, Union[str, bool, float]]
SettingsType = Dict[str, Union[bool, int]]

Form, Window = uic.loadUiType('dialog.ui')


def qimage_to_bytes(qimg: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    try:
        qimg.save(buffer, 'jpg')
        return bytes(buffer.data())
    finally:
        buffer.close()


def upload_image_api(bimg: bytes, *, s: requests.Session = requests.session()) -> requests.Response:
    return s.post(f'https://{API_HOST}/upload', files={'file': bimg})


def upload_image_save_record(qimg: QImage) -> RecordType:
    bimg = qimage_to_bytes(qimg)
    r = upload_image_api(bimg)
    timestamp = datetime.now().strftime(DATETIME_FORMAT)
    photo = PHOTOS_DIR / f'{timestamp}.jpg'
    with photo.open('wb') as f:
        f.write(bimg)
    success = r.status_code == requests.codes.ok
    record = RecordsDriver.create(timestamp, success, False, 0.0)
    if success:
        j = r.json()
        record['human'] = j['human']
        record['ihunch'] = j['pred']
    RecordsDriver.append(record)
    return record


def today_truncated():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


class RecordsDriver:
    _file = DATA_DIR / 'records.json'
    _lock = FileLock(_file.parent / f'{_file.name}.lock')

    @classmethod
    def _load(cls) -> List[RecordType]:
        try:
            records = json.load(cls._file.open('r'))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            records = []
        return records

    @classmethod
    def _save(cls, records: List[RecordType]) -> None:
        json.dump(records, cls._file.open('w'))

    @classmethod
    def load(cls, beg: Optional[datetime] = None, end: Optional[datetime] = None) -> List[RecordType]:
        with cls._lock:
            records = cls._load()
        beg = beg.strftime(DATETIME_FORMAT) if beg is not None else None
        end = end.strftime(DATETIME_FORMAT) if end is not None else None
        if beg is not None and end is not None:
            records = [x for x in records if beg < x['timestamp'] < end]
        elif beg is not None:
            records = [x for x in records if beg < x['timestamp']]
        elif end is not None:
            records = [x for x in records if x['timestamp'] < end]
        return records

    @classmethod
    def append(cls, record: RecordType) -> None:
        with cls._lock:
            records = cls._load()
            records.append(record)
            cls._save(records)

    @staticmethod
    def create(timestamp: str, success: bool, human: bool, ihunch: float) -> RecordType:
        return {'timestamp': timestamp, 'success': success, 'human': human, 'ihunch': ihunch}


class SettingsDriver:
    _file = DATA_DIR / 'settings.json'
    _lock = FileLock(_file.parent / f'{_file.name}.lock')

    @staticmethod
    def _initialized() -> SettingsType:
        return {'warn': True, 'stat': True, 'record': True, 'stat_index': 0, 'record_index': 0}

    @classmethod
    def _load(cls) -> SettingsType:
        try:
            settings = json.load(cls._file.open('r'))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            settings = cls._initialized()
        return settings

    @classmethod
    def _save(cls, settings: SettingsType) -> None:
        json.dump(settings, cls._file.open('w'))

    @classmethod
    def load(cls) -> SettingsType:
        with cls._lock:
            return cls._load()

    @classmethod
    def save(cls, settings: SettingsType) -> None:
        with cls._lock:
            cls._save(settings)

    @classmethod
    def init(cls) -> SettingsType:
        with cls._lock:
            settings = cls._initialized()
            cls._save(settings)
            return settings


class Notifier:
    __slots__ = ['_t', '_nid']
    _ = None

    def __init__(self, acts: Iterable[str] = []):
        if __class__._ is None:
            __class__._ = zroya.init('iHunch Escape No. 1', *APPID.split('.'))
        self._t = zroya.Template(zroya.TemplateType.Text4)
        for act in acts:
            self._t.addAction(act)
        self._nid = None

    def notify(self, line1: str, line2: str, attr: Optional[str] = None,
               on_click: Optional[Callable] = None, on_action: Optional[Callable] = None,
               on_dismiss: Optional[Callable] = None, on_fail: Optional[Callable] = None) -> None:
        self._t.setFirstLine(line1)
        self._t.setSecondLine(line2)
        if attr is not None:
            self._t.setAttribution(attr)
        self._nid = zroya.show(self._t, on_click, on_action, on_dismiss, on_fail)

    def hide(self) -> None:
        if self._nid is not None:
            zroya.hide(self._nid)

    @staticmethod
    def create_notifier(first_line: str, second_line: str, attribution: str, actions: list) -> zroya.Template:
        t = zroya.Template(zroya.TemplateType.Text4)
        t.setFirstLine(first_line)
        t.setSecondLine(second_line)
        t.setAttribution(attribution)
        for action in actions:
            t.addAction(action)
        return t


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    __slots__ = ['fn', 'args', 'kwargs', 'signals']

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class StatCanvas(FigureCanvasQTAgg):
    __slots__ = ['fig', 'ax']

    def __init__(self, parent, object_name, width=640, height=480):
        self.fig = plt.Figure()
        dpi = self.fig.get_dpi()
        self.fig.set_size_inches(width / dpi, height / dpi)
        self.ax = self.fig.add_subplot(1, 1, 1)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setGeometry(QRect(-1, 53, width + 1, height + 1))
        self.setObjectName(object_name)

    def plot_today_vs_yesterday(self) -> None:
        today = today_truncated()
        yesterday = today - timedelta(days=1)
        records = RecordsDriver.load(beg=yesterday)
        if not records:
            return
        df = pd.DataFrame(records)
        timestamp = pd.to_datetime(df.timestamp)
        df['day'] = timestamp.dt.day
        df['hour'] = timestamp.dt.hour
        df = df.groupby(['day', 'hour'], as_index=False).mean()
        self.ax.cla()
        sns.lineplot(x='hour', y='ihunch', hue='day', style='day', data=df,
                     legend='full', marker='.', linewidth=2, ax=self.ax)
        self.ax.axhline(y=0.5, ls=':', c='.5')
        self.ax.set(xlim=(0, 24), ylim=(0, 1))

    def plot_week_to_day(self) -> None:
        today = today_truncated()
        a_week_ago = today - timedelta(days=7)
        records = RecordsDriver.load(beg=a_week_ago)
        if not records:
            return
        df = pd.DataFrame(records)
        timestamp = pd.to_datetime(df.timestamp)
        df['day'] = timestamp.dt.day
        df = df.groupby('day', as_index=False).mean()
        self.ax.cla()
        sns.lineplot(x='day', y='ihunch', ci=None, marker='o', color='r',
                    dashes=False, linewidth=2, data=df, ax=self.ax)
        self.ax.axhline(y=0.5, ls=':', c='.5')
        self.ax.set(xlim=(a_week_ago.day, today.day), ylim=(0, 1))

    def plot_week_to_percent(self) -> None:
        today = today_truncated()
        a_week_ago = today - timedelta(days=7)
        records = RecordsDriver.load(beg=a_week_ago)
        if not records:
            return
        df = pd.DataFrame(records)
        timestamp = pd.to_datetime(df.timestamp)
        df['day'] = timestamp.dt.day
        df['ihunch'] = df.ihunch >= 0.5
        df = df.groupby('day', as_index=False).mean()
        self.ax.cla()
        sns.barplot(x='day', y='ihunch', data=df, ax=self.ax)
        self.ax.set(ylim=(0, 1))


class MyWindow(Window, Form):
    __slots__ = [
        # widgets
        'cameraViewfinder',
        'statCanvas0',
        'statCanvas1',
        'statCanvas2',
        # commons
        'threadpool',
        # camera
        'camera',
        'capture',
        'capture_timer',
        # photo
        'photo_timestamp',
        'photo_pixmap',
        # setting
        'warn_notifier',
        'warn_notifier_timer',
        'stat_notifier',
        'stat_notifier_timer',
    ]

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # widgets
        self.cameraViewfinder = QCameraViewfinder(self.cameraWidget)
        self.cameraViewfinder.setGeometry(QRect(-1, 52, 641, 481))
        self.cameraViewfinder.setObjectName('cameraViewfinder')
        self.statCanvas0 = StatCanvas(self.statWidget0, 'statCanvas0', 640, 480)
        self.statCanvas1 = StatCanvas(self.statWidget1, 'statCanvas1', 640, 480)
        self.statCanvas2 = StatCanvas(self.statWidget2, 'statCanvas2', 640, 480)

        # common
        self.threadpool = QThreadPool()
        # camera
        self.camera = None
        self.capture = None
        self.init_camera_and_capture()
        self.capture_timer = self.create_timer(5_000, self.capture_safe)
        # photo
        self.photo_timestamp = None
        self.photo_pixmap = QPixmap()
        # setting
        self.warn_notifier = Notifier(['확인', '무시'])
        self.warn_notifier_timer = self.create_timer(60_000, self.notify_warn_if_bad)
        self.stat_notifier = Notifier(['확인', '무시'])
        self.stat_notifier_timer = self.create_timer(self.get_setting_stat_interval(), self.notify_stat)

        # connect: camera
        self.cameraButton.toggled.connect(lambda toggle: self.cameraButton.setText('정지' if toggle else '시작'))
        self.cameraButton.toggled.connect(self.toggle_all_timers)
        # connect: stat, photo
        self.statTabWidget.tabBarClicked.connect(self.load_stat)
        self.tabWidget.tabBarClicked.connect(lambda index:
                                             self.load_photo() if index == 1 else
                                             self.load_stat(self.statTabWidget.currentIndex()) if index == 2 else None)
        self.photoLeftButton.clicked.connect(lambda: self.load_photo(left=True))
        self.photoRightButton.clicked.connect(lambda: self.load_photo(right=True))
        # connect: setting
        self.settingWarnButton.toggled.connect(self.toggle_warn_timer)
        self.connect_setting_stat_cycle_selected(self.settingStatCycleOff)
        self.connect_setting_stat_cycle_selected(self.settingStatCycle1)
        self.connect_setting_stat_cycle_selected(self.settingStatCycle2)
        self.connect_setting_stat_cycle_selected(self.settingStatCycle3)
        self.connect_setting_stat_cycle_selected(self.settingStatCycle6)
        self.settingStatTestButton.pressed.connect(lambda: self.settingStatTestButton.setIcon(QIcon('resource/test_off.png')))
        self.settingStatTestButton.released.connect(lambda: self.settingStatTestButton.setIcon(QIcon('resource/test_on.png')))
        self.settingStatTestButton.clicked.connect(self.notify_stat)

    def connect_setting_stat_cycle_selected(self, cycle: QPushButton) -> None:
        def selected(toggle: bool) -> None:
            checkeds = [x for x in others if x.isChecked()]
            if not checkeds:
                cycle.setChecked(True)
            elif toggle:
                checkeds[0].setChecked(False)
                self.toggle_stat_timer(cycle is not self.settingStatCycleOff)
        others: List[QPushButton] = [
            self.settingStatCycle1,
            self.settingStatCycle2,
            self.settingStatCycle3,
            self.settingStatCycle6,
            self.settingStatCycleOff,
        ]
        others.remove(cycle)
        cycle.toggled.connect(selected)

    def init_camera_and_capture(self) -> bool:
        available_cameras = QCameraInfo.availableCameras()
        if not available_cameras:
            return False
        self.camera = self.create_camera(available_cameras, 0, self.cameraViewfinder, self.error_camera)
        self.capture = self.create_capture(self.camera, self.process_image_on_threadpool, self.error_camera)
        if self.camera.isAvailable():
            self.camera.start()
        return True

    def check_camera(self) -> bool:
        if (self.camera is None or not self.camera.isAvailable()) and not self.init_camera_and_capture():
            return False
        if not self.capture.isReadyForCapture():
            self.camera.start()
        return True

    def start_capture_timer_safe(self) -> None:
        if self.check_camera():
            self.capture_timer.start()
        else:
            self.error_camera()

    def capture_safe(self) -> None:
        if self.check_camera():
            self.capture.capture()
        else:
            self.error_camera()

    def error_camera(self, *args) -> None:
        self.cameraButton.setChecked(False)

    def get_setting_stat_interval(self) -> int:
        cycles: List[QPushButton] = [
            self.settingStatCycle1,
            self.settingStatCycle2,
            self.settingStatCycle3,
            self.settingStatCycle6,
        ]
        checkeds = [x for x in cycles if x.isChecked()]
        text = checkeds[0].objectName().replace('settingStatCycle', '', 1) if checkeds else 1
        msec = int(text) * 3_600_000
        return msec

    def process_image_on_threadpool(self, id: int, qimg: QImage) -> None:
        def display_result(record: RecordType) -> None:
            if record['success']:
                self.display_ihunch_status(self.cameraStatusBar, record['human'], record['ihunch'])
        worker = Worker(upload_image_save_record, qimg)
        worker.signals.result.connect(display_result)
        self.threadpool.start(worker)

    def load_stat(self, index: int = 0) -> None:
        statCanvas = getattr(self, f'statCanvas{index}')
        if index == 0:
            statCanvas.plot_today_vs_yesterday()
        elif index == 1:
            statCanvas.plot_week_to_day()
        else:
            statCanvas.plot_week_to_percent()
        statCanvas.draw()

    def load_photo(self, left=False, right=False) -> None:
        beg, end = None, None
        index = -1
        if left:
            end = self.photo_timestamp
        elif right:
            beg = self.photo_timestamp
            index = 0
        records = RecordsDriver.load(beg, end)
        if records:
            record = records[index]
            timestamp = record['timestamp']
            self.photo_timestamp = datetime.strptime(timestamp, DATETIME_FORMAT)
            self.photo_pixmap.load(str(PHOTOS_DIR / f'{timestamp}.jpg'))
            self.photoImage.setPixmap(self.photo_pixmap)
            self.display_ihunch_status(self.photoStatusBar, record['human'], record['ihunch'])

    def toggle_all_timers(self, toggle: bool) -> None:
        if toggle:
            self.start_capture_timer_safe()
        else:
            self.capture_timer.stop()
        self.toggle_warn_timer(toggle)
        self.toggle_stat_timer(toggle)

    def toggle_warn_timer(self, toggle: bool) -> None:
        if toggle and self.cameraButton.isChecked():
            self.warn_notifier_timer.start()
        else:
            self.warn_notifier_timer.stop()

    def toggle_stat_timer(self, toggle: bool) -> None:
        if toggle and self.cameraButton.isChecked():
            self.stat_notifier_timer.setInterval(self.get_setting_stat_interval())
            self.stat_notifier_timer.start()
        else:
            self.stat_notifier_timer.stop()

    def notify_warn_if_bad(self) -> None:
        minutes = 5
        beg = datetime.now() - timedelta(minutes=minutes)
        records = RecordsDriver.load(beg)
        stats = [x['ihunch'] > 0.5 for x in records if x['human']]
        if not stats:
            return
        ihunch_percent = sum(stats) / len(stats) * 100
        if ihunch_percent < 90:
            return
        self.warn_notifier.notify('거북목 경고',
                                  f'최근 {minutes}분 중에 거북목 자세 비중이 {ihunch_percent:.2f}%를 차지합니다!',
                                  '거북목 탈출 넘버원',
                                  on_action=lambda nid, index: self.settingWarnButton.setChecked(False) if index == 1 else None)

    def notify_stat(self) -> None:
        hours = self.stat_notifier_timer.interval() // 3_600_000
        beg = datetime.now() - timedelta(hours=hours)
        records = RecordsDriver.load(beg)
        stats = [x['ihunch'] > 0.5 for x in records if x['human']]
        if not stats:
            return
        ihunch_percent = sum(stats) / len(stats) * 100
        self.stat_notifier.notify('최근 거북목 통계',
                                  f'최근 {hours}시간 중에 거북목 자세 비중이 {ihunch_percent:.2f}%를 차지했습니다.',
                                  '거북목 탈출 넘버원',
                                  on_action=lambda nid, index: self.settingStatCycleOff.setChecked(True) if index == 1 else None)

    @staticmethod
    def create_camera(cameras: list, index: int, viewfinder: QCameraViewfinder, error: Callable) -> QCamera:
        camera = QCamera(cameras[index])
        camera.setViewfinder(viewfinder)
        camera.setCaptureMode(QCamera.CaptureStillImage)
        camera.error.connect(error)
        return camera

    @staticmethod
    def create_capture(camera: QCamera, callback: Callable, error: Callable) -> QCameraImageCapture:
        capture = QCameraImageCapture(camera)
        capture.setCaptureDestination(QCameraImageCapture.CaptureToBuffer)
        capture.imageCaptured.connect(callback)
        capture.error.connect(error)
        return capture

    @staticmethod
    def create_timer(interval: int, callback: Callable) -> QTimer:
        timer = QTimer()
        timer.setInterval(interval)
        timer.timeout.connect(callback)
        return timer

    @staticmethod
    def display_ihunch_status(statusbar: QLabel, human: bool, ihunch: float) -> None:
        if human:
            if ihunch > 0.5:
                text, color = '거북목', 'FF0000'
            else:
                text, color = '정상', '23F200'
            text += f' ({ihunch:.4f})'
        else:
            text, color = '자리비움', 'FF971E'
        statusbar.setText(text)
        statusbar.setAlignment(Qt.AlignCenter)
        statusbar.setStyleSheet(f'color: #{color};')


def main():
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
