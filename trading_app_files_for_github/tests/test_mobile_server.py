"""
Test suite for AlphaTrader Mobile Server API endpoints & safety features.
"""

import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_api_status():
    """Verify status endpoint provides required mobile dashboard metrics."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "portfolio_value" in data
    assert "cash_balance" in data
    assert "net_pnl" in data
    assert "status" in data
    assert "loss_limit_used_pct" in data
    assert "daily_loss_limit_pct" in data


def test_pin_verification():
    """Verify office security PIN protection."""
    # Correct PIN
    ok_resp = client.post("/api/verify-pin", json={"pin": "1234"})
    assert ok_resp.status_code == 200
    assert ok_resp.json()["authenticated"] is True

    # Incorrect PIN
    bad_resp = client.post("/api/verify-pin", json={"pin": "9999"})
    assert bad_resp.status_code == 401


def test_watchlist_screener():
    """Verify watchlist screener returns confluence scores."""
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    first = items[0]
    assert "symbol" in first
    assert "score" in first
    assert "trend" in first


def test_simulation_trade():
    """Verify that on-demand 3-second simulation runs and records trade."""
    response = client.post("/api/simulation/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Check that trade appears in history
    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    trades = hist_resp.json()
    assert len(trades) >= 1
    assert trades[0]["symbol"] == "INFY.NS"


def test_emergency_kill_switch():
    """Verify emergency kill switch stops bot and clears open positions."""
    response = client.post("/api/kill-switch")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify positions are 0
    pos_resp = client.get("/api/positions")
    assert pos_resp.status_code == 200
    assert len(pos_resp.json()) == 0

    # Verify bot state
    stat_resp = client.get("/api/status")
    assert stat_resp.json()["status"] == "KILL_SWITCH_ACTIVE"


def test_bot_toggle():
    """Verify start and pause controls."""
    pause_resp = client.post("/api/bot/pause")
    assert pause_resp.status_code == 200
    assert client.get("/api/status").json()["status"] == "PAUSED"

    start_resp = client.post("/api/bot/start")
    assert start_resp.status_code == 200
    assert client.get("/api/status").json()["status"] == "RUNNING"
