import streamlit as st
def login():
     st.markdown("<h2>KrishakAI Login</h2>",unsafe_allow_html=True)
     username=st.text_input("Username")
     password=st.text_input("Password",type="password")
     if st.button("Login"):
            if username=="admin" and password=="1234":
               st.session_state["Login"]=True
               st.success("login Successful")
            else:
                 st.error("Invalid Credentials")