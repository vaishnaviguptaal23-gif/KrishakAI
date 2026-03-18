import streamlit as st
import cv2
import numpy as np
import pandas as pd
import os
from PIL import Image
from ultralytics import YOLO
import datetime
import time
from enum import Enum
import folium
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
import json
import urllib.request
import urllib.parse
from modules.login import login
from modules.language import translations
from modules.labour import labour_panel
# from modules.voice_assistant import VoiceAssistant
st.set_page_config(page_title="KrishakAI Pest Detection",layout="wide")
model=YOLO("yolov8n.pt")
# Load CSS
def load_css():
    with open("assets/style.css") as f:
     st.markdown(f"<style>{f.read()}</style>",unsafe_allow_html=True)
load_css()

# Default values used when fetching weather via location
if "fetched_temp" not in st.session_state:
    st.session_state["fetched_temp"] = 25
if "fetched_humidity" not in st.session_state:
    st.session_state["fetched_humidity"] = 60


def fetch_current_weather(lat: float, lon: float) -> dict:
    """Fetch current temperature and humidity for a given location using Open-Meteo."""
    # Open-Meteo provides free weather data with no API key required.
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode({
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "relativehumidity_2m",
            "timezone": "auto",
        })
    )

    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)

    current = data.get("current_weather", {})
    temperature = current.get("temperature")
    # Find closest humidity value for the current hour
    humidity = None
    if "hourly" in data and "time" in data["hourly"] and "relativehumidity_2m" in data["hourly"]:
        times = data["hourly"]["time"]
        humidities = data["hourly"]["relativehumidity_2m"]
        now = current.get("time")
        if now in times:
            idx = times.index(now)
            humidity = humidities[idx]
        else:
            # fallback to the most recent value if exact time not found
            humidity = humidities[-1] if humidities else None

    return {"temperature": temperature, "humidity": humidity}


class SeverityLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
# Database for crop stages,diseases,and treatment suggestions
class HybridCropDoctor:
    def __init__(self):
        self.disease_db = self._load_disease_database()
        self.crop_stages = self._load_crop_stages()
        self.pest_treatment_db = self._load_pest_treatment_database()
        # Lo
    def _load_disease_database(self) -> dict:
        """Load crop-disease knowledge base"""
        return {
            "wheat": {
                "rust": {
                    "symptoms": ["brown spots", "orange powder", "red patches"],
                    "treatment": "Triazole fungicide (Propiconazole)",
                    "organic": "Sulfur dust",
                    "severity": SeverityLevel.HIGH,
                    "prevention": "Clean seeds, crop rotation"
                },
                "powdery_mildew": {
                    "symptoms": ["white powder", "leaves pale"],
                    "treatment": "Potassium bicarbonate",
                    "organic": "Baking soda solution",
                    "severity": SeverityLevel.MEDIUM,
                    "prevention": "Good air circulation"
                }
            },
            "tomato": {
                "early_blight": {
                    "symptoms": ["brown spots", "concentric rings", "yellow halo"],
                    "treatment": "Chlorothalonil spray",
                    "organic": "Neem oil + Copper sulfate",
                    "severity": SeverityLevel.MEDIUM,
                    "prevention": "Remove lower leaves, mulch"
                },
                "late_blight": {
                    "symptoms": ["water-soaked spots", "white mold", "stem rot"],
                    "treatment": "Metalaxyl-M + Mancozeb",
                    "organic": "Bordeaux mixture (1%)",
                    "severity": SeverityLevel.CRITICAL,
                    "prevention": "Avoid overhead irrigation"
                }
            }
        }
    
    def _load_crop_stages(self) -> dict:
        """Growth stages affect disease susceptibility"""
        return {
            "wheat": ["germination", "tillering", "grain_filling", "maturity"],
            "tomato": ["seedling", "flowering", "fruit_set", "mature_fruit"]
        }
    
    def _load_pest_treatment_database(self) -> dict:
        """Pest treatment database with crop-specific dosages"""
        return {
            "aphid": {
                "common_name": "Aphids",
                "description": "Small, soft-bodied insects that suck plant sap",
                "treatment": {
                    "chemical": "Imidacloprid 17.8% SL",
                    "organic": "Neem oil spray",
                    "biological": "Ladybird beetles (natural predators)"
                },
                "dosage": {
                    "wheat": "0.3-0.5 ml per liter of water, spray 200-300 liters per acre",
                    "rice": "0.4-0.6 ml per liter of water, spray 300-400 liters per acre",
                    "cotton": "0.5-0.7 ml per liter of water, spray 200-300 liters per acre",
                    "tomato": "0.3-0.5 ml per liter of water, spray 200-300 liters per acre",
                    "potato": "0.4-0.6 ml per liter of water, spray 300-400 liters per acre"
                },
                "prevention": "Plant resistant varieties, maintain field hygiene"
            },
            "beetle": {
                "common_name": "Beetles",
                "description": "Hard-shelled insects that chew leaves",
                "treatment": {
                    "chemical": "Chlorpyrifos 20% EC",
                    "organic": "Pyrethrum extract",
                    "biological": "Parasitic wasps"
                },
                "dosage": {
                    "wheat": "2-3 ml per liter of water, spray 200-300 liters per acre",
                    "rice": "2.5-3.5 ml per liter of water, spray 300-400 liters per acre",
                    "cotton": "3-4 ml per liter of water, spray 200-300 liters per acre",
                    "tomato": "2-3 ml per liter of water, spray 200-300 liters per acre",
                    "potato": "2.5-3.5 ml per liter of water, spray 300-400 liters per acre"
                },
                "prevention": "Crop rotation, deep ploughing"
            },
            "caterpillar": {
                "common_name": "Caterpillars",
                "description": "Larval stage of moths and butterflies that eat leaves",
                "treatment": {
                    "chemical": "Emamectin benzoate 5% SG",
                    "organic": "Bacillus thuringiensis (Bt)",
                    "biological": "Trichogramma wasps"
                },
                "dosage": {
                    "wheat": "0.2-0.4 gm per liter of water, spray 200-300 liters per acre",
                    "rice": "0.3-0.5 gm per liter of water, spray 300-400 liters per acre",
                    "cotton": "0.4-0.6 gm per liter of water, spray 200-300 liters per acre",
                    "tomato": "0.2-0.4 gm per liter of water, spray 200-300 liters per acre",
                    "potato": "0.3-0.5 gm per liter of water, spray 300-400 liters per acre"
                },
                "prevention": "Remove egg masses, use pheromone traps"
            },
            "whitefly": {
                "common_name": "Whiteflies",
                "description": "Small white flying insects that suck sap",
                "treatment": {
                    "chemical": "Buprofezin 25% SC",
                    "organic": "Sticky yellow traps",
                    "biological": "Encarsia wasps"
                },
                "dosage": {
                    "wheat": "1-1.5 ml per liter of water, spray 200-300 liters per acre",
                    "rice": "1.2-1.8 ml per liter of water, spray 300-400 liters per acre",
                    "cotton": "1.5-2 ml per liter of water, spray 200-300 liters per acre",
                    "tomato": "1-1.5 ml per liter of water, spray 200-300 liters per acre",
                    "potato": "1.2-1.8 ml per liter of water, spray 300-400 liters per acre"
                },
                "prevention": "Avoid nitrogen-rich fertilizers, use reflective mulches"
            },
            "spider_mite": {
                "common_name": "Spider Mites",
                "description": "Tiny spider-like pests that cause webbing",
                "treatment": {
                    "chemical": "Abamectin 1.9% EC",
                    "organic": "Sulfur spray",
                    "biological": "Predatory mites"
                },
                "dosage": {
                    "wheat": "0.5-0.7 ml per liter of water, spray 200-300 liters per acre",
                    "rice": "0.6-0.8 ml per liter of water, spray 300-400 liters per acre",
                    "cotton": "0.7-1 ml per liter of water, spray 200-300 liters per acre",
                    "tomato": "0.5-0.7 ml per liter of water, spray 200-300 liters per acre",
                    "potato": "0.6-0.8 ml per liter of water, spray 300-400 liters per acre"
                },
                "prevention": "Maintain humidity, avoid dust"
            }
        }
    
    def diagnose(self, crop: str, symptoms: list, 
                weather_data: dict = None, growth_stage: str = None) -> dict:
        """
        Hybrid diagnosis using multiple signals
        """
        # Step 1: Symptom matching
        matched_diseases = self._match_symptoms(crop, symptoms)
        
        # Step 2: Rule-based filtering
        filtered_diseases = self._apply_rules(crop, matched_diseases, 
                                             weather_data, growth_stage)
        
        # Step 3: AI confidence scoring
        final_results = self._score_with_ml(crop, symptoms, filtered_diseases)
        
        return self._format_advice(final_results)
    
    def _match_symptoms(self, crop: str, symptoms: list) -> list:
        """Rule-based symptom matching"""
        if not symptoms:
            return []
        matches = []
        crop_diseases = self.disease_db.get(crop, {})
        
        for disease, details in crop_diseases.items():
            disease_symptoms = details["symptoms"]
            match_score = sum(1 for s in symptoms 
                            if any(sym in s.lower() 
                                  for sym in disease_symptoms)) / len(symptoms)
            if match_score > 0.5:
                matches.append({
                    "disease": disease,
                    "match_score": match_score,
                    "details": details
                })
        
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)
    
    def _apply_rules(self, crop: str, diseases: list, 
                    weather_data: dict = None, growth_stage: str = None) -> list:
        """Apply agricultural rules"""
        if not weather_data:
            return diseases
        
        # High humidity favors fungal diseases
        if weather_data.get("humidity") > 80:
            for d in diseases:
                if "fungal" in d["details"].get("type", "").lower():
                    d["match_score"] *= 1.2
        
        return diseases
    
    def _score_with_ml(self, crop: str, symptoms: list, diseases: list) -> list:
        """Would integrate ML model for final scoring"""
        # Placeholder - in production, call your ML model
        return diseases
    
    def _format_advice(self, results: list) -> dict:
        """Format final recommendation"""
        if not results:
            return {
                "diagnosis": "Unknown condition",
                "confidence": "N/A",
                "severity": "Unknown",
                "treatment": "Consult local agriculture expert",
                "organic_option": "N/A",
                "prevention": "N/A",
                "immediate_actions": ["Consult local agriculture expert"],
                "timeline": "N/A",
                "when_to_seek_help": []
            }
        
        primary = results[0]
        details = primary["details"]
        
        return {
            "diagnosis": primary["disease"].replace("_", " ").title(),
            "confidence": f"{primary['match_score']:.0%}",
            "severity": details.get("severity").value,
            "treatment": details["treatment"],
            "organic_option": details["organic"],
            "prevention": details["prevention"],
            "immediate_actions": self._get_immediate_actions(details.get("severity")),
            "timeline": self._estimate_timeline(details.get("severity")),
            "when_to_seek_help": self._get_escalation_criteria(details.get("severity"))
        }
    
    def _get_immediate_actions(self, severity) -> list:
        actions = {
            SeverityLevel.LOW: ["Monitor daily", "Improve air circulation"],
            SeverityLevel.MEDIUM: ["Start treatment immediately", "Remove infected leaves"],
            SeverityLevel.HIGH: ["Begin treatment today", "Isolate affected plants"],
            SeverityLevel.CRITICAL: ["Emergency treatment required", "Contact extension office"]
        }
        return actions.get(severity, [])
    
    def _estimate_timeline(self, severity) -> str:
        timelines = {
            SeverityLevel.LOW: "2-3 weeks",
            SeverityLevel.MEDIUM: "1-2 weeks",
            SeverityLevel.HIGH: "3-5 days",
            SeverityLevel.CRITICAL: "1-2 days"
        }
        return timelines.get(severity, "Unknown")
    
    def _get_escalation_criteria(self, severity) -> list:
        criteria = {
            SeverityLevel.LOW: ["Monitor for spread", "Check within 1 week"],
            SeverityLevel.MEDIUM: ["Spread to other leaves", "No improvement in 3 days"],
            SeverityLevel.HIGH: ["Rapid spread", "Wilting of stems", "Fruit/grain damage"],
            SeverityLevel.CRITICAL: ["Immediate spread", "Plant death risk", "Entire field threatened"]
        }
        return criteria.get(severity, ["Contact extension office"])
    
    def get_pest_treatment(self, pest_name: str, crop: str = None) -> dict:
        """Get treatment information for detected pest"""
        pest_key = pest_name.lower().replace(" ", "_")
        if pest_key in self.pest_treatment_db:
            treatment_info = self.pest_treatment_db[pest_key].copy()
            if crop and crop in treatment_info.get("dosage", {}):
                treatment_info["recommended_dosage"] = treatment_info["dosage"][crop]
            else:
                treatment_info["recommended_dosage"] = "Contact local agriculture expert for crop-specific dosage"
            return treatment_info
        return {
            "common_name": pest_name,
            "description": "Unknown pest",
            "treatment": {"chemical": "Consult local agriculture expert", "organic": "Consult local agriculture expert"},
            "recommended_dosage": "Contact local agriculture expert",
            "prevention": "Consult local agriculture expert"
        }

# Initialize session state for menu
if 'menu' not in st.session_state:
    st.session_state.menu = "Home"

# Check login
if "Login" not in st.session_state or not st.session_state["Login"]:
    st.title("KrishakAI - Login Portal")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.header("Login")
        username = st.text_input("Mobile Number", key="login_mobile")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                with open("users.json", "r") as f:
                    users = json.load(f)
                if username in users and users[username]["password"] == password:
                    st.session_state["Login"] = True
                    st.session_state["user"] = users[username]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
            except FileNotFoundError:
                st.error("No users registered yet. Please register first.")
    
    with tab2:
        st.header("Register New Account")
        name = st.text_input("Full Name")
        age = st.number_input("Age", min_value=1, max_value=100, step=1)
        mobile = st.text_input("Mobile Number")
        password = st.text_input("Create Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        
        if st.button("Register"):
            if age < 18:
                st.error("Age must be 18 or above")
            elif password != confirm:
                st.error("Passwords do not match")
            elif not name or not mobile or not password:
                st.error("All fields are required")
            elif len(mobile) != 10 or not mobile.isdigit():
                st.error("Please enter a valid 10-digit mobile number")
            elif sum(c.isdigit() for c in password) < 4:
                st.error("Password must contain at least 4 numeric digits")
            else:
                # Save to file
                try:
                    with open("users.json", "r") as f:
                        users = json.load(f)
                except FileNotFoundError:
                    users = {}
                
                if mobile in users:
                    st.error("Mobile number already registered")
                else:
                    users[mobile] = {
                        "name": name,
                        "age": age,
                        "password": password  # In production, hash this
                    }
                    with open("users.json", "w") as f:
                        json.dump(users, f)
                    st.success("Registration successful! Welcome to KrishakAI!")
                    st.session_state["Login"] = True
                    st.session_state["user"] = users[mobile]
                    st.rerun()
else:
    # Language selection (English/Hindi)
    lang_choice = st.selectbox(
        "Language / भाषा", 
        ["English", "हिन्दी"],
        index=0 if st.session_state.get("lang_code", "en") == "en" else 1,
        key="lang_choice"
    )
    lang_code = "en" if lang_choice == "English" else "hi"
    st.session_state["lang_code"] = lang_code
    t = translations.get(lang_code, translations["en"])

    # Horizontal navigation bar (with icons)
    st.markdown("---")
    cols = st.columns(9)  # Added one more column for voice assistant
    menu_buttons = [
        ("Home", f"🏠 {t['home']}"),
        ("Image Detection", f"🖼️ {t['image_detection']}"),
        ("Camera Detection", f"📷 {t['camera_detection']}"),
        ("Dashboard", f"📊 {t['dashboard']}"),
        ("Heatmap", f"🗺️ {t['heatmap']}"),
        ("AI Crop Doctor", f"🧠 {t['ai_crop_doctor']}"),
        ("Voice Assistant", f"🎤 {t['voice_assistant']}"),
        ("Help Desk", f"🆘 {t['help_desk']}")
    ]
    for i, (menu_key, label) in enumerate(menu_buttons):
        if cols[i].button(label, key=f"nav_{menu_key}"):
            st.session_state.menu = menu_key

    # Logout button
    if cols[8].button(f"🚪 {t['logout']}", key="logout"):
        st.session_state["Login"] = False
        if "user" in st.session_state:
            del st.session_state["user"]
        st.rerun()
    st.markdown("---")

    menu = st.session_state.menu
    if menu=="Home":
        user_name = st.session_state.get("user", {}).get("name", "User")
        st.title(f"Welcome {user_name} - {t['title']}")
        st.subheader(t.get("home_subtitle", "AI powered pest monitoring system for sustainable agriculture"))
        st.write(t.get("home_description", "KrishakAI helps farmers detect crop pests early using AI. Uploads crop images to detect infestations."))

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center'>🚜 {t.get('features_title','Features')}</h2>", unsafe_allow_html=True)
        feature_cols = st.columns(5)
        feature_items = [
            ("🕷️", t.get("feature_pest_detection", "Pest Detection")),
            ("📷", t.get("feature_camera", "Real-time Camera Monitoring")),
            ("📊", t.get("feature_dashboard", "Farmer Dashboard")),
            ("🧠", t.get("feature_doctor", "AI Crop Doctor")),
            ("🗺️", t.get("feature_heatmap", "Pest Heatmap"))
        ]
        for col, (emoji, label) in zip(feature_cols, feature_items):
            col.markdown(f"<div style='font-size:2.4rem; text-align:center'>{emoji}</div>", unsafe_allow_html=True)
            col.markdown(f"<div style='text-align:center; font-weight:bold'>{label}</div>", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        col1,col2 = st.columns([2, 1])
        col2.image(
            "https://farmonaut.com/wp-content/uploads/2024/10/Revolutionizing-Agriculture-How-Farmonauts-AI-Driven-Precision-Farming-Solutions-Boost-Crop-Yields-and-Sustainability_1.jpg"
        )
    
    elif menu=="Image Detection":
        st.header(t["upload"])
        
        # Crop selection for treatment recommendations
        selected_crop = st.selectbox(
            t.get("camera_select_crop", "Select Crop for Treatment Recommendations"),
            ["wheat", "rice", "cotton", "tomato", "potato"],
            key="image_crop"
        )
        
        doctor = HybridCropDoctor()
        
        # File uploader with custom styling
        st.markdown("### 📤 Upload Crop Image")
        uploaded_file=st.file_uploader(t["upload"],type=["jpg","png","jpeg"], label_visibility="collapsed") 
        
        if uploaded_file:
            # Create columns for better layout
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 📸 Original Image")
                image=Image.open(uploaded_file)   
                image = image.convert('RGB')  # Convert to RGB to remove alpha channel
                image_np=np.array(image)
                st.image(image, use_column_width=True)
            
            with col2:
                st.markdown("#### 🎯 Detection Results")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("🔍 Analyzing image..."):
                    status_text.text("⏳ Processing image...")
                    progress_bar.progress(25)
                    
                    results=model(image_np)
                    annotated=results[0].plot()
                    
                    progress_bar.progress(75)
                    status_text.text("✅ Detection complete!")
                    progress_bar.progress(100)
                    
                    st.image(annotated, use_column_width=True)
                
                progress_bar.empty()
                status_text.empty()
            
            boxes=results[0].boxes
            detected_pests = set()
            
            if boxes:
                # Success banner
                st.markdown("---")
                st.success(f"✅ **Detection Complete!** Found {len(boxes)} pest(s) in the image")
                st.markdown("---")
                
                # Summary Card for all detected pests
                st.subheader("🎯 **Quick Summary - All Detected Pests**")
                summary_data = []
                
                for box in boxes:
                    conf=float(box.conf)
                    cls=int(box.cls)
                    pest_name=model.names[cls]
                    detected_pests.add(pest_name)
                    risk_score=conf*100
                    
                    if conf > 0.5:  # Only show high confidence detections
                        treatment_info = doctor.get_pest_treatment(pest_name, selected_crop)
                        summary_data.append({
                            "🐛 Pest Name": treatment_info['common_name'],
                            "📊 Confidence": f"{conf:.2%}",
                            "⚠️ Risk Level": f"{risk_score:.1f}%",
                            "💊 Quantity/Acre": treatment_info['recommended_dosage'],
                            "🔬 Treatment": treatment_info['treatment']['chemical']
                        })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # Detailed treatment for each pest
                st.subheader("📋 **Detailed Treatment Guide**")
                for i, box in enumerate(boxes):
                    conf=float(box.conf)
                    cls=int(box.cls)
                    pest_name=model.names[cls]
                    risk_score=conf*100
                    
                    if conf > 0.5:  # Only show high confidence detections
                        treatment_info = doctor.get_pest_treatment(pest_name, selected_crop)
                        
                        with st.expander(f"🚨 #{i+1} {treatment_info['common_name']} - Detailed Treatment (Confidence: {conf:.2%})", expanded=(i==0)):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Risk Score", f"{risk_score:.1f}%", delta="High" if risk_score > 80 else "Medium" if risk_score > 50 else "Low")
                                st.write(f"**Pest Name:** {treatment_info['common_name']}")
                                st.write(f"**Confidence:** {conf:.2%}")
                            
                            with col2:
                                st.info("**📊 Quantity per Acre**")
                                st.write(treatment_info['recommended_dosage'])
                                st.write(f"**Description:** {treatment_info['description']}")
                            
                            with col3:
                                st.success("**Treatment Options:**")
                                st.write(f"🔬 **Chemical:** {treatment_info['treatment']['chemical']}")
                                st.write(f"🌿 **Organic:** {treatment_info['treatment']['organic']}")
                                if 'biological' in treatment_info['treatment']:
                                    st.write(f"🐛 **Biological:** {treatment_info['treatment']['biological']}")
                                st.write(f"🛡️ **Prevention:** {treatment_info['prevention']}")
                
                # Save to evidence
                for pest in detected_pests:
                    data = {
                        "date": [datetime.datetime.now()],
                        "pest": [pest],
                        "confidence": [max(float(box.conf) for box in boxes if model.names[int(box.cls)] == pest)],
                        "risk_score": [max(float(box.conf) * 100 for box in boxes if model.names[int(box.cls)] == pest)]
                    }
                    df_save=pd.DataFrame(data)
                    # Add headers only if file doesn't exist
                    if not os.path.exists("evidence.csv"):
                        df_save.to_csv("evidence.csv", mode="w", header=True, index=False)
                    else:
                        df_save.to_csv("evidence.csv", mode="a", header=False, index=False)
                
                st.info("✅ Detection saved to Dashboard! Go to **Dashboard** to view your detection history.")
            else:
                st.warning("⚠️ No pests detected in this image. Try:\n- Another image with visible pest damage\n- Better lighting\n- Closer view of affected leaves")
    elif menu=="Camera Detection":
        st.header(f"📷 {t['camera_detection']}")
        st.info(t.get("camera_instruction", "Use your device camera to capture a crop image."))
        st.write(t.get("camera_tip", "Tip: On mobile, rotate your phone in landscape mode for better framing."))

        # Crop selection for treatment recommendations
        selected_crop = st.selectbox(
            t.get("camera_select_crop", "Select Crop for Treatment Recommendations"),
            ["wheat", "rice", "cotton", "tomato", "potato"],
            key="camera_crop"
        )

        doctor = HybridCropDoctor()

        mode = st.radio(
            "Camera Mode",
            ["📸 Photo (mobile)", "🎥 Live (desktop)"],
            index=0,
            help="Photo mode works on mobile. Live mode uses OpenCV and works on local desktop machines."
        )

        if mode.startswith("📸"):
            camera_file = st.camera_input(
                f"📸 {t.get('camera_capture', 'Take a photo of the crop')}",
                key="camera_input"
            )

            if camera_file:
                image = Image.open(camera_file)
                image = image.convert('RGB')  # Convert to RGB to remove alpha channel
                image_np = np.array(image)
                st.image(image, caption=t.get("camera_capture", "Captured Photo"), use_column_width=True)

                results = model(image_np)
                annotated = results[0].plot()
                st.image(annotated, caption="Detection Result", use_column_width=True)

                boxes = results[0].boxes
                detected_pests = set()

                if boxes:
                    st.success(f"✅ Found {len(boxes)} pest(s)")
                    
                    # Summary Card for all detected pests
                    st.markdown("---")
                    st.subheader("🎯 **Detection Summary**")
                    summary_data = []
                    
                    for box in boxes:
                        conf = float(box.conf)
                        cls = int(box.cls)
                        pest_name = model.names[cls]
                        detected_pests.add(pest_name)
                        risk_score = conf * 100
                        
                        if conf > 0.5:
                            treatment_info = doctor.get_pest_treatment(pest_name, selected_crop)
                            summary_data.append({
                                "Pest Name": treatment_info['common_name'],
                                "Confidence": f"{conf:.2%}",
                                "Risk Level": f"{risk_score:.1f}%",
                                "Recommended Quantity": treatment_info['recommended_dosage'],
                                "Treatment": treatment_info['treatment']['chemical']
                            })
                    
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Detailed treatment for each pest
                    for box in boxes:
                        conf = float(box.conf)
                        cls = int(box.cls)
                        pest_name = model.names[cls]
                        risk_score = conf * 100
                        
                        if conf > 0.5:
                            treatment_info = doctor.get_pest_treatment(pest_name, selected_crop)
                            
                            with st.expander(f"🚨 {treatment_info['common_name']} - Detailed Treatment", expanded=False):
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric("Risk Score", f"{risk_score:.1f}%", delta="High" if risk_score > 80 else "Medium" if risk_score > 50 else "Low")
                                    st.write(f"**Pest Name:** {treatment_info['common_name']}")
                                    st.write(f"**Confidence:** {conf:.2%}")
                                
                                with col2:
                                    st.info("**📊 Quantity per Acre**")
                                    st.write(treatment_info['recommended_dosage'])
                                    st.write(f"**Description:** {treatment_info['description']}")
                                
                                with col3:
                                    st.success("**Treatment Options:**")
                                    st.write(f"🔬 **Chemical:** {treatment_info['treatment']['chemical']}")
                                    st.write(f"🌿 **Organic:** {treatment_info['treatment']['organic']}")
                                    if 'biological' in treatment_info['treatment']:
                                        st.write(f"🐛 **Biological:** {treatment_info['treatment']['biological']}")
                                    st.write(f"🛡️ **Prevention:** {treatment_info['prevention']}")

                    # Save evidence for detected pests
                    for pest in detected_pests:
                        data = {
                            "date": [datetime.datetime.now()],
                            "pest": [pest],
                            "confidence": [max(float(box.conf) for box in boxes if model.names[int(box.cls)] == pest)],
                            "risk_score": [max(float(box.conf) * 100 for box in boxes if model.names[int(box.cls)] == pest)]
                        }
                        df = pd.DataFrame(data)
                        # Add headers only if file doesn't exist
                        if not os.path.exists("evidence.csv"):
                            df.to_csv("evidence.csv", mode="w", header=True, index=False)
                        else:
                            df.to_csv("evidence.csv", mode="a", header=False, index=False)
                    
                    st.info("✅ Detection saved to Dashboard!")
                else:
                    st.warning("⚠️ No pests detected. Try a different angle or better lighting.")
                    if st.button(t.get("camera_capture_again", "Capture again"), key="camera_capture_again"):
                        st.session_state["camera_input"] = None
                        st.rerun()
            else:
                st.info(t.get("camera_idle", "Use the camera control above to take a photo and run pest detection."))

        else:
            st.warning("⚠️ Live camera mode may not work on remote servers. Use a local desktop for best results.")
            camera_index = st.selectbox("Select Camera Device", [0, 1, 2], help="Try different numbers if camera doesn't work")
            preview_mode = st.checkbox(t.get("camera_preview_tip", "If you want a raw preview without detections, enable the preview mode."))

            run = st.checkbox("Start Live Camera")
            if run:
                camera = cv2.VideoCapture(camera_index)
                if not camera.isOpened():
                    st.error(f"❌ Cannot access camera device {camera_index}. Please check:")
                    st.write("- Camera permissions")
                    st.write("- Camera not in use by another application")
                    st.write("- Try a different camera device number")
                    run = False
                else:
                    st.success("✅ Camera accessed successfully!")
                    frame_window = st.image([])
                    status_placeholder = st.empty()
                    detected_pests = set()
                    stop_button = st.button("Stop Camera", key="stop_cam")

                    while run and not stop_button:
                        status_placeholder.info("📹 Camera active – detecting pests...")
                        ret, frame = camera.read()
                        if not ret:
                            st.error("Failed to capture frame from camera")
                            break

                        if preview_mode:
                            frame_window.image(frame, channels="BGR")
                        else:
                            results = model(frame)
                            annotated = results[0].plot()
                            frame_window.image(annotated, channels="BGR")

                            boxes = results[0].boxes
                            if boxes:
                                current_pests = set()
                                for box in boxes:
                                    conf = float(box.conf)
                                    cls = int(box.cls)
                                    pest_name = model.names[cls]
                                    current_pests.add(pest_name)

                                    if conf > 0.5:
                                        risk_score = conf * 100
                                        treatment_info = doctor.get_pest_treatment(pest_name, selected_crop)

                                        with st.expander(f"🚨 {treatment_info['common_name']} Detected (Confidence: {conf:.2f})", expanded=True):
                                            col1, col2 = st.columns(2)
                                            with col1:
                                                st.metric("Risk Score", f"{risk_score:.1f}%")
                                                st.write(f"**Description:** {treatment_info['description']}")
                                                st.write(f"**Recommended Dosage:** {treatment_info['recommended_dosage']}")

                                            with col2:
                                                st.success("**Treatment Options:**")
                                                st.write(f"🔬 **Chemical:** {treatment_info['treatment']['chemical']}")
                                                st.write(f"🌿 **Organic:** {treatment_info['treatment']['organic']}")
                                                if 'biological' in treatment_info['treatment']:
                                                    st.write(f"🐛 **Biological:** {treatment_info['treatment']['biological']}")
                                                st.info(f"🛡️ **Prevention:** {treatment_info['prevention']}")

                                new_pests = current_pests - detected_pests
                                if new_pests:
                                    for pest in new_pests:
                                        data = {
                                            "date": [datetime.datetime.now()],
                                            "pest": [pest],
                                            "confidence": [max(float(box.conf) for box in boxes if model.names[int(box.cls)] == pest)],
                                            "risk_score": [max(float(box.conf) * 100 for box in boxes if model.names[int(box.cls)] == pest)]
                                        }
                                        df = pd.DataFrame(data)
                                        # Add headers only if file doesn't exist
                                        if not os.path.exists("evidence.csv"):
                                            df.to_csv("evidence.csv", mode="w", header=True, index=False)
                                        else:
                                            df.to_csv("evidence.csv", mode="a", header=False, index=False)
                                    detected_pests.update(new_pests)

                        time.sleep(0.1)
                        if stop_button:
                            break

                    camera.release()
                    status_placeholder.empty()
                    st.info("Camera stopped.")
            else:
                st.info(t.get("camera_idle", "Use the camera control above to take a photo and run pest detection."))

    elif menu=="Heatmap":

        st.header(f"🗺️ {t['heatmap']}")
        st.write(t.get("location_help", "Enter your coordinates to center the map."))

        # Optional user location (latitude / longitude)
        # Provide current saved location defaults first
        if "heatmap_lat" not in st.session_state:
            st.session_state["heatmap_lat"] = "23.25"
        if "heatmap_lon" not in st.session_state:
            st.session_state["heatmap_lon"] = "77.41"

        def _set_heatmap_location_from_geoloc():
            try:
                location = streamlit_geolocation()
                if location and "latitude" in location and "longitude" in location:
                    st.session_state["heatmap_lat"] = str(location["latitude"])
                    st.session_state["heatmap_lon"] = str(location["longitude"])
                    st.success("✅ Location detected. You can now fetch weather below.")
                    st.rerun()
                else:
                    st.warning("Could not determine location. Please allow location permissions or enter coordinates manually.")
            except Exception as e:
                st.error(f"Error fetching location: {e}")

        if st.button("📍 Use my current location", key="heatmap_geoloc", on_click=_set_heatmap_location_from_geoloc):
            pass

        col1, col2 = st.columns([1, 1])
        with col1:
            lat = st.text_input(t.get("heatmap_lat", "Your Latitude"), value=str(st.session_state.get("heatmap_lat")), key="heatmap_lat")
        with col2:
            lon = st.text_input(t.get("heatmap_lon", "Your Longitude"), value=str(st.session_state.get("heatmap_lon")), key="heatmap_lon")

        if st.button("🌤️ Fetch current temperature and humidity", key="heatmap_weather"):
            try:
                center_lat = float(lat)
                center_lon = float(lon)
                weather = fetch_current_weather(center_lat, center_lon)
                st.session_state["heatmap_temp"] = weather.get("temperature")
                st.session_state["heatmap_humidity"] = weather.get("humidity")
                st.success(f"Weather: {st.session_state.get('heatmap_temp')}°C, {st.session_state.get('heatmap_humidity')}%")
            except Exception as e:
                st.error(f"Could not fetch weather: {e}")

        # Display last fetched weather if available
        if "heatmap_temp" in st.session_state or "heatmap_humidity" in st.session_state:
            temp = st.session_state.get("heatmap_temp")
            hum = st.session_state.get("heatmap_humidity")
            if temp is not None and hum is not None:
                st.info(f"🌡️ Temp: {temp}°C   💧 Humidity: {hum}%")

        farms = [
            {"location": [28.61, 77.20], "status": "pest", "crop": "Wheat"},
            {"location": [22.57, 88.36], "status": "healthy", "crop": "Rice"},
            {"location": [19.07, 72.87], "status": "pest", "crop": "Cotton"},
            {"location": [26.85, 80.94], "status": "healthy", "crop": "Sugarcane"},
        ]

        try:
            center_lat = float(lat)
            center_lon = float(lon)
        except ValueError:
            st.warning("Please enter valid numeric latitude and longitude.")
            center_lat = 23.25
            center_lon = 77.41

        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        folium.Marker(
            location=[center_lat, center_lon],
            popup=t.get("heatmap_your_location", "Your location"),
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

        for farm in farms:
            loc = farm["location"]
            status = farm["status"]
            crop = farm["crop"]
            if status == "pest":
                folium.Marker(
                    location=loc,
                    popup=f"Pest detected in {crop}",
                    icon=folium.Icon(color="red", icon="warning")
                ).add_to(m)
            else:
                folium.Marker(
                    location=loc,
                    popup=f"Healthy {crop} crop",
                    icon=folium.Icon(color="green", icon="ok")
                ).add_to(m)

        st_folium(m, width=900, height=500)


    elif menu=="AI Crop Doctor":

        st.header("🌾 AI Crop Doctor")
        
        doctor = HybridCropDoctor()
        
        tab1, tab2 = st.tabs(["Text Diagnosis", "Image Analysis"])
        
        with tab1:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                crop = st.selectbox("Select Crop", ["wheat", "rice", "cotton", "tomato", "potato"])
                symptoms = st.text_area("Describe symptoms", placeholder="e.g., brown spots, yellow leaves, wilting")

                st.markdown("**🌤️ Fetch real weather for your location**")
                lat = st.text_input("Latitude", value=str(st.session_state.get("weather_lat", "23.25")), key="weather_lat")
                lon = st.text_input("Longitude", value=str(st.session_state.get("weather_lon", "77.41")), key="weather_lon")

                if st.button("📍 Fetch current weather", key="fetch_weather"):
                    try:
                        loc_lat = float(lat)
                        loc_lon = float(lon)
                        weather = fetch_current_weather(loc_lat, loc_lon)

                        if weather.get("temperature") is not None:
                            st.session_state["fetched_temp"] = weather["temperature"]
                        if weather.get("humidity") is not None:
                            st.session_state["fetched_humidity"] = weather["humidity"]

                        st.success(f"Weather fetched: {st.session_state['fetched_temp']}°C, {st.session_state['fetched_humidity']}% humidity")
                    except Exception as e:
                        st.error(f"Could not fetch weather: {e}")

                humidity = st.slider(
                    "Current Humidity (%)", 0, 100, int(st.session_state.get("fetched_humidity", 60))
                )
                temperature = st.slider(
                    "Temperature (°C)", 5, 45, int(st.session_state.get("fetched_temp", 25))
                )

            with col2:
                st.write("**Growth Stages:**")
                growth_stage = st.selectbox("Select Stage", doctor.crop_stages.get(crop, [])) if crop in doctor.crop_stages else st.text_input("Growth Stage")
            
            if st.button("🔍 Get Diagnosis"):
                symptoms_list = [s.strip() for s in symptoms.split(",") if s.strip()]
                if not symptoms_list:
                    st.warning("Please describe the symptoms before getting diagnosis.")
                else:
                    weather_data = {"humidity": humidity, "temperature": temperature}
                    
                    with st.spinner("Analyzing..."):
                        result = doctor.diagnose(crop, symptoms_list, weather_data, growth_stage)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Disease", result["diagnosis"])
                        st.metric("Confidence", result["confidence"])
                        st.metric("Severity", result["severity"])
                    
                    with col2:
                        st.success("**Treatment Plan:**")
                        st.write(f"🔬 Chemical: {result['treatment']}")
                        st.write(f"🌿 Organic: {result['organic_option']}")
                        st.write(f"🛡️ Prevention: {result['prevention']}")
                    
                    st.warning("**Immediate Actions:**")
                    for action in result["immediate_actions"]:
                        st.write(f"  ✓ {action}")
                    
                    st.info(f"⏱️ Timeline: {result['timeline']}")
        
        with tab2:
            uploaded_image = st.file_uploader("Upload crop image", type=["jpg", "png", "jpeg"])
            if uploaded_image:
                image = Image.open(uploaded_image)
                image = image.convert('RGB')  # Convert to RGB to remove alpha channel
                st.image(image, caption="Uploaded Crop Image")
                # Would integrate with classification model here
    elif menu=="VoiceAssistant":
        st.header(f"🎤 {t.get('voice_assistant', 'Voice Assistant')}")
        st.info(t.get('voice_help', 'Ask questions in English or Hindi by voice, and get answers through voice response.'))
        
        # Language selection for voice
        voice_lang = st.radio(
            "Select Language / भाषा चुनें:",
            ["English", "हिन्दी"],
            horizontal=True,
            key="voice_language"
        )
        voice_lang_code = "en" if voice_lang == "English" else "hi"
        
        # Initialize voice assistant
        voice_assistant = VoiceAssistant(language_code=voice_lang_code)
        
        # Run voice conversation
        voice_assistant.voice_conversation()
        
        st.markdown("---")
        st.subheader("💡 Tips for Voice Assistant:")
        st.markdown("""
        - **English**: Ask about pests, diseases, weather, crops
        - **हिंदी**: कीटों, रोगों, मौसम, फसलों के बारे में पूछें
        - Speak clearly and wait for the response
        - You can ask follow-up questions
        - The assistant will provide voice responses for all queries
        """)
    elif menu=="Help Desk":
        st.header(f"🆘 {t['help_desk']}")
        
        with st.expander(f"🏠 {t['home']}"):
            st.write(t.get("help_home", "Welcome page shows the main feature overview and navigation."))
        
        with st.expander(f"🖼️ {t['image_detection']}"):
            st.write(t.get("help_image", "Upload images to detect pests and save results to your dashboard."))
        
        with st.expander(f"📷 {t['camera_detection']}"):
            st.write(t.get("help_camera", "Use the camera to capture plant images for real-time pest detection."))
        
        with st.expander(f"📊 {t['dashboard']}"):
            st.write(t.get("help_dashboard", "View pest detection history and risk trend charts."))
        
        with st.expander(f"🗺️ {t['heatmap']}"):
            st.write(t.get("help_heatmap", "See pest hotspots and healthy areas on an interactive map."))
        
        with st.expander(f"🌾 {t['ai_crop_doctor']}"):
            st.write(t.get("help_doctor", "Describe symptoms and get AI-driven diagnosis and treatment advice."))
        
        st.subheader("🎥 Recommended Tutorial Videos")
        st.write("Watch these videos to learn more about pest detection and crop management:")
        st.markdown("""
        - [Introduction to AI in Agriculture](https://www.youtube.com/results?search_query=ai+in+agriculture)
        - [Common Crop Pests Identification](https://www.youtube.com/results?search_query=crop+pests+identification)
        - [Using Technology for Farm Management](https://www.youtube.com/results?search_query=technology+in+farm+management)
        - [Organic Pest Control Methods](https://www.youtube.com/results?search_query=organic+pest+control)
        - [Smart Farming with AI](https://www.youtube.com/results?search_query=smart+farming+ai)
        """)
        
        st.info("🔗 Click the links above to watch helpful tutorial videos on YouTube!")
        
        st.subheader("📞 Contact Support")
        st.write("""
        **Need Help?** Contact our support team:
        - Email: support@krishakai.com
        - Phone: +91-XXXXXXXXXX
        - Visit: www.krishakai.com/support
        """)
        
        st.info("💡 **Tip**: Start with Image Detection to familiarize yourself with the app!")
    elif menu=="Dashboard":
        st.title(f"📊 {t['dashboard']}")
        st.write("Real-time updates show pest detections as they are logged into the system.")

        # Live refresh controls
        col1, col2 = st.columns([3, 1])
        with col1:
            live_mode = st.checkbox("Live updates (auto-refresh)", value=False)
        with col2:
            refresh_secs = st.slider("Refresh interval (seconds)", 2, 15, 5, label_visibility="collapsed")

        # Demo data button
        col_demo, col_clear = st.columns([1, 1])
        with col_demo:
            if st.button("📊 Load Demo Data"):
                demo_data = pd.DataFrame({
                    "date": pd.date_range(start="2026-03-10", periods=15, freq="1H"),
                    "pest": ["aphid", "beetle", "caterpillar", "whitefly", "spider_mite"] * 3,
                    "confidence": [0.92, 0.85, 0.88, 0.79, 0.95, 0.87, 0.90, 0.82, 0.89, 0.91, 0.84, 0.93, 0.86, 0.88, 0.94],
                    "risk_score": [92, 85, 88, 79, 95, 87, 90, 82, 89, 91, 84, 93, 86, 88, 94]
                })
                demo_data.to_csv("evidence.csv", index=False)
                st.success("✅ Demo data loaded! Charts will appear below.")
                st.rerun()

        with col_clear:
            if st.button("🗑️ Clear Data"):
                if os.path.exists("evidence.csv"):
                    os.remove("evidence.csv")
                    st.success("✅ Data cleared!")
                    st.rerun()

        def load_evidence():
            try:
                df = pd.read_csv("evidence.csv")
                if df.empty:
                    st.info("📌 No detections yet. Go to **Image Detection** or **Camera Detection** to start detecting pests!")
                    return pd.DataFrame(columns=["date", "pest", "confidence", "risk_score"])
                df["date"] = pd.to_datetime(df["date"])
                return df
            except FileNotFoundError:
                st.info("📌 No detection data available yet. Go to **Image Detection** or **Camera Detection** to start!")
                return pd.DataFrame(columns=["date", "pest", "confidence", "risk_score"])
            except Exception as e:
                st.warning(f"⚠️ Error loading data: {str(e)}")
                return pd.DataFrame(columns=["date", "pest", "confidence", "risk_score"])

        df = load_evidence()

        if not df.empty:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Detections", len(df))
            col2.metric("Average Risk", round(df["risk_score"].mean(), 2))
            col3.metric("Max Risk", round(df["risk_score"].max(), 2))

            pest_filter = st.selectbox("Filter by Pest", ["All"] + sorted(list(df["pest"].unique())))
            if pest_filter != "All":
                df_filtered = df[df["pest"] == pest_filter]
            else:
                df_filtered = df

            # Animated charts
            st.subheader("📈 Risk Trend Over Time")
            if not df_filtered.empty:
                risk_chart_data = df_filtered.set_index("date")["risk_score"]
                st.line_chart(risk_chart_data)
            else:
                st.info("No data for selected filter")

            st.subheader("📊 Pest Distribution")
            if not df.empty:
                pest_counts = df["pest"].value_counts()
                st.bar_chart(pest_counts)
            else:
                st.info("No pest data available")

            st.subheader("📉 Confidence Trend")
            if not df_filtered.empty:
                confidence_chart_data = df_filtered.set_index("date")["confidence"]
                st.area_chart(confidence_chart_data)
            else:
                st.info("No data for selected filter")

            st.subheader("📋 Detection History")
            st.dataframe(df_filtered, use_container_width=True)

            if live_mode:
                progress = st.progress(0)
                total_steps = refresh_secs * 10
                for i in range(total_steps):
                    progress.progress(int((i + 1) / total_steps * 100))
                    time.sleep(0.1)
                st.rerun()
        else:
            st.warning("📭 No detection data yet. Click '📊 Load Demo Data' to see example charts, or start detecting pests!")

