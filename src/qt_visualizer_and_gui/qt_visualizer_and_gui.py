import logging
import time
from typing import Dict

import cv2
import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea
from pyqtgraph.Qt import QtWidgets

logger = logging.getLogger(__name__)


class QTVisualizerAndGui:
    def __init__(self):
        # https://pyqtgraph.readthedocs.io/en/latest/config_options.html
        pg.setConfigOptions(imageAxisOrder='row-major')
        self.pyqtgraph_app = pg.mkQApp("FreeMoCap! :O ")

        self._dict_of_camera_image_item_widgets = {}
        self._dict_of_simple_timestamp_line_plots = {}
        self._dict_of_cam_timestamps = {}
        self._dict_of_timestamp_difference_line_plots = {}
        self._dict_of_cam_timestamp_differences = {}
        self._dict_of_timestamp_difference_histograms = {}
        self._number_of_cameras = None
        self._webcam_ids_list = []

        self._is_paused = False

    @property
    def pause_button_pressed(self):
        return self._is_paused

    def close(self):
        self._main_window_widget.close()

    def setup_and_launch(self, webcam_ids_list):
        logger.info('setting up QT Visualizer and GUI')
        self._number_of_cameras = len(webcam_ids_list)
        self._webcam_ids_list = webcam_ids_list
        self._setup_main_window()
        self._setup_control_panel()
        self._setup_camera_views_dock()
        self._setup_timestamp_plot()
        self._setup_time_difference_from_cam0_line_plot()
        self._setup_time_difference_from_cam0_histogram_plot()
        logger.info('launching QT Visualizer and GUI window')
        self._main_window_widget.show()

    def update_camera_view_image(self, webcam_id, image_to_display):
        if self.pause_button_pressed:
            return

        try:
            camera_image_item_widget = self._dict_of_camera_image_item_widgets[webcam_id]
        except Exception as e:
            logger.warning(f'Could not find ViewBoxWidget for camera {webcam_id}')
            raise e
        camera_image_item_widget.setImage(cv2.cvtColor(image_to_display, cv2.COLOR_BGR2RGB))

    def update_timestamp_plots(self, dict_of_timestamps):
        if self.pause_button_pressed:
            return

        try:
            camera_0_timestamp = dict_of_timestamps['0']
        except:
            logger.info('no timestamp for camera0')
            camera_0_timestamp = np.nan

        for webcam_id in self._webcam_ids_list:
            try:
                this_cameras_timestamp = dict_of_timestamps[webcam_id]
                time_diff_from_cam0 = this_cameras_timestamp - camera_0_timestamp

                self._dict_of_cam_timestamps[webcam_id] = np.append(self._dict_of_cam_timestamps[webcam_id],
                                                                    this_cameras_timestamp)
                self._dict_of_cam_timestamp_differences[webcam_id] = np.append(
                    self._dict_of_cam_timestamp_differences[webcam_id],
                    time_diff_from_cam0)

            except Exception as e:
                logger.warning(f'Could not find timestamp dictionary for camera {webcam_id}')
                raise e

        self._update_simple_timestamp_plot()
        self._update_timestamp_difference_plot()
        self._update_timestamp_difference_histogram()

    def _update_simple_timestamp_plot(self):
        for webcam_id, timestamps_array in self._dict_of_cam_timestamps.items():
            plot_item = self._dict_of_simple_timestamp_line_plots[webcam_id]
            plot_item.setData(timestamps_array)

    def _update_timestamp_difference_plot(self):
        camera_0_id = '0'

        for webcam_id in self._dict_of_cam_timestamps.keys():
            self._dict_of_timestamp_difference_line_plots[webcam_id].setData(
                self._dict_of_cam_timestamp_differences[webcam_id])

    def _update_timestamp_difference_histogram(self):
        for webcam_id in self._webcam_ids_list:
            counts, bin_edges = np.histogram(self._dict_of_cam_timestamp_differences[webcam_id],
                                             bins=np.linspace(-50, 50, 100))
            try:
                self._dict_of_timestamp_difference_histograms[webcam_id].setData(
                    x=bin_edges,
                    y=counts)
            except Exception as e:
                logger.warning(f'Could not find timestamp difference line plot widget for camera {webcam_id}')
                raise e

    def _setup_main_window(self, window_width: int = 1000, window_height: int = 1000):
        """
        This is the main main window for the GUI.
        Its structure is based loosely on the 'Dock Widgets' example from `python -m pyqtgraph.examples`
        """
        self._main_window_widget = QtWidgets.QMainWindow()
        self._main_window_widget.resize(window_width, window_height)

        self._main_dock_area = DockArea()
        self._main_window_widget.setCentralWidget(self._main_dock_area)
        self._main_window_widget.setWindowTitle('Main Window ;D')

    def _setup_control_panel(self):
        self._control_panel_dock = Dock('Control Panel', size=(1, 1))
        control_panel_layout_widget = pg.LayoutWidget()
        self._control_panel_dock.addWidget(control_panel_layout_widget)

        label = QtWidgets.QLabel("Blah Blah Blah put words here ")
        control_panel_layout_widget.addWidget(label, row=0, col=0)

        self._pause_button = QtWidgets.QPushButton('Pause')
        self._pause_button.setEnabled(True)
        self._pause_button.clicked.connect(self._pause)
        control_panel_layout_widget.addWidget(self._pause_button, row=1, col=0)

        self._play_button = QtWidgets.QPushButton('Resume')
        self._play_button.setEnabled(False)
        self._play_button.clicked.connect(self._play)
        control_panel_layout_widget.addWidget(self._play_button, row=2, col=0)

        self._main_dock_area.addDock(self._control_panel_dock, position='left')

    def _setup_camera_views_dock(self):
        self._camera_graphics_layout_window = pg.GraphicsLayoutWidget()
        self._camera_views_dock = Dock('Camera Views')
        self._camera_views_dock.addWidget(self._camera_graphics_layout_window)
        self._main_dock_area.addDock(self._camera_views_dock, 'right', self._control_panel_dock)

        for this_webcam_id in self._webcam_ids_list:
            self._dict_of_camera_image_item_widgets[this_webcam_id] = self._create_camera_view_widget()

    def _create_camera_view_widget(self):
        camera_view_box_widget = pg.ViewBox(invertY=True, lockAspect=True)
        camera_image_item = pg.ImageItem()
        camera_view_box_widget.addItem(camera_image_item)
        self._camera_graphics_layout_window.addItem(camera_view_box_widget)
        return camera_image_item

    def _setup_timestamp_plot(self):
        # create widget/dock for reprojection error subplot
        timestamp_plot_widget = pg.PlotWidget(title="Timestamp vs Frame#")
        timestamp_plot_widget.setLabel('left', "timestamp", units='seconds')
        timestamp_plot_widget.setLabel('bottom', "Frame#", units='Frame')
        timestamp_plot_widget.addLegend()

        for this_cam_num, this_webcam_id in enumerate(self._webcam_ids_list):
            this_timestamp_plot_line = timestamp_plot_widget.plot(np.empty(0),
                                                                  pen=(this_cam_num, self._number_of_cameras),
                                                                  name="camera " + this_webcam_id)

            self._dict_of_simple_timestamp_line_plots[this_webcam_id] = this_timestamp_plot_line
            self._dict_of_cam_timestamps[this_webcam_id] = np.ndarray(0)

        self._timestamp_plot_dock = Dock("Camera Timestamps")
        self._timestamp_plot_dock.addWidget(timestamp_plot_widget)
        self._main_dock_area.addDock(self._timestamp_plot_dock, 'bottom')

    def _setup_time_difference_from_cam0_line_plot(self):
        # create widget/dock for reprojection error subplot
        timestamp_difference_plot_widget = pg.PlotWidget(title="Timestamp difference from Camera0 on each frame")
        timestamp_difference_plot_widget.setLabel('left', "this_camera timestamp - cam0 timestamp", units='seconds')
        timestamp_difference_plot_widget.setLabel('bottom', "Frame#", units='Frame')
        timestamp_difference_plot_widget.addLegend()

        for this_cam_num, this_webcam_id in enumerate(self._webcam_ids_list):
            this_plot_line = timestamp_difference_plot_widget.plot(np.empty(0),
                                                                   pen=(this_cam_num, self._number_of_cameras),
                                                                   name="camera " + this_webcam_id)

            self._dict_of_timestamp_difference_line_plots[this_webcam_id] = this_plot_line
            self._dict_of_cam_timestamp_differences[this_webcam_id] = np.ndarray(0)

        self._timestamp_difference_plot_dock = Dock("Camera Timestamps")
        self._timestamp_difference_plot_dock.addWidget(timestamp_difference_plot_widget)
        self._main_dock_area.addDock(self._timestamp_difference_plot_dock, 'right', self._timestamp_plot_dock)

    def _setup_time_difference_from_cam0_histogram_plot(self):
        timestamp_difference_histogram_plot_widget = pg.PlotWidget(
            title="Timestamp difference from Camera0 on each frame")
        timestamp_difference_histogram_plot_widget.setLabel('left', "Proportion")
        timestamp_difference_histogram_plot_widget.setLabel('bottom', "milliseconds")
        timestamp_difference_histogram_plot_widget.addLegend()

        for this_cam_num, this_webcam_id in enumerate(self._webcam_ids_list):
            this_histogram_plot_item = timestamp_difference_histogram_plot_widget.plot(np.empty(0),
                                                                                       np.empty(0),
                                                                                       stepMode="center",
                                                                                       fillLevel=0,
                                                                                       fillOutline=True,
                                                                                       brush=pg.mkBrush(color=(
                                                                                           this_cam_num,
                                                                                           self._number_of_cameras),
                                                                                           alpha=.5),
                                                                                       name="camera " + this_webcam_id)

            self._dict_of_timestamp_difference_histograms[this_webcam_id] = this_histogram_plot_item

        timestamp_plot_dock = Dock("Camera Timestamp Difference histogram")
        timestamp_plot_dock.addWidget(timestamp_difference_histogram_plot_widget)
        self._main_dock_area.addDock(timestamp_plot_dock, 'right', self._timestamp_difference_plot_dock)

    def _pause(self):
        self._is_paused = True
        self._play_button.setEnabled(True)
        self._play_button.setText("GUI Paused - Main loop still active")
        self._pause_button.setEnabled(False)

    def _play(self):
        self._is_paused = False
        self._play_button.setEnabled(False)
        self._pause_button.setEnabled(True)
