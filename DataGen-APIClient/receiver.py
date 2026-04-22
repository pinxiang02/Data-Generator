from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="DataGen Test Receiver")

# In-memory dictionary to hold our running calculations
stats = {
    "payload_count": 0,
    "total_temp1": 0,
    "total_temp2": 0.0,
    "max_pressure": 0,
    "unique_machines": set() # Using a set to track unique MachineIDs
}

# 1. NEW STRUCTURE: Exactly matching your text specification
class GeneratorPayload(BaseModel):
    MachineID: str
    Temperature1: int
    Temperature2: float
    Pressure: int
    
    # Keeping the optional timestamp we added earlier
    timestamp: Optional[str] = Field(None, alias="@timestamp")

# 2. Updated Receiver Logic
@app.post("/ingest")
async def ingest_data(data: GeneratorPayload):
    # Update global counts
    stats["payload_count"] += 1
    stats["unique_machines"].add(data.MachineID)
    
    # Calculate Rolling Averages
    stats["total_temp1"] += data.Temperature1
    stats["total_temp2"] += data.Temperature2
    avg_temp1 = stats["total_temp1"] / stats["payload_count"]
    avg_temp2 = stats["total_temp2"] / stats["payload_count"]

    # Track Maximum Pressure
    if data.Pressure > stats["max_pressure"]:
        stats["max_pressure"] = data.Pressure

    # Alert if pressure spikes above a theoretical threshold (e.g., 90)
    pressure_alert = data.Pressure > 90

    # Print the live analytics to the terminal
    print(f"\n--- Data Received from [ {data.MachineID} ] ---")
    print(f"Temperature 1 : {data.Temperature1} (Rolling Avg: {avg_temp1:.1f})")
    print(f"Temperature 2 : {data.Temperature2:.2f} (Rolling Avg: {avg_temp2:.2f})")
    print(f"Pressure      : {data.Pressure} (All-Time Max: {stats['max_pressure']}) | Alert: {pressure_alert}")
    
    # 3. Return the calculated data
    return {
        "status": "success",
        "calculations": {
            "machine_id": data.MachineID,
            "average_temperature_1": round(avg_temp1, 2),
            "average_temperature_2": round(avg_temp2, 2),
            "max_pressure": stats["max_pressure"],
            "total_machines_tracked": len(stats["unique_machines"]),
            "pressure_warning": pressure_alert
        }
    }