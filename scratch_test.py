import easyocr
from exif import Image as ExifImage
import cv2

image_path = r'd:\ZTE\Digital\Azimuth Check_Gemini\Test photo\SLA0006_Test azimuth.jpeg'

# 1. Try EXIF
with open(image_path, 'rb') as img_file:
    try:
        exif_img = ExifImage(img_file)
        if exif_img.has_exif:
            print("EXIF Attributes:", exif_img.list_all())
            if 'gps_img_direction' in exif_img.list_all():
                print("GPS Img Direction:", exif_img.gps_img_direction)
        else:
            print("No EXIF data")
    except Exception as e:
        print("EXIF Error:", str(e))

# 2. Try EasyOCR
try:
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image_path)
    print("OCR Text detected:")
    for (bbox, text, prob) in result:
        print(f"- {text} (prob: {prob:.2f})")
except Exception as e:
    print("EasyOCR Error:", str(e))
