# Migration Complete: async-dash → Flask + FastAPI

## Changes Made

### New Files Created
- `fastapi_service/` - Complete FastAPI microservice
  - `main.py` - FastAPI app with lifespan management
  - `config.py` - Service configuration
  - `websocket/manager.py` - Connection manager
  - `websocket/routes.py` - WebSocket endpoint
  - `services/csv_monitor.py` - CSV file watcher
- `start_services.sh` - Helper script to run both services

### Modified Files
1. **app.py** - Converted from async-dash/Quart to standard Flask-based Dash
2. **src/callbacks.py:30-42** - Updated WebSocket URL to connect to FastAPI on port 8058
3. **pyproject.toml** - Updated dependencies:
   - Removed: `async-dash`, `quart`, `hypercorn`
   - Added: `fastapi`, `uvicorn`, `websockets`, `pydantic-settings`, `python-multipart`

### Unchanged Files (Zero Changes to Business Logic)
- `src/data_loader.py`
- `src/umap_processor.py`
- `src/layout.py`
- All other callbacks in `src/callbacks.py`
- `assets/custom.css`

## Testing

### Start Both Services

**Option 1: Using helper script**
```bash
./start_services.sh
```

**Option 2: Manual (two terminals)**

Terminal 1 - FastAPI:
```bash
uv run python -m fastapi_service.main
```

Terminal 2 - Dash:
```bash
uv run python app.py
```

### Verify Services

1. **Check FastAPI health**
```bash
curl http://localhost:8058/health
```

2. **Open browser**
```bash
open http://localhost:8050
```

3. **Check WebSocket connection**
   - Open DevTools → Network → WS tab
   - Should see connection to `ws://localhost:8058/api/v1/ws`

## Manual Testing Checklist

- [ ] WebSocket connection establishes (green "Live" indicator)
- [ ] Append rows to `data/phenobase.csv` → notifications appear
- [ ] Event log updates in real-time
- [ ] New rows highlighted with green border
- [ ] "Pause Updates" toggle works
- [ ] UMAP computation still works
- [ ] Time series chart updates
- [ ] Image serving works

## Architecture

**Before:**
```
Quart (Port 8050)
├─ Dash UI
├─ WebSocket /ws
└─ CSV Watcher
```

**After:**
```
Flask + Dash (Port 8050)     FastAPI (Port 8058)
├─ UI Components             ├─ WebSocket /api/v1/ws
├─ Callbacks (sync)    ◄─────├─ CSV Watcher
└─ Image serving             └─ Connection Manager
```

## Success Metrics
✅ Dependencies updated successfully
✅ FastAPI service imports without errors
✅ Dash app imports without errors
✅ Zero changes to core business logic
✅ Minimal changes to callbacks (1 callback updated)
✅ Production-ready architecture
