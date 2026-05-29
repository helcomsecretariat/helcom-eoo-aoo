
# EOO / AOO QGIS Plugin

A QGIS plugin for calculating **Extent of Occurrence (EOO)** and **Area of Occupancy (AOO)** of ecosystem components (habitats, species, communities, etc) in the Baltic Sea. Calculation is done based on ecosystem components distribution raster datasets.

---

## 📌 Overview

This plugin calculates:

- **Extent of Occurrence (EOO)**  
  Area (km²) of the minimum convex polygon enclosing all raster cells with value `1`.

- **Area of Occupancy (AOO)**  
  Number of raster cells with value `1`.
  
User can optionally clip EOO polygons to the Baltic Sea coastline.

The plugin processes multiple ecosystem components (ECs) in one run and produces both **polygon (Shapefile)** and **tabular (CSV)** outputs.

---

## ⚙️ Features

- Step-by-step guided interface
- Batch processing of multiple ecosystem components
- Automatic raster validation
- Optional clipping to coastline
- Background processing (no UI freezing)
- Progress bar and runtime estimation
- CSV + Shapefile output
- Automatic result loading into QGIS

---

## 📂 Input Requirements

### 1. CSV File
- First column must contain a header in the first row and ecosystem component names in the next rows.
- Plugin reads data from the first column only. 

Example:
Zone1_A
Zone1_B
Zone1_C

---

### 2. Raster Folder

- One raster per ecosystem component
- File naming must match CSV entries

Example:
Zone1_A.tif
Zone1_B.tif
Zone1_C.tif

---

### 3. Raster Specifications

All rasters must:

- Have identical CRS
- Have identical resolution
- Have matching extent
- Contain values:
  - `1` → presence
  - `0` or other values → absence

---

### 4. Optional Coastline Layer

- Used for clipping EOO polygons
- Must be in the same CRS as rasters
- Provided with plugin (configurable)

---

## 🚀 Workflow

### Step 1 — Load CSV

- Select a CSV file with ecosystem components
- Plugin loads list for selection

---

### Step 2 — Select ECs

- Search and filter components
- Select/deselect items
- Confirm selection

---

### Step 3 — Select Raster Folder

- Choose folder with EC rasters
- Click **Validate rasters**

Validation includes:
- File presence
- Naming consistency
- Raster compatibility

---

### Step 4 — Output and Options

- Select output folder
- Choose:
  - ✅ Optional clipping to coastline
  - ✅ Optional "Add result to QGIS map"

---

### Step 5 — Run

- Click **Run selected tools**
- Monitor progress
- Cancel if needed

---

## 📊 Output

Results are saved in automatically created time-stamped **EOO_AOO_YYYYMMDD_HHMMSS** folder, in the selected output folder.

### Files generated:

#### 1. Shapefile **EOO_AOO_YYYYMMDD_HHMMSS.shp**

Contains an EOO polygon (clipped or not clipped, depending on user decision) and following fields:

| Field | Description |
|------|------------|
| EC_NAME | Ecosystem component |
| EOO_KM2 | Extent of Occurrence (km²) |
| AOO_CELLS | Number of occupied raster cells |

---

#### 2. CSV File **EOO_AOO_YYYYMMDD_HHMMSS.csv**

Contains no EOO polygon same fields as Shapefile.

---

## 🧠 Methodology

### EOO Calculation

1. Identify raster cells where value = 1
2. Convert cells to points (centroids)
3. Generate convex hull polygon
4. Optionally clip to coastline
5. Calculate area in km²

---

### AOO Calculation

1. Count number of cells where value = 1

---

## ⏱ Performance Notes

- Processing time depends on:
  - Number of ECs
  - Raster size
  - Clipping enabled (slower)

---

## ⚠️ Limitations

- Large rasters may increase processing time
- Partial outputs remain if processing is cancelled
- All rasters must be aligned and compatible

---

## 🛠 Installation

1. Download plugin ZIP
2. In QGIS, navigate to **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select plugin ZIP

---

## ✅ Usage Tips

- Prepare a CSV with ecosystem coimponent names and ensure that names in CSV are similar to tif raster names
- Pre-align rasters before processing
- Use projected CRS (e.g. EPSG:3035) for correct area calculation

---

## 👨‍💻 Author

Andžej Miloš  
GIS Application Developer

---

## 📄 License

Specify your license here (e.g. MIT, GPL)

---

## 🔄 Version

v1.0
