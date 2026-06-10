
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

app = FastAPI(title="CONSTRUCT-AI Demo")

class EstimateRequest(BaseModel):
    work_type: str
    qty: float
    location: str

@app.get("/")
async def root():
    return {"message": "CONSTRUCT-AI Engine Online. Use /estimate endpoint."}

@app.post("/estimate")
async def get_estimate(req: EstimateRequest):
    try:
        # 1. 地域係数の読み込み
        with open('/home/user/construct_ai/region_coefficients.json', 'r') as f:
            regions = json.load(f)
        
        coeff = regions.get(req.location, regions['Default'])
        
        # 2. 単価の取得 (本来は Cognee からの recall だが、MVPでは簡易的に固定値を想定)
        # 実際は cognee.recall(f"Price for {req.work_type}")
        unit_price = 2000 
        
        # 3. 積算計算
        total = req.qty * unit_price * coeff['coefficient']
        
        return {
            "location": req.location,
            "coefficient": coeff['coefficient'],
            "base_unit_price": unit_price,
            "calculated_total": total,
            "currency": "JPY",
            "status": "Instant Estimate"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080)
