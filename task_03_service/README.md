# 👾 Energy Consumption & Price Dashboard

A full-stack web dashboard for managing and visualizing energy consumption and price data for European and Asian regions of Russia.

Built with **FastAPI** (backend) + **Streamlit** (frontend) + **CSV** (storage).

---

## 🗂 Project Structure

```
task_03_service/
├── backend/
│   ├── main.py       ← FastAPI application
│   └── data.csv      ← persistent data storage
│   └── requirements.txt
├── frontend/
│   └── app.py        ← Streamlit UI
│   └── requirements.txt
└── README.md
```

---

## ⚙️ Requirements

- Python 3.10+
- pip packages:

```bash
pip install fastapi uvicorn streamlit pandas plotly requests pydantic
```

---

## 🚀 How to Run

### 1. Start the backend

```bash
python main.py
```

The API will be available at: `https://python-hse-v2.onrender.com`  
Interactive API docs at: `https://python-hse-v2.onrender.com/docs`

### 2. Start the frontend

Open a **second terminal** and run:

```bash
streamlit run app.py
```

The dashboard will open at: `http://localhost:8501](https://pythonhsev2-jrqdbg8watz33jge6m8j8s.streamlit.app`

> ⚠️ Both backend and frontend must be running at the same time.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/code_monkey_all_records` | Get all records |
| `POST` | `/code_monkey_adds_records` | Add a new record |
| `DELETE` | `/code_monkey_deletes_record/{id}` | Delete a record by ID |

### POST request body example

```json
{
  "datetime": "2024-01-01 00:00:00",
  "energy_europe": 12345.0,
  "energy_asia": 45678.0,
  "price_europe": 9876.0,
  "price_asia": 5432.0
}
```

---

## ✅ Data Validation

The API automatically validates all incoming data:

- `datetime` — must be a valid date string, e.g. `"2024-01-01 00:00:00"`
- `energy_europe`, `energy_asia` — must be `>= 0`
- `price_europe`, `price_asia` — must be `>= 0`

Invalid data returns a `422 Unprocessable Entity` response automatically.

---

## 📊 Dashboard Features

- **Data Table** — view all records in an interactive table
- **Charts** — two line charts showing energy consumption and prices over time
- **Add Record** — form to add new data points
- **Delete Record** — remove a record by ID

---

## 🗃 Data Format

The `data.csv` file uses the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Auto-generated unique ID |
| `datetime` | str | Timestamp of the record |
| `energy_europe` | float | Energy consumption, European region (MW·h) |
| `energy_asia` | float | Energy consumption, Asian region (MW·h) |
| `price_europe` | float | Energy price, European region (RUB/MW·h) |
| `price_asia` | float | Energy price, Asian region (RUB/MW·h) |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit + Plotly |
| Data | Pandas + CSV |
| Validation | Pydantic v2 |

---

*Created by a crazy monkey that thinks she can code 🤪*
