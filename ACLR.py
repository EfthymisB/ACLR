from PySide2 import QtWidgets, QtCore, QtGui
from functools import partial
import multiprocessing
import datetime
import subprocess
import signal
import sys
import os
import re


def sumbit_render(scene_file, output, start_f, end_f, step_f, threads, process, override_cam, cam_sel):

    # Check if selected scene file is empty.
    if not scene_file.text():
        scene_file.setFocus()
        return
    # Check if selected scene file exists.
    elif not os.path.isfile(scene_file.text().replace('\\', '/')):
        scene_file.setSelection(0, len(scene_file.text()))
        scene_file.setFocus()
        return
    # Check if output dir is empty.
    elif not output.text():
        output.setFocus()
        return
    # Check if output dir exists.
    elif not os.path.isdir(output.text()):
        output.setSelection(0, len(output.text()))
        output.setFocus()
        return

    # Submit render
    if override_cam:
        process.start('cmd.exe /C Render -r arnold -s {start} -e {end} -b {step} -ai:threads {threads} -rd {output} '
                      '-cam {cam_sel} -postFrame $s=`currentTime-q`;print("""Frame_"""+$s+"""_completed\\n"""); '
                      '-postRender print("""Render_finished\\n"""); {scene_file.text()}'.format(start=start_f, end=end_f, step=step_f, threads=threads, output=output.text(), cam_sel=cam_sel.text(), scene_file=scene_file.text()))
    else:
        process.start('cmd.exe /C Render -r arnold -s {start} -e {end} -b {step} -ai:threads {threads} -rd {output} '
                      '-postFrame $s=`currentTime-q`;print("""Frame_"""+$s+"""_completed\\n"""); '
                      '-postRender print("""Render_finished\\n"""); {scene_file}'.format(start=start_f, end=end_f, step=step_f, threads=threads, output=output.text(), scene_file=scene_file.text()))
    return True


class MainProjectWindow(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(MainProjectWindow, self).__init__(parent)

        self.mainLayout = None
        self.project_grBox = None
        self.project_grBox_layout = None
        self.frame_grBox = None
        self.frame_grBox_layout = None
        self.scene_file = None
        self.destination_path = None
        self.startFrame = None
        self.endFrame = None
        self.stepFrame = None
        self.nameWidget = None
        self.folderWidget = None
        self.frames_and_render_layout = None
        self.thirdGroupBoxLayout_2 = None
        self.render_device_grBox = None
        self.render_device_grBox_layout = None
        self.third_layout_1 = None
        self.third_layout_2 = None
        self.cameraGroupBox = None
        self.cameraGroupBoxLayout = None

        self.setup_ui()

        self._process = QtCore.QProcess(self)
        self._process.started.connect(self.handle_started)
        self._process.finished.connect(self.handle_finished)
        self._process.error.connect(self.handle_error)

        self._time = QtCore.QTime()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.handle_timeout)

    # If Rendering, ignore close.
    def closeEvent(self, event):
        if self._timer.isActive():
            event.ignore()
        else:
            QtWidgets.QWidget.closeEvent(self, event)

    def handle_timeout(self):
        #self.button_stop.setText('Elapsed: %.*f' % (2, self._time.elapsed() / 1000.0))
        data = bytearray(self._process.readAllStandardOutput()).decode('utf-8').rstrip()
        if 'Frame_' in data:
            try:
                self.progress_bar_value += (100 / ((self.endFrame.value() - self.startFrame.value()) / self.stepFrame.value()))
            except ZeroDivisionError:
                self.progress_bar_value = 1
            self.progress_bar.setValue(self.progress_bar_value)
            new_frame = int(self.progress_bar.format().split('/')[0]) + 1
        else:
            new_frame = self.progress_bar.format().split('/')[0]
        time_elapsed = datetime.timedelta(seconds=round(self._time.elapsed()/1000.0))
        self.progress_bar.setFormat('{new_frame}/{total_frames_num} frames'
                                    '                %p%                {time_elapsed}'.format(new_frame=int(new_frame), total_frames_num=self.total_frames_num, time_elapsed=time_elapsed))

    def handle_started(self):
        self.button_create.setDisabled(True)
        self.button_stop.setDisabled(False)
        self._time.start()
        self._timer.start(100)

    def handle_finished(self):
        self._timer.stop()
        self.button_create.setDisabled(False)
        self.button_stop.setDisabled(True)
        self.progress_bar.setValue(100)

    def handle_error(self, error):
        if error == QtCore.QProcess.CrashExit:
            print('Process killed')
        else:
            print(self._process.errorString())

    def handle_button_stop(self):
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
        self.project_grBox = QtWidgets.QGroupBox("Project")
        self.project_grBox_layout = QtWidgets.QVBoxLayout(self.project_grBox)
        self.mainLayout.addWidget(self.project_grBox)

        self.frames_and_render_layout = QtWidgets.QHBoxLayout(self)
        self.mainLayout.addLayout(self.frames_and_render_layout)

        self.frame_grBox = QtWidgets.QGroupBox("Frames")
        self.frame_grBox_layout = QtWidgets.QFormLayout(self.frame_grBox)
        self.frames_and_render_layout.addWidget(self.frame_grBox, 1)
        self.cameraGroupBox = QtWidgets.QGroupBox("Camera", alignment=QtCore.Qt.AlignCenter)
        self.cameraGroupBoxLayout = QtWidgets.QFormLayout(self.cameraGroupBox)
        self.frames_and_render_layout.addWidget(self.cameraGroupBox, 1)
        self.cameraListWidget = QtWidgets.QListWidget()
        self.cameraListWidget.setMaximumWidth(80)
        self.cameraListWidget.setDisabled(True)
        self.camera_override = QtWidgets.QCheckBox(parent=self)
        self.camera_override.move(135, 97)
        self.camera_override.clicked.connect(self.camera_override_switch)
        self.cameraGroupBoxLayout.addWidget(self.cameraListWidget)

        self.render_device_grBox = QtWidgets.QGroupBox("Render device (CPU)")
        self.render_device_grBox_layout = QtWidgets.QVBoxLayout(self.render_device_grBox)

        self.frames_and_render_layout.addWidget(self.render_device_grBox, 7)

    def update_cameras(self, event):

        self.cameraListWidget.clear()

        if event.endswith('.ma'):
            try:
                file = open(event, 'r')
                file_lines = file.readlines()
                results = []
                for line in file_lines:
                    if line.startswith('createNode camera'):
                        results.append(re.search('"(.*?)"', line).group(1)[:-5])
                for result in sorted(set(results)):
                    self.cameraListWidget.addItem(result)
                self.cameraListWidget.setCurrentRow(0)
            except FileNotFoundError:
                pass

        elif event.endswith('.mb'):
            try:
                import maya.standalone
                maya.standalone.initialize(name='python')
                import maya.cmds as cmds
                cmds.file(r"C:\Users\Efthymis\Desktop\Test\TEST.mb", f=True, o=True)
                cameras = cmds.listCameras()
            
                for cam in sorted(set(cameras)):
                    self.cameraListWidget.addItem(cam)
                self.cameraListWidget.setCurrentRow(0)
            except:
                pass

    def camera_override_switch(self):
        self.cameraListWidget.setEnabled(self.camera_override.isChecked())

    def total_frames(self):
        frames = (self.endFrame.value() - self.startFrame.value()) + 1
        total_frames = int(frames / self.stepFrame.value())
        if total_frames == 0:
            total_frames += 1
        self.total_frames_num = total_frames
        self.progress_bar.setFormat('0/{total_frames} frames                    %p%'.format(total_frames=total_frames))

    def prepare_render(self):
        self.progress_bar.setValue(0)
        self.progress_bar_value = 0

        self.total_frames()

        if sumbit_render(self.scene_file, self.destination_path, self.startFrame.value(), self.endFrame.value(),
                         self.stepFrame.value(), self.thread_slider.value(), self._process,
                         self.camera_override.isChecked(), self.cameraListWidget.currentItem()):
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
        self.total_frames_num = 1
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
        self.button_stop.clicked.connect(partial(self.handle_button_stop))
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
            # Change buttons color to Green if Render.exe env variable exists.
            subprocess.check_call(['where', 'Render'])
            self.check_env_but.setStyleSheet("border-radius : 10;"
                                 "background-color: qradialgradient(spread:pad, cx:0.5, cy:0.5, radius:0.5, fx:0.5, "
                                 "fy:0.5, stop:0 rgba(0, 200, 0, 255), stop:0.642045 rgba(34, 220, 34, 255), "
                                 "stop:0.977273 rgba(0, 220, 0, 0));")
            self.check_env_label.setText('Render.exe Path found!')
            self.button_create.setDisabled(False)
        except subprocess.CalledProcessError:
            # Change buttons color to Red if Render.exe env variable doesn't exist.
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

        self.scene_file.textChanged.connect(self.update_cameras)

        self.project_grBox_layout.addLayout(scene_file_layout)
        self.project_grBox_layout.addLayout(destination_path_layout)
        self.project_grBox_layout.addStretch()

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
        self.render_device_grBox_layout.addWidget(self.thread_label, 1, QtCore.Qt.AlignCenter)
        self.render_device_grBox_layout.addWidget(self.thread_slider)

        self.slider_labels_layout = QtWidgets.QHBoxLayout()
        self.render_device_grBox_layout.addLayout(self.slider_labels_layout)

        self.slider_min = QtWidgets.QLabel('1')
        self.slider_value = QtWidgets.QLabel('{cpu_count}'.format(cpu_count=multiprocessing.cpu_count()))
        my_font = QtGui.QFont()
        my_font.setBold(True)
        self.slider_value.setFont(my_font)
        self.slider_max = QtWidgets.QLabel('{cpu_count}'.format(cpu_count=multiprocessing.cpu_count()))

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

        self.frame_grBox_layout.addRow(name_label, spinbox)

        return spinbox


if __name__ == '__main__':
    # Create the Qt Application
    app = QtWidgets.QApplication(sys.argv)
    for i in range(2018, 2023):
        path = "C:\\Program Files\\Autodesk\\Arnold\\Maya{i}".format(i=i)
        if os.path.isdir(path):
            app.setWindowIcon(QtGui.QIcon(path + "\\arnold.ico"))

    win = MainProjectWindow()
    win.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
