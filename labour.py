import streamlit as st
import pandas as pd
def labour_panel():
    st.header("Labour & Contractor")
    name=st.text_input("Name")
    work=st.text_input("Work")
    contact=st.text_input("Contact")
if st.button("Add"):
        data={"name":[name],"work":[work],"contact":[contact]}
        df=pd.DataFrame(data)
        df.to_csv("labour.csv",mode="a",header=False,index=False)
        st.success("Added")
# try:df=pd.read_csv("labour.csv")
#     st.dataframe(df) 
# except:  
#      st.write("No Data")    