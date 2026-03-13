import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API = 'http://localhost:8000'

st.markdown('''
    <style>
        .stApp {
            background-color: #fff0f3;
        }
        
        input[type="number"], input[type="text"] {
            background-color: white !important;
        }
			
        .stFormSubmitButton button, .stButton button {
            background-color: #880e4f !important;
            color: white !important;
			border: 2px solid #880e4f !important;
        }
    </style>
''', unsafe_allow_html=True)

st.set_page_config(page_title='Energy Dashboard By Crazy Monkey', page_icon='🐒', layout='wide')

st.title('👾 Energy Consumption & Price Dashboard')
st.caption('Data for European and Asian parts of Russia - powered by FastAPI + Streamlit. Created by crazy monkey that thinks that she can code🤪')

def fetch_data():
	try:
		req = requests.get(f'{API}/code_monkey_all_records')
		req.raise_for_status()
		req = req.json()
		if req:
			df = pd.json_normalize(req)
			return df
		return pd.DataFrame()
	except Exception as e:
		st.error(f'Error fetching data: {e}')
		st.stop()

df = fetch_data()

st.header('🌸 Data Table')
if df.empty:
	st.info('No records found.')
else:
	st.dataframe(df, use_container_width=True, hide_index=True)
	st.markdown(f'**Total records:** {len(df)}')
	
	st.header('🎀 Charts')
	col1, col2 = st.columns(2)
	with col1:
		fig_energy = px.line(
			df,
			x='datetime',
			y=['energy_europe', 'energy_asia'],
			title='Energy Consumption over Time 👾',
			color_discrete_map={
				'energy_europe': '#ff1493',
				'energy_asia': '#008000',
			},
		)
		fig_energy.update_traces(mode='lines+markers')
		st.plotly_chart(fig_energy, use_container_width=True)

	with col2:
		fig_energy = px.line(
			df,
			x='datetime',
			y=['price_europe', 'price_asia'],
			title='Energy Prices over Time 👾',
			color_discrete_map={
				'price_europe': '#ff1493',
				'price_asia': '#008000',
			},
		)
		fig_energy.update_traces(mode='lines+markers')
		st.plotly_chart(fig_energy, use_container_width=True)

st.header('🎊 Add New Record')
with st.form('add_form'):
	col1, col2, col3 = st.columns(3)
	with col1:
		new_datetime = st.text_input('Datetimez', value='2024-01-01 00:00:00',help='Format: YYYY-MM-DD HH:MM:SS',)
		new_energy_europ = st.number_input('Energy Europe', min_value=0.0, value=12345.0, step=100.0)
	
	with col2:
		new_energy_asia = st.number_input('Energy Asia', min_value=0.0, value=45678.0, step=100.0)
		new_price_europ = st.number_input('Price Europe', min_value=0.0, value=9876.0, step=10.0)

	with col3:
		new_price_asia = st.number_input("Price Asia", min_value=0.0, value=5432.0, step=10.0)
	submitted = st.form_submit_button("Add Record", type="primary")

if submitted:
    payload = {
        "datetime": new_datetime,
        "energy_europe": new_energy_europ,
        "energy_asia": new_energy_asia,
        "price_europe": new_price_europ,
        "price_asia": new_price_asia,
    }
    try:
        req = requests.post(f"{API}/code_monkey_adds_records", json=payload)
        if req.status_code == 200:
            st.success(f"Record added successfully! (id={req.json()['id']})")
            st.rerun()
        else:
            detail = req.json().get("detail", req.text)
            st.error(f"Error {req.status_code}: {detail}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")	

st.header("🗑️ Delete Record")
with st.form("delete_form"):
    delete_id = st.number_input("Id to delete",min_value=1, step=1)
    delete_submitted = st.form_submit_button("Delete Record", type="secondary")

if delete_submitted:
    try:
        req = requests.delete(f"{API}/code_monkey_deletes_record/{int(delete_id)}", timeout=10)
        if req.status_code == 200:
            st.success(f"Record {int(delete_id)} deleted successfully!")
            st.rerun()
        elif req.status_code == 404:
            st.error(f"Record with id={int(delete_id)} not found.")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
