"""
CONSTRUCT-AI — FastAPI 積算エンジン
Railway デプロイ対応版 (認証・CORS・静的配信込み)
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import uvicorn

# ── ロギング ──────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("construct-ai")

# ── アプリ初期化 ──────────────────────────────────
app = FastAPI(
    title="CONSTRUCT-AI",
    description="建設工事 AI 積算 API — powered by HERMES",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API キー認証 ──────────────────────────────────
API_KEY = os.getenv("CONSTRUCT_API_KEY", "")  # 空なら認証スキップ(開発用)

async def verify_api_key(request: Request):
    if not API_KEY:
        return  # 開発環境: 認証なし
    key = request.headers.get("X-API-Key", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ── データ読み込み ────────────────────────────────
BASE_DIR = Path(__file__).parent

def load_json(filename: str) -> dict:
    path = BASE_DIR / filename
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}

# region_coefficients.json の構造:
# { "osaka": {"coefficient": 1.05, "labor_index": 1.08}, ... }
REGION_DATA: dict = load_json("region_coefficients.json")

# scrape_config.json or unit_prices.json の構造:
# { "earthwork": {"standard": 8500, "economy": 6500, "premium": 12000}, ... }
UNIT_PRICES: dict = load_json("unit_prices.json")

# フォールバック単価（JSONファイルがない場合）
FALLBACK_PRICES = {
    "earthwork":   {"standard": 8500,  "economy": 6500,  "premium": 12000},
    "concrete":    {"standard": 45000, "economy": 38000, "premium": 58000},
    "asphalt":     {"standard": 12000, "economy": 9500,  "premium": 16000},
    "drainage":    {"standard": 35000, "economy": 28000, "premium": 48000},
    "foundation":  {"standard": 55000, "economy": 45000, "premium": 75000},
    "framing":     {"standard": 280000,"economy": 220000,"premium": 380000},
    "roofing":     {"standard": 18000, "economy": 14000, "premium": 28000},
    "interior":    {"standard": 22000, "economy": 16000, "premium": 35000},
    "exterior":    {"standard": 3500,  "economy": 2800,  "premium": 5500},
    "electrical":  {"standard": 120000,"economy": 95000, "premium": 180000},
    "plumbing":    {"standard": 150000,"economy": 120000,"premium": 220000},
    "hvac":        {"standard": 200000,"economy": 160000,"premium": 300000},
    "demolition":  {"standard": 8000,  "economy": 6500,  "premium": 11000},
    "renovation":  {"standard": 35000, "economy": 28000, "premium": 50000},
}

FALLBACK_REGIONS = {
    "osaka":     {"coefficient": 1.05, "labor_index": 1.08},
    "tokyo":     {"coefficient": 1.20, "labor_index": 1.25},
    "yokohama":  {"coefficient": 1.15, "labor_index": 1.18},
    "nagoya":    {"coefficient": 1.08, "labor_index": 1.10},
    "kobe":      {"coefficient": 1.03, "labor_index": 1.05},
    "kyoto":     {"coefficient": 1.04, "labor_index": 1.06},
    "fukuoka":   {"coefficient": 0.98, "labor_index": 0.99},
    "sapporo":   {"coefficient": 0.95, "labor_index": 0.94},
    "sendai":    {"coefficient": 0.97, "labor_index": 0.97},
    "hiroshima": {"coefficient": 0.99, "labor_index": 1.00},
    "saitama":   {"coefficient": 1.12, "labor_index": 1.14},
    "chiba":     {"coefficient": 1.10, "labor_index": 1.12},
    "kanazawa":  {"coefficient": 1.00, "labor_index": 1.01},
    "shizuoka":  {"coefficient": 1.02, "labor_index": 1.03},
    "nara":      {"coefficient": 1.00, "labor_index": 1.01},
    "wakayama":  {"coefficient": 0.97, "labor_index": 0.98},
}

def get_unit_price(work_type: str, grade: str) -> int:
    prices = UNIT_PRICES.get(work_type) or FALLBACK_PRICES.get(work_type)
    if not prices:
        raise HTTPException(status_code=400, detail=f"Unknown work_type: {work_type}")
    return prices.get(grade) or prices.get("standard", 10000)

def get_region(location: str) -> dict:
    # 大文字小文字を無視して検索
    loc = location.lower()
    region = REGION_DATA.get(loc) or FALLBACK_REGIONS.get(loc)
    if not region:
        # 未登録地域は係数 1.0 で処理
        logger.warning(f"Unknown location '{location}', using coefficient=1.0")
        region = {"coefficient": 1.0, "labor_index": 1.0}
    return region

# ── スキーマ ──────────────────────────────────────
class EstimateRequest(BaseModel):
    work_type: str = Field(..., description="工種コード (例: earthwork, concrete)")
    qty: float     = Field(..., gt=0, description="数量")
    location: str  = Field(..., description="地域コード (例: osaka, tokyo)")
    grade: str     = Field("standard", description="グレード: standard / economy / premium")

class EstimateResponse(BaseModel):
    work_type: str
    qty: float
    location: str
    grade: str
    unit_price: int
    regional_coefficient: float
    labor_index: float
    base_cost: int
    material_cost: int
    labor_cost: int
    overhead: int
    total_cost: int
    currency: str = "JPY"
    note: str

# ── エンドポイント ────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "CONSTRUCT-AI"}

@app.post("/estimate", response_model=EstimateResponse, dependencies=[Depends(verify_api_key)])
async def estimate(req: EstimateRequest):
    try:
        unit_price = get_unit_price(req.work_type, req.grade)
        region     = get_region(req.location)
        coeff      = region["coefficient"]
        labor_idx  = region.get("labor_index", coeff)

        base_cost     = int(unit_price * req.qty)
        adjusted_cost = int(base_cost * coeff)

        # 内訳: 材料50% / 労務35% / 諸経費15%
        material_cost = int(adjusted_cost * 0.50)
        labor_cost    = int(adjusted_cost * 0.35 * labor_idx)
        overhead      = adjusted_cost - material_cost - int(adjusted_cost * 0.35)
        total_cost    = material_cost + labor_cost + overhead

        logger.info(f"Estimate: {req.work_type} {req.qty} @ {req.location} → ¥{total_cost:,}")

        return EstimateResponse(
            work_type=req.work_type,
            qty=req.qty,
            location=req.location,
            grade=req.grade,
            unit_price=unit_price,
            regional_coefficient=round(coeff, 3),
            labor_index=round(labor_idx, 3),
            base_cost=base_cost,
            material_cost=material_cost,
            labor_cost=labor_cost,
            overhead=overhead,
            total_cost=total_cost,
            note="概算値。現地調査・詳細設計により変動します。",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Estimate error")
        raise HTTPException(status_code=500, detail=str(e))

# ── 静的ファイル配信 (frontend/) ──────────────────
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(frontend_dir / "index.html"))
else:
    @app.get("/")
    async def index_fallback():
        return {"service": "CONSTRUCT-AI", "docs": "/docs"}

# ── 起動 ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)