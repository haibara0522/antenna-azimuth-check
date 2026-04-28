\# 📡 Antenna Azimuth Check System



An intelligent web application for verifying antenna installation azimuth by comparing design data with actual photos. The system uses AI (OCR) to read azimuth values from photos and provides manual measurement tools for verification.



\## ✨ Features



\- \*\*CSV Data Import\*\* - Upload design data with site locations and azimuth specifications

\- \*\*GPS Location Verification\*\* - Automatically extracts GPS coordinates from photo EXIF data or OCR text

\- \*\*Distance Validation\*\* - Checks if the photo was taken within acceptable distance from the site (configurable threshold)

\- \*\*AI Azimuth Recognition\*\* - Uses EasyOCR to read azimuth values from:

&#x20; - EXIF metadata (GPSImgDirection)

&#x20; - Text printed on photos (watermarks, labels)

\- \*\*Manual Azimuth Measurement\*\* - Click directly on the map to measure bearing

\- \*\*Visual Comparison\*\* - Displays design vs actual azimuth lines on Google Satellite Map

\- \*\*PASS/FAIL Analysis\*\* - Automatically compares results against design threshold



\## 📋 Requirements



\### System Requirements

\- Python 3.8 or higher

\- 2GB RAM minimum (4GB recommended for OCR)

\- Internet connection (for Google Maps)



\### Input Requirements

\- \*\*CSV File\*\* with design data (see format below)

\- \*\*Photo\*\* in JPG, JPEG, or PNG format

\- \*\*GPS data\*\* in photo (EXIF or visible text) for location verification



\## 📊 CSV File Format



Your CSV file must contain the following columns:



| Column | Description | Example |

|--------|-------------|---------|

| `site\_id` | Site identifier | `SLA0006` |

| `lat\_design` | Site latitude (decimal degrees) | `10.823456` |

| `long\_design` | Site longitude (decimal degrees) | `106.629456` |

| `azimuth\_s1` | Design azimuth for Sector 1 | `0.0` |

| `azimuth\_s2` | Design azimuth for Sector 2 | `120.0` |

| `azimuth\_s3` | Design azimuth for Sector 3 | `240.0` |

| `azimuth\_s4` | Design azimuth for Sector 4 | `0.0` |



\### Sample CSV Data:

```csv

site\_id,lat\_design,long\_design,azimuth\_s1,azimuth\_s2,azimuth\_s3,azimuth\_s4

SLA0001,10.823456,106.629456,0,120,240

SLA0002,10.834567,106.640567,45,165,285,0



📖 How to Use - Click to expand



1. Upload CSV file containing site design data
2. Select Site and Sector to check
3. Upload antenna photo (supports JPG, JPEG, PNG)
4. System automatically checks GPS location from EXIF or OCR text
5. \*\*If location OK\*\* → Click "SCAN AZIMUTH" for AI to read azimuth. The azimuth proposed by AI IS FOR REFERENCE ONLY, PLEASE CHECK CAREFULLY.
6. Click on map to set manual bearing (red line will appear)
7. Select which result to use (AI / Manual Click)
8. Compare results with design azimuth



