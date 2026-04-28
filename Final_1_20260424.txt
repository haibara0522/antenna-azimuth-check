import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math
from geopy.distance import geodesic
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import re
import numpy as np

# --- 1. AI VISION (OCR) SETUP ---
try:
    import easyocr
    @st.cache_resource
    def load_ocr():
        return easyocr.Reader(['en'], gpu=False)
    reader = load_ocr()
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Antenna Azimuth Check", page_icon="📡")

# --- 3. CORE FUNCTIONS ---
def get_exif_heading(image_file):
    try:
        img = Image.open(image_file)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {GPSTAGS.get(t, t): value[t] for t in value}
                    heading = gps_data.get('GPSImgDirection')
                    if heading:
                        return float(heading[0]/heading[1]) if isinstance(heading, tuple) else float(heading)
    except: 
        return None
    return None

def get_exif_gps_location(image_file):
    try:
        img = Image.open(image_file)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    
                    lat = gps_data.get('GPSLatitude')
                    lat_ref = gps_data.get('GPSLatitudeRef')
                    lon = gps_data.get('GPSLongitude')
                    lon_ref = gps_data.get('GPSLongitudeRef')
                    
                    if lat and lon:
                        lat_dd = float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600
                        if lat_ref == 'S':
                            lat_dd = -lat_dd
                        
                        lon_dd = float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600
                        if lon_ref == 'W':
                            lon_dd = -lon_dd
                        
                        return lat_dd, lon_dd, "EXIF"
    except Exception:
        pass
    return None

def extract_gps_from_ocr(image_file):
    if not OCR_AVAILABLE:
        return None, None, None
    
    try:
        img = Image.open(image_file).convert('RGB')
        img_np = np.array(img)
        results = reader.readtext(img_np)
        full_text = " ".join([res[1] for res in results])
        
        pattern1 = r'(\d{1,3}\.\d{4,})\s*[,;:\s]+\s*(\d{1,3}\.\d{4,})'
        match = re.search(pattern1, full_text)
        if match:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if 0 <= lat <= 90 and 0 <= lon <= 180:
                return lat, lon, "OCR (Decimal)"
        
        pattern2 = r'(\d{1,3}\.\d{4,})\s*[°\s]*([NS])[\s,;]+(\d{1,3}\.\d{4,})\s*[°\s]*([EW])'
        match = re.search(pattern2, full_text, re.IGNORECASE)
        if match:
            lat = float(match.group(1))
            if match.group(2).upper() == 'S':
                lat = -lat
            lon = float(match.group(3))
            if match.group(4).upper() == 'W':
                lon = -lon
            return lat, lon, "OCR (Decimal Deg)"
        
        numbers = re.findall(r'(\d{1,3}\.\d{4,})', full_text)
        if len(numbers) >= 2:
            lat = float(numbers[0])
            lon = float(numbers[1])
            if 0 <= lat <= 90 and 0 <= lon <= 180:
                return lat, lon, "OCR (Auto pair)"
        
    except Exception:
        pass
    
    return None, None, None

def get_photo_location(image_file):
    try:
        result = get_exif_gps_location(image_file)
        if result:
            return result
        
        if OCR_AVAILABLE:
            lat, lon, method = extract_gps_from_ocr(image_file)
            if lat is not None and lon is not None:
                return lat, lon, method
    except Exception:
        pass
    
    return None

def scan_text_for_azimuth(image_file):
    if not OCR_AVAILABLE:
        return None, None
    try:
        img = Image.open(image_file).convert('RGB')
        img_np = np.array(img)
        results = reader.readtext(img_np)
        full_text = " ".join([res[1] for res in results])

        patterns = [
            r'(?:azimuth|az|dir|direction|heading)[:\s]*(\d{1,3}(?:\.\d+)?)',
            r'(\d{1,3}(?:\.\d+)?)\s?(?:deg|°|o)'
        ]
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                return float(match.group(1)), full_text
        
        numbers = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\b', full_text)
        for num in numbers:
            val = float(num)
            if 0 <= val <= 360 and len(num) >= 2:
                return val, full_text
                
    except Exception:
        return None, None
    return None, None

def calculate_bearing(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360
    except Exception:
        return 0

def get_endpoint(lat, lon, bearing, distance_m=500):
    try:
        destination = geodesic(meters=distance_m).destination((lat, lon), bearing)
        return [destination.latitude, destination.longitude]
    except Exception:
        return [lat, lon]

def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        return geodesic((lat1, lon1), (lat2, lon2)).meters
    except Exception:
        return 999999

# --- 4. SESSION STATE INITIALIZATION ---
if 'manual_az' not in st.session_state:
    st.session_state.manual_az = None
if 'ai_az' not in st.session_state:
    st.session_state.ai_az = None
if 'active_az_source' not in st.session_state:
    st.session_state.active_az_source = None
if 'df_loaded' not in st.session_state:
    st.session_state.df_loaded = False
if 'photo_location' not in st.session_state:
    st.session_state.photo_location = None
if 'location_warning' not in st.session_state:
    st.session_state.location_warning = False
if 'photo_distance' not in st.session_state:
    st.session_state.photo_distance = None
if 'site_id' not in st.session_state:
    st.session_state.site_id = None
if 'az_design' not in st.session_state:
    st.session_state.az_design = None
if 'site_lat' not in st.session_state:
    st.session_state.site_lat = None
if 'site_lon' not in st.session_state:
    st.session_state.site_lon = None
if 'photo' not in st.session_state:
    st.session_state.photo = None
if 'location_verified' not in st.session_state:
    st.session_state.location_verified = False
if 'sector' not in st.session_state:
    st.session_state.sector = "S1"

# --- 5. MAIN DISPLAY ---
st.title("📡 Antenna Azimuth Check System")

with st.expander("📖 How to Use - Click to expand"):
    st.markdown("""
    1. **Upload CSV file** containing site design data
    2. **Select Site and Sector** to check
    3. **Upload antenna photo** (supports JPG, JPEG, PNG)
    4. System automatically checks GPS location from EXIF or OCR text
    5. **If location OK** → Click "SCAN AZIMUTH" for AI to read azimuth
    6. **Click on map** to set manual bearing (red line will appear)
    7. **Select which result to use** (AI / Manual Click)
    8. **Compare results** with design azimuth
    """)

threshold = 10
distance_threshold = 300

col_left, col_right = st.columns([0.3, 0.7], gap="medium")

with col_left:
    st.markdown("### 📂 Data Upload")
    
    st.markdown("**📊 Upload Design CSV**")
    uploaded_file = st.file_uploader("Choose CSV file", type=['csv'], key="csv_uploader", label_visibility="collapsed")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.lower() for c in df.columns]
            
            required_cols = ['site_id', 'azimuth_s1', 'azimuth_s2', 'azimuth_s3', 'azimuth_s4', 'lat_design', 'long_design']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                st.error(f"❌ Missing columns: {', '.join(missing)}")
                st.stop()
            
            search_query = st.text_input("🔍 Search Site:", "").strip().upper()
            filtered = [s for s in df['site_id'].unique() if search_query in str(s).upper()]
            
            if filtered:
                new_site_id = st.selectbox("📍 Select Site:", filtered)
                new_sector = st.radio("📡 Sector:", ["S1", "S2", "S3", "S4"], horizontal=True)
                
                if new_site_id != st.session_state.site_id or new_sector != st.session_state.sector:
                    st.session_state.manual_az = None
                    st.session_state.ai_az = None
                    st.session_state.active_az_source = None
                    st.session_state.photo_location = None
                    st.session_state.location_warning = False
                    st.session_state.location_verified = False
                    st.session_state.photo = None
                    st.session_state.photo_distance = None
                
                st.session_state.site_id = new_site_id
                st.session_state.sector = new_sector
                
                site_data = df[df['site_id'] == new_site_id].iloc[0]
                st.session_state.az_design = site_data[f'azimuth_{new_sector.lower()}']
                st.session_state.site_lat = site_data['lat_design']
                st.session_state.site_lon = site_data['long_design']
                st.session_state.df_loaded = True
                
                st.info(f"**Design Azimuth:** {st.session_state.az_design:.1f}°")
                st.caption(f"📍 **Site Location:** {st.session_state.site_lat:.6f}, {st.session_state.site_lon:.6f}")
            else:
                st.warning("No matching site found")
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
    else:
        st.info("📂 Please upload CSV file")
    
    st.markdown("---")
    
    st.markdown("**📸 Upload Antenna Photo**")
    photo = st.file_uploader("Choose photo", type=['jpg', 'jpeg', 'png'], 
                             key="photo_uploader", label_visibility="collapsed")
    
    if photo and st.session_state.df_loaded:
        is_new_photo = (st.session_state.photo is None or 
                       (hasattr(st.session_state.photo, 'name') and st.session_state.photo.name != photo.name))
        
        if is_new_photo:
            st.session_state.photo = photo
            st.session_state.location_verified = False
            st.session_state.location_warning = False
            st.session_state.manual_az = None
            st.session_state.ai_az = None
            st.session_state.active_az_source = None
            st.session_state.photo_location = None
            st.session_state.photo_distance = None
        
        if not st.session_state.location_verified and not st.session_state.location_warning:
            location_result = get_photo_location(photo)
            
            if location_result:
                if len(location_result) == 3:
                    photo_lat, photo_lon, method = location_result
                else:
                    photo_lat, photo_lon = location_result
                    method = "EXIF"
                
                distance = calculate_distance(st.session_state.site_lat, st.session_state.site_lon, photo_lat, photo_lon)
                
                st.success(f"✅ **GPS Found!** Source: {method}")
                st.info(f"📍 Photo location: {photo_lat:.6f}, {photo_lon:.6f}")
                st.info(f"📏 Distance to site: {distance:.0f} meters")
                
                if distance > distance_threshold:
                    st.session_state.location_warning = True
                    st.session_state.location_verified = False
                    st.session_state.photo_location = (photo_lat, photo_lon)
                    st.session_state.photo_distance = distance
                    
                    st.error(f"""
                    ❌ **LOCATION MISMATCH!**
                    Photo is **{distance:.0f}m** from site (Threshold: {distance_threshold}m)
                    """)
                else:
                    st.session_state.location_warning = False
                    st.session_state.location_verified = True
                    st.session_state.photo_location = (photo_lat, photo_lon)
                    st.session_state.photo_distance = distance
                    st.success(f"✅ **LOCATION VERIFIED!**")
                    st.rerun()
            else:
                st.warning("⚠️ No GPS data found in photo (checked EXIF and OCR text)")
    
    if st.session_state.location_verified:
        st.markdown("---")
        st.markdown("### ⚙️ Controls")
        threshold = st.slider("PASS/FAIL Threshold (degrees)", min_value=1, max_value=30, value=10, step=1, key="threshold_slider")
        distance_threshold = st.slider("Max allowed distance (meters)", min_value=50, max_value=500, value=300, step=50, key="distance_slider")

with col_right:
    if st.session_state.df_loaded and st.session_state.location_verified and st.session_state.photo is not None:
        site_id = st.session_state.site_id
        az_design = st.session_state.az_design
        site_lat = st.session_state.site_lat
        site_lon = st.session_state.site_lon
        photo = st.session_state.photo
        photo_lat, photo_lon = st.session_state.photo_location
        
        st.markdown("### 📊 Analysis View")
        
        col_photo, col_map = st.columns(2, gap="medium")
        
        with col_photo:
            st.markdown("**📸 Antenna Photo**")
            st.image(photo, use_container_width=True)
        
        with col_map:
            st.markdown("**🗺️ Site Map**")
            st.caption("💡 **Click on map to set manual bearing - Red line will appear**")
            
            try:
                m = folium.Map(location=[site_lat, site_lon], zoom_start=19,
                               tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                               attr='Google Satellite')
                
                # Site marker
                folium.Marker([site_lat, site_lon], 
                             popup=f"🏢 Site: {site_id}\nDesign: {az_design:.1f}°", 
                             icon=folium.Icon(color='blue')).add_to(m)
                
                # Photo marker
                folium.Marker([photo_lat, photo_lon], 
                             popup=f"📸 Photo Location",
                             icon=folium.Icon(color='green', icon='camera', prefix='fa')).add_to(m)
                
                # Line from photo to site
                folium.PolyLine([[photo_lat, photo_lon], [site_lat, site_lon]],
                               color='orange', weight=2, dash_array='5').add_to(m)
                
                # Design line from SITE
                design_endpoint = get_endpoint(site_lat, site_lon, az_design)
                folium.PolyLine([[site_lat, site_lon], design_endpoint], 
                               color="#00BFFF", weight=3, 
                               tooltip=f"Design: {az_design:.1f}°").add_to(m)
                
                # MANUAL LINE - RED LINE
                if st.session_state.manual_az is not None:
                    manual_endpoint = get_endpoint(photo_lat, photo_lon, st.session_state.manual_az)
                    folium.PolyLine([[photo_lat, photo_lon], manual_endpoint], 
                                   color="#FF4B4B", weight=5,
                                   tooltip=f"Manual: {st.session_state.manual_az:.1f}°").add_to(m)
                    folium.Marker(manual_endpoint, 
                                 icon=folium.Icon(color='red', icon='flag', prefix='fa'),
                                 popup=f"Manual: {st.session_state.manual_az:.1f}°").add_to(m)
                
                # Active AI line
                if st.session_state.active_az_source == 'ai' and st.session_state.ai_az is not None:
                    active_endpoint = get_endpoint(photo_lat, photo_lon, st.session_state.ai_az)
                    folium.PolyLine([[photo_lat, photo_lon], active_endpoint], 
                                   color="#FFA500", weight=4,
                                   tooltip=f"AI: {st.session_state.ai_az:.1f}°").add_to(m)
                
                map_data = st_folium(m, width=None, height=400, key="site_map")
                
                # Handle map click - MANUAL BEARING
                if map_data and map_data.get('last_clicked'):
                    clicked_lat = map_data['last_clicked']['lat']
                    clicked_lng = map_data['last_clicked']['lng']
                    bearing = calculate_bearing(photo_lat, photo_lon, clicked_lat, clicked_lng)
                    st.session_state.manual_az = bearing
                    st.success(f"📍 Manual bearing set to {bearing:.1f}°")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Map error: {e}")
        
        st.markdown("---")
        
        # Scanning Results
        st.markdown("### 📊 Scanning Results")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            if st.session_state.ai_az is not None:
                st.metric("🤖 AI Detected", f"{st.session_state.ai_az:.1f}°")
                if st.button("✓ Use AI Result", key="use_ai"):
                    st.session_state.active_az_source = 'ai'
                    st.session_state.manual_az = None
                    st.rerun()
            else:
                st.metric("🤖 AI Detected", "Not scanned")
        
        with col_res2:
            if st.session_state.manual_az is not None:
                st.metric("🖱️ Manual Click", f"{st.session_state.manual_az:.1f}°")
                if st.button("✓ Use Manual Result", key="use_manual"):
                    st.session_state.active_az_source = 'manual'
                    st.session_state.ai_az = None
                    st.rerun()
            else:
                st.metric("🖱️ Manual Click", "Not set")
                st.caption("Click on map above")
        
        with col_res3:
            st.metric("📐 Design", f"{az_design:.1f}°")
        
        # SCAN AZIMUTH button
        if st.button("🔍 SCAN AZIMUTH", use_container_width=True, type="primary"):
            with st.spinner("AI analyzing photo..."):
                res = get_exif_heading(photo)
                if res is not None:
                    st.session_state.ai_az = res
                    st.success(f"✅ AI Detected: {res}° (EXIF)")
                else:
                    res_az, _ = scan_text_for_azimuth(photo)
                    if res_az is not None:
                        st.session_state.ai_az = res_az
                        st.success(f"✅ AI Detected: {res_az}° (OCR)")
                    else:
                        st.error("❌ No azimuth found")
                st.rerun()
        
        # Active azimuth
        st.markdown("---")
        if st.session_state.active_az_source == 'ai' and st.session_state.ai_az is not None:
            st.info(f"🎯 **Active: {st.session_state.ai_az:.1f}° (AI)**")
            current_az = st.session_state.ai_az
        elif st.session_state.active_az_source == 'manual' and st.session_state.manual_az is not None:
            st.info(f"🎯 **Active: {st.session_state.manual_az:.1f}° (Manual Click)**")
            current_az = st.session_state.manual_az
        else:
            current_az = None
            st.info("🎯 No active azimuth selected")
        
        # Comparison & Conclusion
        st.markdown("---")
        st.markdown("### 📊 Comparison & Conclusion")
        
        if current_az is not None:
            diff = abs(current_az - az_design)
            if diff > 180:
                diff = 360 - diff
            
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.metric("📊 Deviation", f"{diff:.1f}°")
            with col_c2:
                status = "✅ PASS" if diff <= threshold else "❌ FAIL"
                st.metric("Status", status)
            with col_c3:
                source = "AI" if st.session_state.active_az_source == 'ai' else "Manual"
                st.metric("Source", source)
            
            if diff <= threshold:
                st.success(f"🎉 **PASS** - Deviation: {diff:.1f}° ≤ {threshold}°")
            else:
                st.error(f"❌ **FAIL** - Deviation: {diff:.1f}° > {threshold}°")
        else:
            st.info("Select AI or Manual result to compare with design")
    
    elif st.session_state.df_loaded and st.session_state.location_warning:
        st.warning("⚠️ Location mismatch! Please upload a photo within the allowed distance.")
    
    else:
        st.info("👆 Complete the steps on the left panel")