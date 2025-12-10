Here is the **updated API documentation with `curl` examples** added for every endpoint.

---

# **Lichess Stockfish Bot – REST API Documentation (with curl examples)**

Base URL (public through Nginx):

```
https://mazehkhor.com/bot/api/
```

All endpoints return JSON.
All `POST` requests expect JSON unless stated otherwise.

---

# **Overview**

The API enables:

* Checking bot status
* Starting or stopping the bot
* Getting or setting the Stockfish skill level

Skill level is an integer between **0 and 20**.

---

# **1. GET `/api/bot/status`**

Returns the current state of the bot.

### **curl Example**

```bash
curl https://mazehkhor.com/bot/api/bot/status
```

### **Response**

```json
{
  "ok": true,
  "running": true,
  "level": 20,
  "pid": 12345
}
```

---

# **2. POST `/api/bot/start`**

Starts the bot.
Optional JSON allows setting the skill level before launching.

---

## **Start bot (no parameters)**

### **curl Example**

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/start
```

---

## **Start bot with skill level**

### **curl Example**

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/start \
     -H "Content-Type: application/json" \
     -d '{"level": 15}'
```

### **Response**

```json
{
  "ok": true,
  "started": true,
  "running": true,
  "level": 15,
  "pid": 67890
}
```

---

# **3. POST `/api/bot/stop`**

Stops the running bot.

### **curl Example**

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/stop
```

### **Response**

```json
{
  "ok": true,
  "stopped": true,
  "running": false,
  "level": 20,
  "pid": null
}
```

---

# **4. GET `/api/bot/level`**

Returns current skill level.

### **curl Example**

```bash
curl https://mazehkhor.com/bot/api/bot/level
```

### **Response**

```json
{
  "ok": true,
  "level": 20
}
```

---

# **5. POST `/api/bot/level`**

Sets the Stockfish skill level (does **not** restart the bot).

### **curl Example**

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/level \
     -H "Content-Type: application/json" \
     -d '{"level": 5}'
```

### **Response**

```json
{
  "ok": true,
  "level": 5,
  "running": true
}
```

---

# **Error Response Format**

All errors follow this structure:

```json
{
  "ok": false,
  "error": "Description of error"
}
```

Examples:

### Invalid level

```json
{
  "ok": false,
  "error": "Invalid 'level'. Must be integer 0–20."
}
```

### Missing field

```json
{
  "ok": false,
  "error": "Missing 'level' in JSON body."
}
```

---

# **Quick Testing Cheat Sheet**

You can paste these directly into your terminal:

### Check status

```bash
curl https://mazehkhor.com/bot/api/bot/status
```

### Start bot

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/start
```

### Start with level

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/start \
     -H "Content-Type: application/json" \
     -d '{"level": 12}'
```

### Stop bot

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/stop
```

### Get level

```bash
curl https://mazehkhor.com/bot/api/bot/level
```

### Set level

```bash
curl -X POST https://mazehkhor.com/bot/api/bot/level \
     -H "Content-Type: application/json" \
     -d '{"level": 3}'
```