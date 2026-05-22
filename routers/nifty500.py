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


from fastapi import HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json

@router.get("/api/nifty500-dashboard")
async def nifty500_dashboard():
    """Return profit curve (realized only) + current total PnL, and portfolio table."""
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
            "total_realized_pnl": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "capital_available": state.get("capital_available", 0),
        })

    # Sort dates ascending
    sorted_dates = sorted(portfolio_history.keys())

    # --- 1. Build profit curve (cumulative realized PnL over time) ---
    profit_curve = []
    cumulative_realized = 0.0
    for date_str in sorted_dates:
        day_data = portfolio_history[date_str]
        # Closed PnL of the day
        realized_day = sum(pos.get("realised_pnl", 0.0) for pos in day_data.get("closed_positions", []))
        cumulative_realized += realized_day

        # Unrealised PnL from holdings on that day
        unrealised_day = sum(pos.get("unrealized_pnl", 0.0) for pos in day_data.get("holdings", []))

        total_day = cumulative_realized + unrealised_day

        profit_curve.append({
            "date": date_str,
            "realized_pnl_day": round(realized_day, 2),        # optional, keep for reference
            "cumulative_realized": round(cumulative_realized, 2),
            "unrealized_pnl": round(unrealised_day, 2),
            "total_pnl": round(total_day, 2),
        })

    # --- 2. Latest date's unrealized PnL (for total PnL) ---
    latest_date_str = sorted_dates[-1]
    latest_day_data = portfolio_history[latest_date_str]
    latest_unrealized = sum(pos.get("unrealized_pnl", 0.0) for pos in latest_day_data.get("holdings", []))
    total_realized = cumulative_realized  # after last date
    total_pnl = total_realized + latest_unrealized


    # --- 3. Portfolio holdings for last 7 days (most recent first) ---
    # --- 3. Portfolio holdings for last 7 days (most recent first) ---
    latest_date = datetime.strptime(latest_date_str, "%Y-%m-%d")
    last_7_dates = []
    for i in range(7):
        d = latest_date - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        if d_str in portfolio_history:
            last_7_dates.append(d_str)

    portfolio_table = []
    for date_str in last_7_dates:
        day_data = portfolio_history[date_str]

        # Process holdings
        holdings_list = []
        for h in day_data.get("holdings", []):
            qty = h.get("quantity", 0)
            avg_price = h.get("average_price", 0)
            cur_value = h.get("current_value", 0)
            cur_price = cur_value / qty if qty else 0.0
            u_pnl = h.get("unrealized_pnl", 0.0)
            cost = avg_price * qty
            pnl_pct = (u_pnl / cost * 100) if cost != 0 else 0.0

            holdings_list.append({
                "symbol": h.get("symbol", "").replace("NSE:", "").replace("-EQ", ""),
                "quantity": qty,
                "average_price": round(avg_price, 2),
                "current_price": round(cur_price, 2),
                "current_value": round(cur_value, 2),
                "unrealized_pnl": round(u_pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
            })

        # Process closed positions
        closed_list = []
        for c in day_data.get("closed_positions", []):
            closed_list.append({
                "symbol": c.get("symbol", "").replace("NSE:", "").replace("-EQ", ""),
                "quantity": c.get("quantity", 0),
                "entry_price": round(c.get("entry_price", 0), 2),
                "exit_price": round(c.get("exit_price", 0), 2),
                "realised_pnl": round(c.get("realised_pnl", 0), 2),
                "type": c.get("type", ""),
            })

        day_realised = sum(c.get("realised_pnl", 0) for c in day_data.get("closed_positions", []))
        day_unrealised = sum(h.get("unrealized_pnl", 0) for h in day_data.get("holdings", []))

        portfolio_table.append({
            "date": date_str,
            "holdings": holdings_list,
            "closed_positions": closed_list,
            "total_unrealized": round(day_unrealised, 2),
            "total_realized": round(day_realised, 2),
        })

    # Calculate total value of all current holdings (latest date)
    latest_holdings = portfolio_history[latest_date_str].get("holdings", [])
    total_holdings_value = round(sum(h.get("current_value", 0) for h in latest_holdings), 2)

    return JSONResponse({
        "profit_curve": profit_curve,
        "portfolio_table": portfolio_table,
        "latest_date": latest_date_str,
        "total_realized_pnl": round(total_realized, 2),
        "total_unrealized_pnl": round(latest_unrealized, 2),
        "total_pnl": round(total_pnl, 2),
        "capital_available": state.get("capital_available", 0),
        "total_holdings_value": total_holdings_value,
    })
