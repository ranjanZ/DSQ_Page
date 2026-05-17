# routers/nifty500.py
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["nifty500"])

@router.post("/api/nifty500-report")
async def nifty500_report(data: dict = Body(...)):
    if not data:
        raise HTTPException(status_code=400, detail="JSON body required")

    initial_capital = data.get("initial_capital", data.get("initialCapital", 0)) or 0
    performance = data.get("performance", [])
    portfolio = data.get("portfolio", [])

    parsed_perf = []
    if isinstance(performance, list):
        for item in performance:
            if not isinstance(item, dict):
                continue
            date = item.get("date") or item.get("Date") or item.get("dt")
            equity = item.get("equity") or item.get("value") or item.get("capital") or 0
            try:
                equity = float(equity)
            except:
                equity = 0.0
            parsed_perf.append({"date": date, "equity": equity})

    summary = {}
    if parsed_perf:
        start = parsed_perf[0]["equity"]
        end = parsed_perf[-1]["equity"]
        base = initial_capital or start or 1
        net_return = ((end - base) / base) * 100 if base else 0.0
        summary = {
            "record_count": len(parsed_perf),
            "start_equity": start,
            "end_equity": end,
            "net_return_pct": round(net_return, 2),
        }

    return JSONResponse({
        "success": True,
        "initial_capital": initial_capital,
        "portfolio": portfolio if isinstance(portfolio, list) else [],
        "performance": parsed_perf,
        "summary": summary,
    })