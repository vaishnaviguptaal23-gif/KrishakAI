import speech_recognition as sr
import pyttsx3
import streamlit as st

class VoiceAssistant:
    def __init__(self, language_code="en"):
        self.language_code = language_code
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()

        # Set voice (Hindi/English)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id)

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()
        st.success(f"🔊 {text}")

    def listen(self):
        with sr.Microphone() as source:
            st.info("🎤 बोलिए / Speak now...")
            audio = self.recognizer.listen(source)

        try:
            # Try Hindi first
            text = self.recognizer.recognize_google(audio, language="hi-IN")
            st.write(f"🗣 आपने कहा: {text}")
            return text

        except:
            try:
                # fallback English
                text = self.recognizer.recognize_google(audio, language="en-IN")
                st.write(f"🗣 You said: {text}")
                return text
            except:
                return "Sorry samajh nahi aaya"

    def get_response(self, query):
        q = query.lower()

        # 🌱 Pest
        if "pest" in q or "कीट" in q or "insect" in q:
            return "कीट नियंत्रण के लिए नीम तेल या उचित pesticide का उपयोग करें। Use neem oil or recommended pesticide."

        # 🌦 Weather
        elif "weather" in q or "मौसम" in q:
            return "मौसम की जानकारी dashboard में देखें। Please check weather section in dashboard."

        # 🌾 Crop
        elif "crop" in q or "फसल" in q:
            return "फसल के लिए सही सिंचाई और उर्वरक का उपयोग करें। Maintain proper irrigation and fertilizers."

        # 💊 Disease
        elif "disease" in q or "रोग" in q:
            return "रोग नियंत्रण के लिए fungicide का उपयोग करें और प्रभावित पत्तियों को हटाएं।"

        else:
            return "मैं खेती से जुड़े सवालों में मदद कर सकता हूँ। I can help with farming related questions."

    def voice_conversation(self):
        if st.button("🎙 Start / शुरू करें"):
            query = self.listen()
            response = self.get_response(query)
            self.speak(response)