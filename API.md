* All endpoints
* Linux (real curl) examples
* PowerShell-compatible examples
* Authentication notes
* The new endpoints you added (logs, restart, current game, stats)

Here is the full updated **API.md** — ready to paste into your repository.

---

# **Lichess Stockfish Bot – REST API Documentation**

Base URL (via Nginx):

```
https://mazehkhor.com/bot/api/
```

All endpoints return JSON.
Authentication is required using an API key.

---

# **Authentication**

Every API request must include the header:

```
X-API-Key: <your_key_here>
```

If missing or invalid, the API returns:

```json
{
  "ok": false,
  "error": "Unauthorized"
}
```

---

# **Two Ways to Call the API**

## ✅ Linux / macOS (real curl)

Use:

```bash
curl -H "X-API-Key: YOUR_KEY"
```

## ✅ Windows PowerShell

PowerShell does **not** support curl-style `-H` syntax.
Use:

```powershell
curl -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

If you want Linux-style curl inside PowerShell, use:

```powershell
curl.exe -H "X-API-Key: YOUR_KEY"
```

---

# ----------------------------------------------

# **1. BOT STATUS**

# ----------------------------------------------

## **GET `/bot/api/bot/status`**

Returns bot process status.

### 🟦 **Linux / macOS**

```bash
curl -X GET "https://mazehkhor.com/bot/api/bot/status" \
     -H "X-API-Key: YOUR_KEY"
```

### 🟥 **PowerShell**

```powershell
curl "https://mazehkhor.com/bot/api/bot/status" `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

### Example response

```json
{
  "ok": true,
  "running": true,
  "level": 20,
  "pid": 12345
}
```

---

# ----------------------------------------------

# **2. START BOT**

# ----------------------------------------------

## **POST `/bot/api/bot/start`**

### 🟦 Linux / macOS

```bash
curl -X POST "https://mazehkhor.com/bot/api/bot/start" \
     -H "X-API-Key: YOUR_KEY"
```

### Start with level

```bash
curl -X POST "https://mazehkhor.com/bot/api/bot/start" \
     -H "X-API-Key: YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"level": 12}'
```

### 🟥 PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/start" `
     -Method POST `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

### Example response

```json
{
  "ok": true,
  "started": true,
  "running": true,
  "level": 12,
  "pid": 67890
}
```

---

# ----------------------------------------------

# **3. STOP BOT**

# ----------------------------------------------

## **POST `/bot/api/bot/stop`**

### 🟦 Linux / macOS

```bash
curl -X POST "https://mazehkhor.com/bot/api/bot/stop" \
     -H "X-API-Key: YOUR_KEY"
```

### 🟥 PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/stop" `
     -Method POST `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

---

# ----------------------------------------------

# **4. SET / GET LEVEL**

# ----------------------------------------------

## **GET `/bot/api/bot/level`**

### Linux

```bash
curl https://mazehkhor.com/bot/api/bot/level \
     -H "X-API-Key: YOUR_KEY"
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/level" `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

---

## **POST `/bot/api/bot/level`**

### Linux

```bash
curl -X POST "https://mazehkhor.com/bot/api/bot/level" \
     -H "X-API-Key: YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"level": 5}'
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/level" `
     -Method POST `
     -Headers @{ "X-API-Key" = "YOUR_KEY"; "Content-Type" = "application/json" } `
     -Body '{"level": 5}'
```

---

# ----------------------------------------------

# **5. RESTART BOT (NEW)**

# ----------------------------------------------

## **POST `/bot/api/bot/restart`**

### Linux

```bash
curl -X POST "https://mazehkhor.com/bot/api/bot/restart" \
     -H "X-API-Key: YOUR_KEY"
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/restart" `
     -Method POST `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

---

# ----------------------------------------------

# **6. GET RECENT LOGS (NEW)**

# ----------------------------------------------

## **GET `/bot/api/logs/recent`**

Returns last **200 lines** from app.log.

### Linux

```bash
curl "https://mazehkhor.com/bot/api/logs/recent" \
     -H "X-API-Key: YOUR_KEY"
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/logs/recent" `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

---

# ----------------------------------------------

# **7. GET CURRENT GAME (NEW)**

# ----------------------------------------------

## **GET `/bot/api/bot/current_game`**

Returns current game status & last move from `bot_state.json`.

### Linux

```bash
curl "https://mazehkhor.com/bot/api/bot/current_game" \
     -H "X-API-Key: YOUR_KEY"
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/current_game" `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

### Example response

```json
{
  "ok": true,
  "running": true,
  "in_game": true,
  "state": {
    "status": "playing",
    "game_id": "abc123",
    "color": "black",
    "last_move": "e7e5",
    "opponent": "Opponent123"
  }
}
```

---

# ----------------------------------------------

# **8. BOT STATISTICS (NEW)**

# ----------------------------------------------

## **GET `/bot/api/bot/stats`**

Returns:

* total games
* ratings (bullet / blitz / rapid)
* recent performance (wins, losses, draws)
* details of last N games

### Linux

```bash
curl "https://mazehkhor.com/bot/api/bot/stats" \
     -H "X-API-Key: YOUR_KEY"
```

### PowerShell

```powershell
curl "https://mazehkhor.com/bot/api/bot/stats" `
     -Headers @{ "X-API-Key" = "YOUR_KEY" }
```

---

# **Error Format**

All errors follow this format:

```json
{
  "ok": false,
  "error": "Error message"
}
```