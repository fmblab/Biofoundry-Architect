import streamlit as st

# 3. FAQ Section
st.title("❓ FAQ")
st.subheader("Frequently Asked Questions")

with st.expander("Q. What should I do if an error occurs?"):
    st.write(
        "Please capture a screenshot of the error and send it to the **Technical Support** contact listed at the bottom of the Home page.")

with st.expander("Q. Can I export the EPI analysis results?"):
    st.write("Yes, you can download the generated charts and tables directly from the `Workflow Analytics` page.")