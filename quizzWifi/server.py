# -*- coding: utf-8 -*-
"""Білім жарысы — Wi-Fi сервері (тек Python стандартты кітапханасы).

Іске қосу:  python server.py      (немесе start.bat)
Мұғалім:    http://localhost:8000/host   (осы компьютерде)
Оқушылар:   http://<компьютер IP>:8000   (сол Wi-Fi желісінде)
"""
import json, os, random, socket, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", "8000"))
HERE = os.path.dirname(os.path.abspath(__file__))
GAME_FILE = os.path.join(HERE, "bilim-jarysy.html")

AVATARS = ["🦊", "🐼", "🐸", "🐯", "🐵", "🐨", "🐰", "🐻", "🦁", "🐙", "🦄", "🐲",
           "🐱", "🐶", "🦉", "🐢", "🐧", "🐷", "🐮", "🐔", "🦋", "🐝", "🐬", "🦖"]
COLORS = ["#A8322A", "#1F5C8C", "#4C7A35", "#6A2E4E", "#B07A1C", "#A8324F",
          "#1C7F8E", "#2E3F78", "#8A5A2B", "#3E7D6A", "#C2701C", "#2C3B63"]  # ұлттық түстер

lock = threading.Lock()
S = {"phase": "lobby", "gameId": 0, "seed": 0, "dur": 180, "startAt": 0,
     "questions": None, "players": {}, "joinCount": 0,
     "kicked": set(),   # шығарылған ойыншы id-лері (өздігінен қайта кірмеу үшін)
     "banned": {}}      # бұғатталған телефондар: ip -> {name, av}


def now_ms():
    return int(time.time() * 1000)


def lan_ips():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))  # пакет жіберілмейді, тек маршрут анықталады
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.append(info[4][0])
    except Exception:
        pass
    good = []
    for ip in ips:
        if ip.startswith(("127.", "169.254.", "192.168.56.")) or ip in good:
            continue
        good.append(ip)
    return good


def refresh_phase():
    if S["phase"] == "play" and now_ms() > S["startAt"] + S["dur"] * 1000 + 1500:
        S["phase"] = "end"


def public_players():
    t = now_ms()
    out = []
    for pid, p in S["players"].items():
        out.append({"id": pid, "name": p["name"], "av": p["av"], "color": p["color"],
                    "score": p["score"], "correct": p["correct"], "wrong": p["wrong"],
                    "hits": p["hits"], "coins": p["coins"], "x": p["x"],
                    "online": t - p["seen"] < 6000, "gameId": p["gameId"]})
    return out


def reset_scores(p):
    p.update(score=0, correct=0, wrong=0, hits=0, coins=0, x=0)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def is_local(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 500_000:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            with lock:
                refresh_phase()
                banned = [{"key": ip, "name": b["name"], "av": b["av"]} for ip, b in S["banned"].items()] if self.is_local() else []
                self.send_json({"now": now_ms(), "phase": S["phase"], "gameId": S["gameId"],
                                "seed": S["seed"], "dur": S["dur"], "startAt": S["startAt"],
                                "players": public_players(), "banned": banned})
            return
        if path == "/api/game":
            with lock:
                self.send_json({"now": now_ms(), "gameId": S["gameId"], "seed": S["seed"], "dur": S["dur"],
                                "startAt": S["startAt"], "questions": S["questions"], "phase": S["phase"]})
            return
        if path == "/api/info":
            self.send_json({"ips": lan_ips(), "port": PORT, "isHost": self.is_local()})
            return
        if path.startswith("/api/"):
            self.send_json({"error": "not found"}, 404)
            return
        if path == "/favicon.ico":
            self.send_response(204); self.end_headers(); return
        try:
            with open(GAME_FILE, "rb") as f:
                body = f.read()
        except OSError:
            self.send_json({"error": "bilim-jarysy.html табылмады"}, 500)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = self.path.split("?")[0]
        d = self.read_json()
        with lock:
            refresh_phase()
            t = now_ms()
            if path == "/api/join":
                ip = self.client_address[0]
                if ip in S["banned"] and not self.is_local():
                    return self.send_json({"error": "banned"}, 403)
                pid = str(d.get("id") or "")
                S["kicked"].discard(pid)
                name = str(d.get("name") or "").strip()[:16] or "Оқушы"
                p = S["players"].get(pid)
                if not p:
                    pid = "%08x" % random.getrandbits(32)
                    k = S["joinCount"]; S["joinCount"] += 1
                    p = {"av": AVATARS[k % len(AVATARS)], "color": COLORS[k % len(COLORS)], "gameId": -1}
                    reset_scores(p)
                    S["players"][pid] = p
                p["name"] = name
                p["seen"] = t
                p["ip"] = ip
                return self.send_json({"id": pid, "name": p["name"], "av": p["av"], "color": p["color"]})

            if path == "/api/leave":
                S["players"].pop(str(d.get("id")), None)
                return self.send_json({"ok": True})

            if path == "/api/update":
                pid = str(d.get("id"))
                if pid in S["kicked"]:
                    return self.send_json({"error": "kicked"}, 410)
                p = S["players"].get(pid)
                if not p:
                    return self.send_json({"error": "unknown"}, 404)
                p["seen"] = t
                if d.get("gameId") == S["gameId"] and S["phase"] in ("play", "end"):
                    p["gameId"] = S["gameId"]
                    for k in ("score", "correct", "wrong", "hits", "coins"):
                        try: p[k] = max(0, int(d.get(k, p[k])))
                        except Exception: pass
                    try: p["x"] = float(d.get("x", p["x"]))
                    except Exception: pass
                ranked = sorted([q for q in S["players"].values() if q["gameId"] == S["gameId"]],
                                key=lambda q: -q["score"])
                rank = next((i + 1 for i, q in enumerate(ranked) if q is p), 0)
                return self.send_json({"now": t, "phase": S["phase"], "gameId": S["gameId"],
                                       "startAt": S["startAt"], "dur": S["dur"],
                                       "rank": rank, "total": len(ranked)})

            # ---- тек мұғалім компьютерінен ----
            if not self.is_local():
                return self.send_json({"error": "Бұл әрекетті тек мұғалім компьютері жасай алады"}, 403)
            if path == "/api/start":
                S["gameId"] += 1
                S["seed"] = random.getrandbits(30)
                S["dur"] = max(30, min(900, int(d.get("dur") or 180)))
                qs = d.get("questions")
                S["questions"] = qs if isinstance(qs, list) and qs else None
                S["startAt"] = t + 5000
                S["phase"] = "play"
                for p in S["players"].values():
                    reset_scores(p)
                return self.send_json({"ok": True, "gameId": S["gameId"]})
            if path == "/api/stop":
                if S["phase"] == "play":
                    S["dur"] = max(0, (t - S["startAt"]) // 1000)
                    S["phase"] = "end"
                return self.send_json({"ok": True})
            if path == "/api/reset":
                S["phase"] = "lobby"
                S["players"] = {k: v for k, v in S["players"].items() if t - v["seen"] < 6000}
                for p in S["players"].values():
                    reset_scores(p)
                return self.send_json({"ok": True})
            if path == "/api/kick":
                pid = str(d.get("id"))
                p = S["players"].pop(pid, None)
                S["kicked"].add(pid)
                if d.get("ban") and p and p.get("ip"):
                    S["banned"][p["ip"]] = {"name": p["name"], "av": p["av"]}
                return self.send_json({"ok": True})
            if path == "/api/unban":
                S["banned"].pop(str(d.get("key")), None)
                return self.send_json({"ok": True})
        self.send_json({"error": "not found"}, 404)


class Server(ThreadingHTTPServer):
    # Windows-та SO_REUSEADDR екі серверге бір портты бөлісуге мүмкіндік береді — оны өшіреміз
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        srv = Server(("0.0.0.0", PORT), H)
    except OSError:
        print("Port %d is busy - server is probably already running." % PORT)
        print("Open: http://localhost:%d/host" % PORT)
        return
    ips = lan_ips()
    print("=" * 56)
    print("  Білім жарысы — сервер іске қосылды")
    print("=" * 56)
    print("  Мұғалім экраны:  http://localhost:%d/host" % PORT)
    for ip in ips:
        print("  Оқушылар кіреді: http://%s:%d" % (ip, PORT))
    if not ips:
        print("  (Wi-Fi IP табылмады — компьютер желіге қосылғанын тексеріңіз)")
    print("  Тоқтату: осы терезені жабыңыз немесе Ctrl+C")
    print("=" * 56)
    sys.stdout.flush()
    if "--open" in sys.argv:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:%d/host" % PORT)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
