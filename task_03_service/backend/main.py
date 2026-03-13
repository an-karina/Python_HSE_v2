import pandas as pd
from pydantic import BaseModel, field_validator
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI()

class RecordIn(BaseModel):
	datetime : str
	energy_europe : float
	energy_asia: float
	price_europe: float
	price_asia: float

	@field_validator('datetime')
	def validate_datetime(cls, v):
		try:
			pd.to_datetime(v)
		except Exception:
			raise ValueError("Invalide datetime. Enter a datetime string in such format '2024-01-01 00:00:00'.")
		return v

	@field_validator('energy_europe')
	def validate_energy_europe(cls, v):
		if v < 0:
			raise ValueError('Invalide energy_europe.Energy consumption cannot be negative.')
		return v

	@field_validator('energy_asia')
	def validate_energy_asia(cls, v):
		if v < 0:
			raise ValueError('Invalide energy_asia.Energy consumption cannot be negative.')
		return v

	@field_validator('price_europe')
	def validate_price_europe(cls, v):
		if v < 0:
			raise ValueError('Invalide price_europe.Price cannot be negative.')
		return v
	
	@field_validator('price_asia')
	def validate_price_asia(cls, v):
		if v < 0:
			raise ValueError('Invalide price_asia.Price cannot be negative.')
		return v

class RecordOut(RecordIn):
	id: int


def load_data() -> pd.DataFrame:
	try:
		df = pd.read_csv('data.csv')
		if 'id' not in df.columns:
			df.insert(0, 'id', range(1, len(df) + 1))
		else:
			df['id'] = df['id'].astype(int)
		return df
	except FileNotFoundError:
		return pd.DataFrame(columns=['id', 'datetime', 'energy_europe', 'energy_asia', 'price_europe', 'price_asia'])
	except Exception as e:
		print(f'Error occured: {e}')
		raise
	

def save_data(df: pd.DataFrame) -> None:
	try:
		df.to_csv('data.csv', index=False)
	except Exception as e:
		print(f'Error occured: {e}')
		raise

def next_id(df: pd.DataFrame) -> int:
	if df.empty or 'id' not in df.columns:
		return 1
	return int(df['id'].max()) + 1

@app.get("/code_monkey_all_records", response_model=list[RecordOut])
def get_records():
	try:
		df = load_data()
		return df.to_dict(orient="records")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	
@app.post("/code_monkey_adds_records", response_model=RecordOut)
def add_record(record: RecordIn):
	try:
		df = load_data()
		new_id = next_id(df)
		new_row = {"id": new_id, **record.model_dump()}
		df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
		save_data(df)
		return new_row
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.delete("/code_monkey_deletes_record/{record_id}")
def delete_record(record_id: int):
	try:
		df = load_data()
		if record_id not in df['id'].values:
			raise HTTPException(status_code=404, detail=f"Record with id={record_id} not found")
		df = df.query('id != @record_id').reset_index(drop=True)
		save_data(df)
		return {'message' : f"Record {record_id} deleted successfully"}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
	
	
if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
