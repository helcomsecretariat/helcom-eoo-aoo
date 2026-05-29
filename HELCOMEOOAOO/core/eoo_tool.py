import os
import csv

from qgis.core import (
    QgsRasterLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsVectorFileWriter, QgsFields, QgsField,
    QgsProject, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsWkbTypes, QgsVectorLayer
)
from PyQt5.QtCore import QVariant

from .config import COASTLINE_PATH


def calculate_eoo_aoo(
    ec_list,
    raster_folder,
    shp_path,
    use_clip=False,
    progress_callback=None,
    log_callback=None,
    cancel_check=None
):

    # ---------------------------
    # Create output layer ONCE
    # ---------------------------
    fields = QgsFields()
    fields.append(QgsField("EC_NAME", QVariant.String))
    fields.append(QgsField("EOO_KM2", QVariant.Double))
    fields.append(QgsField("AOO_CELLS", QVariant.Int))
    
    base_path, _ = os.path.splitext(shp_path)
    csv_path = base_path + ".csv"
    csv_rows = []

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    writer = QgsVectorFileWriter.create(
        shp_path,
        fields,
        QgsWkbTypes.MultiPolygon,
        QgsCoordinateReferenceSystem("EPSG:3035"),
        QgsProject.instance().transformContext(),
        options
    )

    results_log = []

    # ---------------------------
    # Load coastline ONCE
    # ---------------------------
    coast_geom = None

    if use_clip:
        coast_layer = QgsVectorLayer(COASTLINE_PATH, "coastline", "ogr")

        if not coast_layer.isValid():
            msg = "ERROR: Coastline failed to load."
            results_log.append(msg)
            if log_callback:
                log_callback(msg)
            return results_log

        for feat in coast_layer.getFeatures():
            coast_geom = feat.geometry()
            break

    # ---------------------------
    # Process ECs
    # ---------------------------
    total = len(ec_list)

    for i, ec in enumerate(ec_list):
        
        
        if cancel_check and cancel_check():
            msg = "Processing cancelled by user."
            if log_callback:
                log_callback(msg)
            return results_log


        raster_path = os.path.join(raster_folder, f"{ec}.tif")

        layer = QgsRasterLayer(raster_path, ec)
        if not layer.isValid():
            msg = f"ERROR: Invalid raster {ec}"
            results_log.append(msg)
            if log_callback:
                log_callback(msg)
            continue

        provider = layer.dataProvider()
        extent = layer.extent()
        cols = layer.width()
        rows = layer.height()

        x_res = extent.width() / cols
        y_res = extent.height() / rows

        points = []
        aoo_count = 0

        block = provider.block(1, extent, cols, rows)

        for row in range(rows):
            
            if cancel_check and cancel_check():
                return results_log

            for col in range(cols):

                val = block.value(row, col)

                if val == 1:
                    aoo_count += 1

                    x = extent.xMinimum() + (col + 0.5) * x_res
                    y = extent.yMaximum() - (row + 0.5) * y_res

                    points.append(QgsPointXY(x, y))

        # ---- Skip empty
        if aoo_count == 0:
            msg = f"{ec}: no presence cells"
            results_log.append(msg)
            if log_callback:
                log_callback(msg)
            continue

        if len(points) < 3:
            msg = f"{ec}: insufficient points for EOO"
            results_log.append(msg)
            if log_callback:
                log_callback(msg)
            continue

        geom = QgsGeometry.fromMultiPointXY(points).convexHull()

        # ---------------------------
        # CLIP TO COASTLINE
        # ---------------------------
        if use_clip and coast_geom:

            if not geom.intersects(coast_geom):
                msg = f"{ec}: outside coastline — skipped"
                results_log.append(msg)
                if log_callback:
                    log_callback(msg)
                continue

            geom = geom.intersection(coast_geom)

            if geom.isEmpty():
                msg = f"{ec}: empty after clipping"
                results_log.append(msg)
                if log_callback:
                    log_callback(msg)
                continue

        # ---------------------------
        # Transform to projected CRS
        # ---------------------------
        src_crs = layer.crs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:3035")

        if src_crs != dest_crs:
            transform = QgsCoordinateTransform(
                src_crs, dest_crs, QgsProject.instance()
            )
            geom.transform(transform)

        # ---------------------------
        # Compute area
        # ---------------------------
        area_km2 = geom.area() / 1_000_000

        feat = QgsFeature()
        feat.setGeometry(geom)
        feat.setAttributes([ec, round(area_km2, 4), aoo_count])

        writer.addFeature(feat)
        
        
        csv_rows.append({
            "EC_NAME": ec,
            "EOO_KM2": round(area_km2, 4),
            "AOO_CELLS": aoo_count
        })

        msg = f"{ec}: EOO={area_km2:.2f} km², AOO={aoo_count}"
        results_log.append(msg)
        if log_callback:
            log_callback(msg)

        # ---------------------------
        # Progress update
        # ---------------------------
        progress = (i + 1) / total * 100
        if progress_callback:
            progress_callback(progress)

    del writer
    
    
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer_csv = csv.DictWriter(
                f,
                fieldnames=["EC_NAME", "EOO_KM2", "AOO_CELLS"]
            )

            writer_csv.writeheader()

            for row in csv_rows:
                writer_csv.writerow(row)

        msg = f"\nCSV saved: {csv_path}"
        results_log.append(msg)
        if log_callback:
            log_callback(msg)

    except Exception as e:
        msg = f"ERROR writing CSV: {str(e)}"
        results_log.append(msg)
        if log_callback:
            log_callback(msg)

    msg = f"\nShapefile saved: {shp_path}"
    results_log.append(msg)
    if log_callback:
        log_callback(msg)

    return results_log