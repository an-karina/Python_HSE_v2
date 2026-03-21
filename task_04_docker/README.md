# 👾 Energy Consumption & Price Dashboard

A full-stack web dashboard for visualising and managing energy consumption and pricing data for the **European and Asian parts of Russia**.

Built with **FastAPI** (backend) + **Streamlit** (frontend), containerised with **Docker Compose**.

---

## Project Structure

```
.
├── backend/
│   ├── main.py            # FastAPI app — REST API endpoints
│   ├── data.csv           # Persistent data storage
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py             # Streamlit dashboard
│   ├── requirements.txt
│   └── Dockerfile
└── docker-compose.yml
```

---

## Running with Docker Compose

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) installed

### Build and start

```bash
docker-compose up --build -d
```

This command builds both Docker images and starts both services together.

| Service | URL |
|---------|-----|
| Streamlit dashboard | http://localhost:8889 |
| FastAPI backend | http://localhost:8888 |
| FastAPI auto-docs (Swagger) | http://localhost:8888/docs |

### Stop the app

```bash
docker-compose down
```

### Rebuild after code changes

```bash
docker-compose up --build --force-recreate
```

---

## Running Locally (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# API available at http://localhost:8888
```

### Frontend

In a **separate terminal**:

```bash
cd frontend
pip install -r requirements.txt
# Change line 6 in app.py to: API = 'http://localhost:8888'
streamlit run app.py --server.port=8889
# Dashboard available at http://localhost:8889
```

---

## How to Use the Dashboard

Open the dashboard at **http://localhost:8889** in your browser.

### 1. Viewing Data

At the top of the page you will see the **Data Table** section, which displays all records currently stored. Each row contains:

- `id` — unique record identifier
- `datetime` — timestamp of the measurement
- `energy_europe` — energy consumption for the European part (MWh)
- `energy_asia` — energy consumption for the Asian part (MWh)
- `price_europe` — energy price for the European part
- `price_asia` — energy price for the Asian part

The total number of records is shown below the table.

### 2. Viewing Charts

Below the data table, the **Charts** section shows two interactive line charts:

- **Energy Consumption over Time** — plots `energy_europe` (pink) and `energy_asia` (green) over time
- **Energy Prices over Time** — plots `price_europe` (pink) and `price_asia` (green) over time

You can hover over any point to see its exact value, zoom in/out using the scroll wheel, and pan by clicking and dragging.

### 3. Adding a New Record

Scroll down to the **Add New Record** section. Fill in the form fields:

| Field | Format | Example |
|-------|--------|---------|
| Datetime | `YYYY-MM-DD HH:MM:SS` | `2024-06-15 12:00:00` |
| Energy Europe | Number ≥ 0 | `15000.0` |
| Energy Asia | Number ≥ 0 | `42000.0` |
| Price Europe | Number ≥ 0 | `9500.0` |
| Price Asia | Number ≥ 0 | `5100.0` |

Click **Add Record**. On success, a green confirmation message appears with the new record's ID, and the table refreshes automatically.

If the datetime format is invalid or any value is negative, a red error message will appear with details.

### 4. Deleting a Record

Scroll down to the **Delete Record** section. Enter the `id` of the record you want to remove and click **Delete Record**.

- If the record exists, a green success message appears and the table refreshes.
- If the `id` is not found, a red error message is shown.

---

## API Endpoints

You can also interact with the backend directly via **http://localhost:8888/docs** (Swagger UI).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/code_monkey_all_records` | Fetch all records |
| `POST` | `/code_monkey_adds_records` | Add a new record |
| `DELETE` | `/code_monkey_deletes_record/{id}` | Delete a record by ID |

### Record schema

| Field | Type | Validation |
|-------|------|------------|
| `datetime` | `str` | Must be parseable (e.g. `2024-01-01 00:00:00`) |
| `energy_europe` | `float` | Must be ≥ 0 |
| `energy_asia` | `float` | Must be ≥ 0 |
| `price_europe` | `float` | Must be ≥ 0 |
| `price_asia` | `float` | Must be ≥ 0 |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Uvicorn, Pandas, Pydantic |
| Frontend | Streamlit, Plotly, Requests, Pandas |
| Storage | CSV file (`data.csv`) |
| Containerisation | Docker, Docker Compose |

---

*Created by a crazy monkey that thinks that she can code 🤪*
