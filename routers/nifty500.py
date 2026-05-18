# routers/nifty500.py
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["nifty500"])

# Path to your permanent trading state file
TRADING_STATE_FILE = Path("/home/zhedge/focus/DSQ_Nifty500Scanner/data/trading_state/permanent.json")

@router.get("/api/nifty500-dashboard")
async def nifty500_dashboard():
    """Read permanent.json and return profit curves + portfolio table data."""
    if not TRADING_STATE_FILE.exists():
        raise HTTPException(status_code=404, detail="Trading state file not found. Make sure the scanner has run.")

    try:
        with open(TRADING_STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse trading state file: {str(e)}")

    portfolio_history = state.get("portfolio_history", {})
    if not portfolio_history:
        return JSONResponse({
            "profit_curve": [],
            "portfolio_table": [],
            "latest_date": None,
            "total_pnl": state.get("total_pnl", 0),
            "capital_available": state.get("capital_available", 0),
        })





    # Sort dates
    sorted_dates = sorted(portfolio_history.keys())  # ISO date strings like "2026-05-13"

    # 1. Profit curve data (daily sums)
    # 1. Profit curve data (cumulative realized + daily unrealized)
    profit_curve = []
    cumulative_realized = 0.0
    for date_str in sorted_dates:
        day_data = portfolio_history[date_str]
        realized_day = sum(pos.get("realised_pnl", 0.0) for pos in day_data.get("closed_positions", []))
        cumulative_realized += realized_day
        unrealized_day = sum(pos.get("unrealized_pnl", 0.0) for pos in day_data.get("holdings", []))
        total = cumulative_realized + unrealized_day
        profit_curve.append({
            "date": date_str,
            "realized_pnl": round(realized_day, 2),
            "unrealized_pnl": round(unrealized_day, 2),
            "total_pnl": round(total, 2),
            "cumulative_realized": round(cumulative_realized, 2)   # optional, for clarity
        })

    # 2. Portfolio holdings for the last 7 days (from the latest date backward)
    latest_date_str = sorted_dates[-1]
    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
    last_7_dates = []
    for i in range(7):
        d = latest_date - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        if d_str in portfolio_history:
            last_7_dates.append(d_str)

    portfolio_table = []
    for date_str in last_7_dates:  # show most recent first
        day_data = portfolio_history[date_str]
        holdings_list = []
        for holding in day_data.get("holdings", []):
            holdings_list.append({
                "symbol": holding.get("symbol", "").replace("NSE:", "").replace("-EQ", ""),
                "quantity": holding.get("quantity", 0),
                "average_price": round(holding.get("average_price", 0), 2),
                "current_value": round(holding.get("current_value", 0), 2),
                "unrealized_pnl": round(holding.get("unrealized_pnl", 0), 2),
            })
        portfolio_table.append({
            "date": date_str,
            "holdings": holdings_list,
            "total_unrealized": round(sum(h.get("unrealized_pnl", 0) for h in holdings_list), 2)
        })

    return JSONResponse({
        "profit_curve": profit_curve,
        "portfolio_table": portfolio_table,
        "latest_date": latest_date_str,
        "total_pnl": state.get("total_pnl", 0),
        "capital_available": state.get("capital_available", 0),
    })