from qgis.core import QgsTask
from PyQt5.QtCore import pyqtSignal

from .eoo_tool import calculate_eoo_aoo


class EOOAOOTask(QgsTask):

    progressChanged = pyqtSignal(float)
    logMessage = pyqtSignal(str)
    taskFinishedSignal = pyqtSignal(bool, bool, str, bool)

    def __init__(self, description, ec_list, raster_folder, output_path, use_clip):
        super().__init__(description, QgsTask.CanCancel)

        self.ec_list = ec_list
        self.raster_folder = raster_folder
        self.output_path = output_path
        self.use_clip = use_clip

        self.logs = []

    def run(self):

        try:
            self.logs = calculate_eoo_aoo(
                self.ec_list,
                self.raster_folder,
                self.output_path,
                use_clip=self.use_clip,
                progress_callback=self.progressChanged.emit,
                log_callback=self.logMessage.emit,
                cancel_check=self.isCanceled
            )
                        
            if self.isCanceled():
                return False

            return True

        except Exception as e:
            self.logs = [f"ERROR: {str(e)}"]
            return False
            
    def finished(self, result):
        """
        Called automatically by QGIS when the task finishes.
        """
        if self.isCanceled():
            self.logMessage.emit("\n⚠ Processing cancelled.\n")
            self.taskFinishedSignal.emit(False, True, self.output_path, self.add_to_map)
            return

        if result:
            self.logMessage.emit("\n✅ Processing finished.\n")
            self.taskFinishedSignal.emit(True, False, self.output_path, self.add_to_map)
        else:
            self.logMessage.emit("\n❌ Processing failed.\n")
            self.taskFinishedSignal.emit(False, False, self.output_path, self.add_to_map)
