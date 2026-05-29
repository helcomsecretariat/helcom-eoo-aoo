import csv
from PyQt5.QtWidgets import QDialog, QFileDialog, QCheckBox, QSpacerItem, QSizePolicy, QMessageBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from pathlib import Path
import os
from PyQt5 import uic
from qgis.core import QgsApplication, QgsVectorLayer, QgsProject
from osgeo import gdal, osr
from datetime import datetime
from .core.eoo_tool import calculate_eoo_aoo
from .core.eoo_aoo_task import EOOAOOTask
import webbrowser

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), "main_dialog_base.ui")
)

class AOOEOODialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
                            
        self._init_step_visibility()
        
        # Storage for checkboxes
        self.ec_checkboxes = []
        
        self.selected_ecs = []
        
        self.available_ecs = []
        
        self.ec_folder = None
        
        # Initial state: everything disabled except CSV loading & EC/P selection
        self.btnConfirmSelection.setEnabled(False)
        self.btnValidate.setEnabled(False)
        self.btnRunTools.setEnabled(False)

        # Connect browse button
        self.btnBrowseCsv.clicked.connect(self.select_csv_file)

        # Connect search fields
        self.searchECLineEdit.textChanged.connect(self.filter_ec_list)
                
        # Connect Select/Deselect All buttons
        self.btnSelectAllECs.clicked.connect(self.select_all_ec)
        self.btnDeselectAllECs.clicked.connect(self.deselect_all_ec)
        
        # Stretch left (EC/P) and right sides
        self.mainHorizontalLayout.setStretch(0, 1)
        self.mainHorizontalLayout.setStretch(1, 1)
        
        self.btnConfirmSelection.clicked.connect(self.confirm_selection)
               
        self.btnBrowseECFolder.clicked.connect(self.select_ec_folder)
        
        self.btnValidate.clicked.connect(self.run_full_validation)
        
        #self.btnRunTools.clicked.connect(self.run_selected_tools)
        self.btnRunTools.clicked.connect(self.run_tools)
        
        self.btnReturnToSelection.clicked.connect(self.on_return_to_selection_clicked)
        self.btnReturnToFolders.clicked.connect(self.on_return_to_folders_clicked)
        self.btnCancelProcessing.clicked.connect(self.cancel_task)
        self.btnStartOver.clicked.connect(self.on_return_to_selection_clicked)
        
        # Output folder selection
        self.btnBrowseOutputFolder.clicked.connect(self.select_output_folder)
        
        self.ecFolderLineEdit.textChanged.connect(self._update_validate_button_state)        
        
        self.outputFolderLineEdit.textChanged.connect(self._update_run_tools_state)
                   
        self._set_button_style(self.btnReturnToSelection)
        self._set_button_style(self.btnReturnToFolders)
        
        self.btnHelp.setIcon(QIcon.fromTheme("help-about"))
        self.btnHelp.clicked.connect(self.open_user_guide)
        
    
    def add_output_to_map(self, shp_path):
        layer_name = os.path.basename(shp_path)
        layer = QgsVectorLayer(shp_path, layer_name, "ogr")
        if not layer.isValid():
            self.selectionOutput.append(f"⚠ Failed to load layer: {shp_path}")
            return
        QgsProject.instance().addMapLayer(layer)
        self.selectionOutput.append(f"Layer added to map: {layer_name}")

            
    def _set_button_style(self, button):
        button.setStyleSheet("""
            text-align: left; 
            padding: 0px 5px;
            min-height: 28px;
        """)
        button.setIcon(QIcon(":/images/themes/default/mActionArrowLeft.svg"))
        button.setIconSize(QSize(16, 16))
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button.adjustSize()
        
    def _init_step_visibility(self):
        self.big_step1.show()
        self.big_step2.hide()
        self.big_step2_Layout.setAlignment(Qt.AlignTop)
        self.big_step3.hide()
        self.big_step3_Layout.setAlignment(Qt.AlignTop)
        self.btnStartOver.hide()
        self.big_step4.hide()
        self.big_step4_Layout.setAlignment(Qt.AlignTop)
        
    
    def on_return_to_selection_clicked(self):
        self.big_step1.show()
        self.big_step2.hide()
        self.big_step3.hide()
        self.big_step4.hide()
        self.selectionOutput.clear()
        self.show_status_message("")
        self.btnStartOver.hide()
        
    def on_return_to_folders_clicked(self):
        self.big_step1.hide()
        self.big_step2.show()
        self.big_step3.hide()
        self.big_step4.hide()
        self.selectionOutput.clear()
        self.show_status_message("")
    
    def _update_confirm_selection_state(self):
        has_ec = any(cb.isChecked() for cb in self.ec_checkboxes)
        self.btnConfirmSelection.setEnabled(has_ec)
            
    def _update_validate_button_state(self):
        ec_ok = bool(self.ecFolderLineEdit.text().strip())
        self.btnValidate.setEnabled(ec_ok)
    
    def _update_run_tools_state(self):
        p = self.outputFolderLineEdit.text().strip()
        folder_path = Path(p)
                        
        self.btnRunTools.setEnabled(folder_path.is_dir() and bool(p))
        
    def select_csv_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select sensitivity scores matrix CSV file",
            "",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        self.csvPathLineEdit.setText(path)
        self.load_ec_p_lists(path)
        
        
    def load_ec_p_lists(self, csv_path):
        """Reads EC names from CSV and populates the UI list."""

        self.clear_lists()

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # First column (excluding header) contains EC names
        ec_names = [row[0].strip() for row in rows[1:]]

        # Populate EC list
        for ec in ec_names:
            cb = QCheckBox(ec)
            self.ecCheckboxLayout.addWidget(cb)
            self.ec_checkboxes.append(cb)
            cb.toggled.connect(self._update_confirm_selection_state)
            
        # Bind checkbox state changes for live updates
        for cb in self.ec_checkboxes:
            cb.stateChanged.connect(self.update_selection_display)


    def clear_lists(self):
        """Remove all existing checkboxes before loading new CSV."""
        for cb in self.ec_checkboxes:
            self.ecCheckboxLayout.removeWidget(cb)
            cb.deleteLater()
        self.ec_checkboxes.clear()

    def filter_ec_list(self, text):
        text = text.lower()

        # Remove ALL spacers at the bottom
        for i in reversed(range(self.ecCheckboxLayout.count())):
            item = self.ecCheckboxLayout.itemAt(i)
            if isinstance(item, QSpacerItem):
                self.ecCheckboxLayout.removeItem(item)

        # Filter checkboxes
        for cb in self.ec_checkboxes:
            cb.setVisible(text in cb.text().lower())

        # Add a fresh bottom spacer
        self.ecCheckboxLayout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )


    def filter_p_list(self, text):
        text = text.lower()

        for i in reversed(range(self.pCheckboxLayout.count())):
            item = self.pCheckboxLayout.itemAt(i)
            if isinstance(item, QSpacerItem):
                self.pCheckboxLayout.removeItem(item)

        for cb in self.p_checkboxes:
            cb.setVisible(text in cb.text().lower())

        self.pCheckboxLayout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )
        
    def select_all_ec(self):
        for cb in self.ec_checkboxes:
            if cb.isVisible():  # only select items matching current search
                cb.setChecked(True)

    def deselect_all_ec(self):
        for cb in self.ec_checkboxes:
            if cb.isVisible():
                cb.setChecked(False)

    def confirm_selection(self):
        selected_ecs = [cb.text() for cb in self.ec_checkboxes if cb.isChecked()]
        
        # Validation
        if not selected_ecs:
            self.show_status_message("⚠ Select at least one Ecosystem component.", "error")
            return
        
        # Store selections for later
        self.selected_ecs = [label.strip() for label in selected_ecs]

        # Success message at the NEW top location
        self.show_status_message("✅ Ecosystem component selection confirmed.", "success")

        # Continue to show details in the text output box
        self.selectionOutput.setPlainText(
            "Selected Ecosystem components:\n" +
            ", ".join(selected_ecs)
        )
                
        # Hide selection steps
        self.big_step1.hide()
        self.big_step2.show()
        self.big_step3.hide()
        self.big_step4.hide()
        
    def update_selection_display(self):
        # Count ECs
        selected_ecs = [cb.text() for cb in self.ec_checkboxes if cb.isChecked()]
        selected_ec_count = len(selected_ecs)
        total_ec_count = len(self.ec_checkboxes)

        # Build display text
        output = []
        output.append(f"Selected Ecosystem components: {selected_ec_count} / {total_ec_count}")
        if selected_ecs:
            output.append(", ".join(selected_ecs))

        output.append("")  # spacer line

        
        # Update UI text box
        self.selectionOutput.setPlainText("\n".join(output))
                
    def show_status_message(self, message: str, message_type: str = "info"):
        """
        Shows a colored status message directly beneath the Confirm button.
        message_type: "info", "success", or "error"
        """

        if message_type == "success":
            color = "#0a7f00"  # green
        elif message_type == "error":
            color = "#b30000"  # red
        else:
            color = "#333333"  # default dark

        self.statusMessageLabel.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.statusMessageLabel.setText(message)
        
    def select_ec_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select EC Raster Folder")
        if folder:
            self.ecFolderLineEdit.setText(folder)
            self.ec_folder = folder

    def run_full_validation(self):
        """
        Combined validation pipeline:
          1. Validate EC folder contains rasters for selected labels.
          2. Ask user if missing rasters should be ignored.
          3. Run detailed GDAL sanity check on all available rasters.
          4. Print a detailed validation log in the summary panel.
        """

        log = []
        ec_folder = self.ecFolderLineEdit.text().strip()
        
        # Validate ECs
        available_ecs, missing_ecs = self.validate_single_group(
            ec_folder, self.selected_ecs, "EC"
        )
        
                
        if len(available_ecs) == 0:
            box_message = "There no selected Ecosystem component rasters in selected folder."
                        
            self.show_status_message("❌ No rasters in the folder.", "error")
            QMessageBox.critical(
                self,
                "No rasters error",
                f"{box_message}\n\nCheck if:\n  • selected folder contain raster files\n  • file names are same as names in the CSV file.",
                QMessageBox.Ok
            )
            
            return
        
        # Save available rasters
        self.available_ecs = available_ecs
                
        # Build file check log
        if missing_ecs:
            log.append("⚠ Some raster files are missing:\n")

            if missing_ecs:
                log.append(f"Missing {len(missing_ecs)} out of {len(self.selected_ecs)} selected Ecosystem component rasters:")
                log.extend(f"  • {m}" for m in missing_ecs)
                log.append("")

            
            # Show log so far
            self.selectionOutput.setPlainText("\n".join(log))
            self.show_status_message("⚠ Missing rasters detected.", "error")

            # Ask user
            proceed = QMessageBox.question(
                self,
                "Missing raster files",
                "\n".join(log) + "\n\nProceed with available rasters?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if proceed == QMessageBox.No:
                self.show_status_message("❌ Validation cancelled.", "error")
                return

            log.append(f"\n⚠ Proceeding with {len(self.available_ecs)} Ecosystem component available rasters.\n")
            
        else:
            log.append("✅ All raster files found.\n")


        # ===============================================================
        # Step 2 — Full raster metadata sanity check
        # ===============================================================
        log.append("\n=== Raster validation ===\n")

        sanity_report = self.run_raster_sanity_check(ec_folder)
        log.append(sanity_report)

        # Critical error detection
        if "❌" in sanity_report:
            self.selectionOutput.setPlainText("\n".join(log))
            self.show_status_message(
                "❌ Critical raster mismatches — cannot proceed.", "error"
            )
            return

        # If passed
        self.selectionOutput.setPlainText("\n".join(log))
        self.show_status_message("✅ Validation complete!", "success")
        
        self.big_step1.hide()
        self.big_step2.hide()
        self.big_step3.show()
        self.big_step4.hide()
        self._update_run_tools_state()
                
    def validate_single_group(self, folder_path: str, selected_items: list, group_label: str):
        expected_files = [name.strip() + ".tif" for name in selected_items]

        if not folder_path or not os.path.isdir(folder_path):
            return [], expected_files  # everything missing

        files_in_folder = {
            f.lower() for f in os.listdir(folder_path)
            if f.lower().endswith(".tif")
        }

        available = []
        missing = []

        for fn in expected_files:
            if fn.lower() in files_in_folder:
                available.append(fn[:-4])
            else:
                missing.append(fn)

        return available, missing
        
    def run_raster_sanity_check(self, ec_folder: str):
        
        log = []
        errors = 0
        warnings = 0

        # Collect all raster paths
        all_paths = []
        for name in self.available_ecs:
            all_paths.append(os.path.join(ec_folder, name + ".tif"))
        
        if not all_paths:
            return "⚠ No rasters available for validation.\n"

        ref = gdal.Open(all_paths[0])
        if ref is None:
            return "❌ Cannot open reference raster.\n"

        ref_gt = ref.GetGeoTransform()
        ref_proj = ref.GetProjection()
        ref_xsize = ref.RasterXSize
        ref_ysize = ref.RasterYSize
        ref_dtype = ref.GetRasterBand(1).DataType
        ref_block = ref.GetRasterBand(1).GetBlockSize()

        ref_res_x = ref_gt[1]
        ref_res_y = abs(ref_gt[5])

        ref_xmin = ref_gt[0]
        ref_xmax = ref_gt[0] + ref_xsize * ref_gt[1]
        ref_ymax = ref_gt[3]
        ref_ymin = ref_gt[3] + ref_ysize * ref_gt[5]

        log.append(f"First raster: {os.path.basename(all_paths[0])} is used as a reference raster.\n")
        log.append(f"--- Reference raster parameters:")
        info_text = f"CRS: {self.get_raster_crs_name(ref)}\nResolution: {self.get_raster_resolution(ref)}\nDimensions: {self.get_raster_dimensions(ref)}\nExtent: {self.get_raster_extent(ref)}\nBlock size: {self.get_raster_block_size(ref)}\nData type: {self.get_raster_data_type(ref)}\n"
        log.append(info_text)

        for path in all_paths:
            ds = gdal.Open(path)
            name = os.path.basename(path)

            if ds is None:
                errors += 1
                log.append(f"❌ Cannot open: {name}\n")
                continue

            gt = ds.GetGeoTransform()
            proj = ds.GetProjection()
            xsize = ds.RasterXSize
            ysize = ds.RasterYSize
            dtype = ds.GetRasterBand(1).DataType
            block = ds.GetRasterBand(1).GetBlockSize()

            res_x = gt[1]
            res_y = abs(gt[5])

            xmin = gt[0]
            xmax = gt[0] + xsize * gt[1]
            ymax = gt[3]
            ymin = gt[3] + ysize * gt[5]

            if proj != ref_proj:
                errors += 1
                log.append(f"❌ CRS mismatch for {name}: {self.get_raster_crs_name(ds)}\n")

            if (res_x != ref_res_x) or (res_y != ref_res_y):
                errors += 1
                log.append(f"❌ Resolution mismatch for {name}: {self.get_raster_resolution(ds)}\n")

            if xsize != ref_xsize or ysize != ref_ysize:
                errors += 1
                log.append(f"❌ Dimension mismatch for {name}: {self.get_raster_dimensions(ds)}\n")

            if (abs(xmin - ref_xmin) > 0.001 or
                abs(xmax - ref_xmax) > 0.001 or
                abs(ymin - ref_ymin) > 0.001 or
                abs(ymax - ref_ymax) > 0.001):
                errors += 1
                log.append(f"❌ Extent mismatch for {name}: {self.get_raster_extent(ds)}\n")

            if gt[2] != 0 or gt[4] != 0:
                warnings += 1
                log.append(f"⚠ Rotated raster: {name}\n")

            if block != ref_block:
                warnings += 1
                log.append(f"⚠ Block size mismatch for {name}: {self.get_raster_block_size(ds)}\n")

            if dtype != ref_dtype:
                warnings += 1
                log.append(f"⚠ Data type mismatch for {name}: {self.get_raster_data_type(ds)}\n")

        # Summary
        log.append("\n=== Raster validation summary ===\n")
        if errors == 0:
            log.append("✅ No critical errors.\n")
        else:
            log.append(f"❌ {errors} critical errors.\n")

        if warnings == 0:
            log.append("✅ No warnings.\n")
        else:
            log.append(f"⚠ {warnings} warnings.\n")

        if errors == 0:
            log.append("✅ Validation passed — rasters compatible.\n")
        else:
            log.append("❌ Validation failed — rasters incompatible.\n")

        return "\n".join(log)
        
    def get_raster_crs_name(self, ds):
        """
        Return CRS name in a user‑friendly form (e.g. 'EPSG:3035').
        """
        proj_wkt = ds.GetProjection()
        if not proj_wkt:
            return "Unknown"

        srs = osr.SpatialReference()
        srs.ImportFromWkt(proj_wkt)

        auth_name = srs.GetAuthorityName(None)
        auth_code = srs.GetAuthorityCode(None)

        if auth_name and auth_code:
            return f"{auth_name}:{auth_code}"

        return srs.GetName() or "Custom CRS"
        
    def get_raster_resolution(self, ds):
        """
        Return raster resolution as (pixel_width, pixel_height).
        """
        gt = ds.GetGeoTransform()
        pixel_width = abs(gt[1])
        pixel_height = abs(gt[5])
        
        return f"{pixel_width:.6g} × {pixel_height:.6g}"
        
    def get_raster_dimensions(self, ds):
        """
        Return raster dimensions as (cols, rows).
        """
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        
        return f"{cols} × {rows} (cols × rows)"
        
    def get_raster_extent(self, ds):
        """
        Return raster extent as (xmin, ymin, xmax, ymax).
        """
        gt = ds.GetGeoTransform()
        cols = ds.RasterXSize
        rows = ds.RasterYSize

        xmin = gt[0]
        ymax = gt[3]
        xmax = xmin + cols * gt[1]
        ymin = ymax + rows * gt[5]
        
        return f"xmin={xmin:.6f}, ymin={ymin:.6f}, xmax={xmax:.6f}, ymax={ymax:.6f}"
        
    def get_raster_block_size(self, ds):
        """
        Return raster block size as (block_x, block_y).
        """
        band = ds.GetRasterBand(1)
        block_x, block_y = band.GetBlockSize()
        
        return f"{block_x} × {block_y}"

    def get_raster_data_type(self, ds):
        """
        Return raster data type name (e.g. 'Float32').
        """
        band = ds.GetRasterBand(1)
        
        return gdal.GetDataTypeName(band.DataType)
        
            
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.outputFolderLineEdit.setText(folder)
            
    def run_tools(self):
        base_folder = self.outputFolderLineEdit.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_folder = os.path.join(base_folder, f"EOO_AOO_{timestamp}")
        os.makedirs(results_folder, exist_ok=True)
        shp_path = os.path.join(results_folder, f"EOO_AOO_{timestamp}.shp")

        self.selectionOutput.clear()
        self.processingProgressBar.setValue(0)

        self.update_runtime_estimate()
        
        self.big_step1.hide()
        self.big_step2.hide()
        self.big_step3.hide()
        self.big_step4.show()

        self.task = EOOAOOTask(
            "EOO/AOO processing",
            self.selected_ecs,
            self.ecFolderLineEdit.text().strip(),
            shp_path,
            self.chkClipCoast.isChecked()
        )
        
        self.task.add_to_map = self.chkAddToMap.isChecked()
        self.task.output_path = shp_path

        self.task.progressChanged.connect(self.on_progress)
        self.task.logMessage.connect(self.on_log)
        self.task.taskFinishedSignal.connect(self.on_task_finished)
        self.btnCancelProcessing.show()
        self.btnStartOver.hide()
        self.show_status_message("⏳ Running EOO and AOO tools...", "info")
        self.selectionOutput.append("Processing started.")

        QgsApplication.taskManager().addTask(self.task)
        
    def on_progress(self, value):
        self.processingProgressBar.setValue(int(value))


    def on_log(self, msg):
        self.selectionOutput.append(msg)        
    
    def cancel_task(self):
        if self.task and self.task.isActive():
            self.task.cancel()
            self.selectionOutput.append("Processing cancelled.")
            self.btnStartOver.show()
            self.btnCancelProcessing.hide()
            
    def on_task_finished(self, success, cancelled, output_path, add_to_map):
        
        self.btnCancelProcessing.hide()
        self.btnStartOver.show()

        # Optional: disable run button
        self.btnRunTools.setEnabled(False)

        if cancelled:
            return

        if success:
            self.show_status_message("✅ Processing finished successfully!", "success")
            if add_to_map and os.path.exists(output_path):
                self.add_output_to_map(output_path)

        else:
            self.selectionOutput.append("❌ Something went wrong.")
            self.show_status_message("❌ Tool processing failed.", "error")
            
    def update_runtime_estimate(self):

        ec_count = len(self.selected_ecs)

        if ec_count == 0:
            self.estimatedRuntimeLabel.hide()
            return

        base = ec_count

        # ---- Adjust for clipping
        factor = 2.5 if self.chkClipCoast.isChecked() else 1.0

        workload = base * factor

        if workload < 5:
            txt = "Estimated runtime: seconds"
        elif workload < 20:
            txt = "Estimated runtime: up to a minute"
        elif workload < 100:
            txt = "Estimated runtime: few minutes"
        else:
            txt = "Estimated runtime: several minutes"

        self.estimatedRuntimeLabel.setText(txt)
        self.estimatedRuntimeLabel.show()
    
    def open_user_guide(self):
        """
        Open online user guide in browser.
        """

        url = "https://github.com/helcomsecretariat/helcom-eoo-aoo"

        webbrowser.open(url)


