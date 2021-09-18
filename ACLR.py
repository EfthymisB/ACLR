import sys
from PySide2 import QtWidgets, QtCore, QtGui
from functools import partial
import multiprocessing
import subprocess
import signal
import os



def run_structure(scene_file, destination, start_f, end_f, step_f, threads, process):

    if not scene_file.text():
        scene_file.setFocus()
        return
    elif not os.path.isfile(scene_file.text().replace('\\', '/')):
        scene_file.setSelection(0, len(scene_file.text()))
        return
    elif not destination.text():
        destination.setFocus()
        return
    elif not os.path.isdir(destination.text()):
        destination.setSelection(0, len(destination.text()))
        return
    process.start(f'cmd.exe /C Render -r arnold -s {start_f} -e {end_f} -b {step_f} -ai:threads {threads} -rd {destination.text()} '
                  f'-postFrame $s=`currentTime-q`;print("""Frame_"""+$s+"""_completed\\n"""); '
                  f'-postRender print("""Render_finished\\n"""); {scene_file.text()}')
    return True

class MainProjectWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(MainProjectWindow, self).__init__(parent)

        self.mainLayout = None
        self.mainGroupBox = None
        self.mainGroupBoxLayout = None
        self.secondGroupBox = None
        self.secondGroupBoxLayout = None
        self.scene_file = None
        self.destination_path = None
        self.startFrame = None
        self.endFrame = None
        self.stepFrame = None
        self.nameWidget = None
        self.folderWidget = None
        self.frames_and_render_layout = None
        self.thirdGroupBoxLayout_2 = None
        self.thirdGroupBox = None
        self.thirdGroupBoxLayout = None
        self.third_layout_1 = None
        self.third_layout_2 = None

        self.setup_ui()

        self._process = QtCore.QProcess(self)
        self._process.started.connect(self.handleStarted)
        self._process.finished.connect(self.handleFinished)
        self._process.error.connect(self.handleError)

        self._time = QtCore.QTime()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.handleTimeout)

    def closeEvent(self, event):
        if self._timer.isActive():
            event.ignore()
        else:
            QtWidgets.QWidget.closeEvent(self, event)

    def handleTimeout(self):
        self.button_stop.setText('Elapsed: %.*f' % (2, self._time.elapsed() / 1000.0))
        data = bytearray(self._process.readAllStandardOutput()).decode('utf-8').rstrip()
        if 'Frame_' in data:
            self.progress_bar_value += (100 / ((self.endFrame.value() - self.startFrame.value()) / self.stepFrame.value()))
            self.progress_bar.setValue(self.progress_bar_value)
            old_frames = self.progress_bar.format().split('/')
            self.progress_bar.setFormat(f'{int(old_frames[0]) + 1}/{old_frames[1]}')

    def handleStarted(self):
        self.button_create.setDisabled(True)
        self.button_stop.setDisabled(False)
        self._time.start()
        self._timer.start(100)

    def handleFinished(self):
        self._timer.stop()
        self.button_create.setDisabled(False)
        self.button_stop.setDisabled(True)
        self.progress_bar.setValue(100)

    def handleError(self, error):
        if error == QtCore.QProcess.CrashExit:
            print('Process killed')
        else:
            print(self._process.errorString())

    def handleButtonStop(self):
        if self._timer.isActive():
            self._process.close()
            os.kill(self._process.processId(), signal.CTRL_C_EVENT)
            self.button_create.click()

    def setup_ui(self):
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.mainLayout)
        self.setFixedSize(500, 300)
        self.setWindowTitle("Arnold Command-line rendering")

        self.create_main_groups()
        self.create_widgets()
        self.create_confirm_buttons()

    def create_main_groups(self):
        self.mainGroupBox = QtWidgets.QGroupBox("Project Structure")
        self.mainGroupBoxLayout = QtWidgets.QVBoxLayout(self.mainGroupBox)
        self.mainLayout.addWidget(self.mainGroupBox)

        self.frames_and_render_layout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.addLayout(self.frames_and_render_layout)

        self.secondGroupBox = QtWidgets.QGroupBox("Frames")
        self.secondGroupBoxLayout = QtWidgets.QFormLayout(self.secondGroupBox)
        self.frames_and_render_layout.addWidget(self.secondGroupBox, 2)

        self.thirdGroupBox = QtWidgets.QGroupBox("Render device")
        self.thirdGroupBoxLayout = QtWidgets.QVBoxLayout(self.thirdGroupBox)

        self.frames_and_render_layout.addWidget(self.thirdGroupBox, 6)

    def total_frames(self):
        frames = (self.endFrame.value() - self.startFrame.value()) + 1
        total_frames = int(frames / self.stepFrame.value())
        if total_frames == 0:
            total_frames += 1
        self.progress_bar.setFormat(f'0/{total_frames} frames                    %p%')

    def prepare_render(self):
        self.progress_bar.setValue(0)
        self.progress_bar_value = 0

        if run_structure(self.scene_file, self.destination_path, self.startFrame.value(), self.endFrame.value(), self.stepFrame.value(), self.thread_slider.value(), self._process):
            self.close()

    def create_confirm_buttons(self):
        self.mainLayout.addLayout(self.frames_and_render_layout)
        self.mainLayout.addStretch()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar_value = 0
        self.total_frames()
        self.mainLayout.addWidget(self.progress_bar)

        confirm_layout = QtWidgets.QHBoxLayout()
        self.mainLayout.addLayout(confirm_layout)

        self.button_create = QtWidgets.QPushButton("Render")
        self.button_stop = QtWidgets.QPushButton("Stop")
        self.button_stop.setDisabled(True)
        button_cancel = QtWidgets.QPushButton("Cancel")

        confirm_layout.addWidget(self.button_create)
        confirm_layout.addWidget(self.button_stop)
        confirm_layout.addWidget(button_cancel)

        self.button_create.clicked.connect(partial(self.prepare_render))
        self.button_stop.clicked.connect(partial(self.handleButtonStop))
        button_cancel.clicked.connect(partial(self.close))

        check_env_layout = QtWidgets.QHBoxLayout()

        self.check_env_but = QtWidgets.QPushButton()
        self.check_env_but.setFixedSize(20, 20)
        self.check_env_but.clicked.connect(partial(self.check_env))

        check_env_font = QtGui.QFont()
        self.check_env_label = QtWidgets.QLabel()
        self.check_env_label.setFont(check_env_font)

        self.check_env()

        check_env_layout.addWidget(self.check_env_but)
        check_env_layout.addWidget(self.check_env_label)

        self.mainLayout.addLayout(check_env_layout)
        self.mainLayout.addStretch()

    def check_env(self):
        try:
            subprocess.check_call(['where', 'Render'])
            self.check_env_but.setStyleSheet("border-radius : 10;"
                                 "background-color: qradialgradient(spread:pad, cx:0.5, cy:0.5, radius:0.5, fx:0.5, "
                                 "fy:0.5, stop:0 rgba(0, 200, 0, 255), stop:0.642045 rgba(34, 220, 34, 255), "
                                 "stop:0.977273 rgba(0, 220, 0, 0));")
            self.check_env_label.setText('Render.exe Path found!')
            self.button_create.setDisabled(False)
        except subprocess.CalledProcessError:
            self.check_env_but.setStyleSheet("border-radius : 10;"
                                 "background-color: qradialgradient(spread:pad, cx:0.5, cy:0.5, radius:0.5, fx:0.5, "
                                 "fy:0.5, stop:0 rgba(200, 0, 0, 255), stop:0.642045 rgba(220, 34, 34, 255), "
                                 "stop:0.977273 rgba(220, 0, 0, 0));")
            self.check_env_label.setText("Render.exe Path missing! Edit your system's Path Environment Variable and add a new\n"
                                         "path pointing to the bin folder of your Maya version and restart the application.")
            self.button_create.setDisabled(True)

    def create_widgets(self):

        scene_file_layout, scene_file = self.create_inputs("Scene file", ".ma / .mb", True)
        destination_path_layout, destination_path = self.create_inputs("Output path", "Enter a directory", False)
        self.scene_file = scene_file
        self.destination_path = destination_path

        self.mainGroupBoxLayout.addLayout(scene_file_layout)
        self.mainGroupBoxLayout.addLayout(destination_path_layout)
        self.mainGroupBoxLayout.addStretch()

        self.startFrame = self.create_spinboxes('Start:', 2500, 1, 1, True, True)
        self.endFrame = self.create_spinboxes('End:', 2500, 1, 1, True, False)
        self.stepFrame = self.create_spinboxes('Step:', 2500, 1, 1)
        self.startFrame.valueChanged.connect(self.total_frames)
        self.endFrame.valueChanged.connect(self.total_frames)
        self.stepFrame.valueChanged.connect(self.total_frames)

        self.thread_label = QtWidgets.QLabel('Number of threads')

        self.thread_slider = QtWidgets.QSlider()
        self.thread_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.thread_slider.setValue(multiprocessing.cpu_count())
        self.thread_slider.setMinimum(1)
        self.thread_slider.setPageStep(1)
        self.thread_slider.setMaximum(multiprocessing.cpu_count())
        self.thread_slider.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.thread_slider.setTickInterval(2)
        self.thread_slider.valueChanged.connect(self.slider_update)
        self.thirdGroupBoxLayout.addWidget(self.thread_label, 1, QtCore.Qt.AlignCenter)
        self.thirdGroupBoxLayout.addWidget(self.thread_slider)

        self.slider_labels_layout = QtWidgets.QHBoxLayout()
        self.thirdGroupBoxLayout.addLayout(self.slider_labels_layout)

        self.slider_min = QtWidgets.QLabel('1')
        self.slider_value = QtWidgets.QLabel(f'{multiprocessing.cpu_count()}')
        my_font = QtGui.QFont()
        my_font.setBold(True)
        self.slider_value.setFont(my_font)
        self.slider_max = QtWidgets.QLabel(f'{multiprocessing.cpu_count()}')

        self.slider_labels_layout.addWidget(self.slider_min, 1, QtCore.Qt.AlignLeft)
        self.slider_labels_layout.addWidget(self.slider_value, 1, QtCore.Qt.AlignCenter)
        self.slider_labels_layout.addWidget(self.slider_max, 1, QtCore.Qt.AlignRight)

    def slider_update(self, value):
        self.slider_value.setText(str(value))

    def spin_box_validator(self, start, value):
        if start:
            end_frame = self.endFrame.value()
            if value > end_frame:
                self.startFrame.setValue(end_frame)
        else:
            start_frame = self.startFrame.value()
            if value < start_frame:
                self.endFrame.setValue(start_frame)

    def create_inputs(self, attribute_name, help_text, is_file):
        h_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel(attribute_name)
        line_edit = QtWidgets.QLineEdit()
        line_edit.setPlaceholderText(help_text)

        sel_dir_but = QtWidgets.QPushButton()
        sel_dir_but.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogOpenButton")))
        sel_dir_but.clicked.connect(partial(self.open_dialog, is_file, line_edit))

        h_layout.addWidget(name_label, 2)
        h_layout.addWidget(line_edit, 8)
        h_layout.addWidget(sel_dir_but, 1)
        return h_layout, line_edit

    def open_dialog(self, is_file, widget):

        if is_file:
            file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Select file', '', '(*.mb *.ma)')
            widget.setText(file_name[0])
        else:
            file_name = QtWidgets.QFileDialog.getExistingDirectory(self)
            widget.setText(file_name)

    def create_spinboxes(self, text, max_value, min_value, value, validator=None, validator_type=None):
        name_label = QtWidgets.QLabel(text)
        spinbox = QtWidgets.QSpinBox(minimum=min_value, maximum=max_value, value=value)
        spinbox.setFixedWidth(50)

        if validator:
            spinbox.valueChanged.connect(partial(self.spin_box_validator, validator_type))

        self.secondGroupBoxLayout.addRow(name_label, spinbox)

        return spinbox


if __name__ == '__main__':
    # Create the Qt Application
    app = QtWidgets.QApplication(sys.argv)

    for i in range(2018, 2023):
        path = f"C:\\Program Files\\Autodesk\\Arnold\\Maya{i}"
        if os.path.isdir(path):
            app.setWindowIcon(QtGui.QIcon(path + "\\arnold.ico"))

    win = MainProjectWindow()
    win.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
