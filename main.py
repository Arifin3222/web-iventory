# =================================================================
#  🟢 ARIFINHUB - PUBLIC SERVER (REPLIT EDITION)
#  Gratis & Open Source. Tanpa Config.json. Tanpa Login.
# =================================================================

from flask import Flask, request, jsonify, render_template_string
from waitress import serve
import secrets
import logging

# --- PENGATURAN (BISA DIEDIT) ---
APP_NAME = "ArifinHub Monitor"
PORT = 8080  # Port standar Replit

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# DATA PENYIMPANAN SEMENTARA (RAM)
# Data akan hilang jika Replit direstart (Sifat Replit memang begitu)
public_data = {} 

# --- FUNGSI LOGIKA (SORTING & STATS) ---
def sort_inventory_by_rarity(items):
    rarity_priority = { "SECRET": 1, "MYTHICAL": 2, "MYTHIC": 2, "LEGENDARY": 3, "EPIC": 4, "RARE": 5, "UNCOMMON": 6, "COMMON": 7 }
    def get_sort_key(item):
        rarity_rank = rarity_priority.get(str(item.get('Rarity', 'COMMON')).upper().strip(), 99)
        weight_val = 0.0
        try:
            w_str = str(item.get('Weight', '0')).lower().replace('kg', '').strip()
            if w_str and w_str != 'none': weight_val = float(w_str)
        except: weight_val = 0.0
        return (rarity_rank, -weight_val)
    items.sort(key=get_sort_key)
    return items

def get_stats(items):
    stats = { "SECRET": 0, "MYTHICAL": 0, "LEGENDARY": 0, "EPIC": 0, "RARE": 0, "UNCOMMON": 0, "COMMON": 0, "TOTAL_VALUE": 0, "MUTATED": 0 }
    for item in items:
        r = str(item.get('Rarity', 'COMMON')).upper().strip()
        if "MYTHIC" in r: r = "MYTHICAL"
        if r in stats: stats[r] += 1
        if item.get('Mutation'): stats['MUTATED'] += 1
        try:
            if item.get('RawPrice'): stats['TOTAL_VALUE'] += int(item['RawPrice'])
            elif item.get('Price'):
                clean_price = str(item['Price']).replace(',', '')
                if clean_price.isdigit(): stats['TOTAL_VALUE'] += int(clean_price)
        except: pass
    stats['TOTAL_VALUE'] = "{:,}".format(stats['TOTAL_VALUE'])
    return stats

# --- TAMPILAN DASHBOARD (HTML) ---
dashboard_html = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>""" + APP_NAME + """</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root { --bg: #0f0f13; --card: #1a1a20; --text: #fff; --accent: #00e4ff; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; padding: 20px; }
        .lucide { vertical-align: middle; margin-right: 4px; }
        
        .top-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .brand { font-size: 24px; color: var(--accent); font-weight: bold; display: flex; align-items: center; gap: 10px; }
        .account-selector { background: #111; color: white; border: 1px solid #00e4ff; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer; font-family: 'Rajdhani'; font-size: 16px; min-width: 200px; }
        
        /* LIVE MONITOR */
        .live-monitor { background: rgba(0, 228, 255, 0.05); border: 1px solid #00e4ff; border-radius: 8px; padding: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }
        .live-info { display: flex; flex-direction: column; gap: 5px; }
        .live-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        .live-data { font-size: 18px; font-weight: bold; color: white; display: flex; align-items: center; gap: 8px;}
        
        .hp-container { width: 150px; height: 10px; background: #333; border-radius: 5px; overflow: hidden; position: relative; }
        .hp-fill { height: 100%; background: #00FF00; width: 0%; transition: width 0.5s ease-in-out; }
        .hp-text { font-size: 14px; font-weight: bold; color: #00FF00; }

        .stats-container { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 25px; background: rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; border: 1px solid #333; }
        .stat-item { font-size: 14px; font-weight: bold; padding: 5px 12px; border-radius: 4px; background: #111; border: 1px solid #333; text-transform: uppercase; display: flex; align-items: center; }
        .total-value { color: #00ff00; border-color: #00ff00; box-shadow: 0 0 10px rgba(0,255,0,0.2); }
        
        .tab-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; }
        .tab-btn { background: rgba(255,255,255,0.05); color: #888; border: 1px solid #333; padding: 10px 30px; border-radius: 4px; cursor: pointer; font-size: 18px; font-weight: bold; transition: 0.3s; margin-right: 10px;}
        .tab-btn.active { background: rgba(0,228,255,0.15); color: var(--accent); border-color: var(--accent); }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 15px; }
        .content-section { display: none; }
        .content-section.active { display: grid; }
        
        .card { background: var(--card); border: 1px solid #333; border-radius: 8px; display: flex; flex-direction: column; align-items: center; overflow: hidden; transition: 0.2s; position: relative; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .card img { width: 90px; height: 90px; object-fit: contain; margin-top: 10px; }
        .rarity-badge { background: white; color: black; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; position: absolute; top:5px; left:5px; }
        .card-body { padding: 10px; text-align: center; width: 100%; box-sizing: border-box; }
        .info-tag { font-size: 12px; color: #ccc; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; border: 1px solid #444; margin-top: 5px; display: inline-flex; align-items: center; gap: 4px; justify-content: center;}
        
        .waiting { grid-column: 1/-1; text-align: center; margin-top: 50px; color: #555; font-size: 18px; font-style: italic; }
        .no-user { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
        
        /* Animasi Mutasi */
        .mutation-active { color: #FF00FF; font-weight: bold; animation: pulse 1.5s infinite alternate; margin-top: 5px; font-size: 11px; text-shadow: 0 0 5px #FF00FF; display: flex; align-items: center; justify-content: center; gap: 4px;}
        @keyframes pulse { 0% { opacity: 0.7; transform: scale(0.98); } 100% { opacity: 1; transform: scale(1.02); } }
    </style>
    <script>
        // --- JAVASCRIPT FRONTEND ---
        async function updateDashboard() {
            const urlParams = new URLSearchParams(window.location.search);
            const selectedUser = urlParams.get('user'); 
            try {
                const res = await fetch('/api/public_data');
                if (!res.ok) return;
                const data = await res.json();
                const users = data.users;
                
                const select = document.getElementById('user-select');
                const currentVal = select.value || selectedUser || (users.length > 0 ? users[0] : "");
                
                select.innerHTML = "";
                if (users.length === 0) {
                    select.innerHTML = "<option>Menunggu Pemain...</option>";
                    document.getElementById('main-content').style.display = 'none';
                    document.getElementById('waiting-screen').style.display = 'block';
                    return;
                } else {
                    document.getElementById('main-content').style.display = 'block';
                    document.getElementById('waiting-screen').style.display = 'none';
                }

                users.forEach(u => {
                    const opt = document.createElement('option');
                    opt.value = u;
                    opt.text = "🎮 " + u;
                    opt.selected = (u === currentVal);
                    select.appendChild(opt);
                });

                let targetUser = selectedUser && data.data[selectedUser] ? selectedUser : (currentVal || users[0]);
                if(targetUser && data.data[targetUser]) renderUserData(data.data[targetUser]);

            } catch (e) { console.error(e); }
        }

        function renderUserData(userData) {
            // Live Stats
            const ls = userData.stats || {};
            document.getElementById('live-hp-text').innerText = Math.floor(ls.Health || 0) + " HP";
            document.getElementById('live-hp-bar').style.width = ((ls.Health / ls.MaxHealth) * 100) + "%";
            document.getElementById('live-status').innerText = ls.Action || "Idle";
            document.getElementById('live-pos').innerText = ls.Position || "Unknown";
            document.getElementById('live-money').innerText = "$" + (ls.Money || 0);

            // Total Value
            let total = 0;
            userData.fishes.forEach(f => {
                let p = typeof f.RawPrice === 'number' ? f.RawPrice : parseInt(f.Price.replace(/,/g, '')) || 0;
                total += p;
            });
            document.getElementById('stat-total').innerText = "$" + total.toLocaleString();

            // Counts
            document.getElementById('btn-fish').innerHTML = `<i data-lucide="fish"></i> Ikan (${userData.fishes.length})`;
            document.getElementById('btn-item').innerHTML = `<i data-lucide="package"></i> Item (${userData.items.length})`;

            // Render Cards
            renderCards('fish-section', userData.fishes);
            renderCards('item-section', userData.items);
            lucide.createIcons();
        }

        function renderCards(containerId, list) {
            let html = "";
            if (!list || list.length === 0) {
                html = '<div class="waiting">Tas Kosong / Belum Sync</div>';
            } else {
                list.forEach(i => {
                    let mut = i.Mutation ? `<span class="mutation-active"><i data-lucide="sparkles"></i> ${i.Mutation}</span>` : '';
                    let prc = i.Price ? `<div style="color:#0f0; font-weight:bold;">$${i.Price}</div>` : '';
                    let inf = i.Weight ? `<i data-lucide="scale"></i> ${i.Weight}` : `x${i.Amount}`;
                    
                    html += `
                    <div class="card" style="border-color: ${i.Color}; box-shadow: 0 0 5px ${i.Color}40;">
                        <div style="padding:10px; display:flex; justify-content:center; background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0) 70%);">
                            <div class="rarity-badge" style="background: ${i.Color};">${i.Rarity}</div>
                            <img src="${i.Image}" style="width:90px;height:90px;object-fit:contain;">
                        </div>
                        <div class="card-body">
                            <div style="font-weight:bold; font-size:14px; margin-bottom:5px;">${i.Name}</div>
                            <div class="info-tag">${inf}</div>
                            ${prc} ${mut}
                        </div>
                    </div>`;
                });
            }
            document.getElementById(containerId).innerHTML = html;
        }

        function changeUser(sel) { window.location.href = "/?user=" + sel.value; }
        function openTab(t) {
            document.querySelectorAll('.content-section').forEach(e=>e.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(e=>e.classList.remove('active'));
            document.getElementById(t+'-section').classList.add('active');
            document.getElementById('btn-'+t).classList.add('active');
        }

        setInterval(updateDashboard, 2000); 
        document.addEventListener("DOMContentLoaded", () => { openTab('fish'); lucide.createIcons(); updateDashboard(); });
    </script>
</head>
<body>
    <div class="top-bar">
        <div class="brand"><i data-lucide="monitor"></i> """ + APP_NAME + """</div>
        <select id="user-select" class="account-selector" onchange="changeUser(this)">
            <option>Loading...</option>
        </select>
    </div>

    <div id="waiting-screen" class="no-user" style="display:none;">
        <h2 style="color:#555;"><i data-lucide="loader"></i> Menunggu Data...</h2>
        <p style="color:#333;">Jalankan script di Roblox untuk memunculkan data.</p>
    </div>

    <div id="main-content" style="display:none;">
        <div class="live-monitor">
            <div class="live-info"><span class="live-label">Status</span><div class="live-data" style="color:#0f0;" id="live-status">...</div></div>
            <div class="live-info"><span class="live-label">Health</span><div class="live-data"><div class="hp-container"><div id="live-hp-bar" class="hp-fill"></div></div><span id="live-hp-text" class="hp-text"></span></div></div>
            <div class="live-info"><span class="live-label">Money</span><div class="live-data" style="color:gold;" id="live-money">...</div></div>
            <div class="live-info"><span class="live-label">Position</span><div class="live-data" style="font-size:14px;" id="live-pos">...</div></div>
        </div>
        <div style="margin-bottom:20px; text-align:center; font-size:20px; color:#0f0; font-weight:bold;">
            <i data-lucide="dollar-sign"></i> TOTAL VALUE: <span id="stat-total">0</span>
        </div>
        <div class="tab-container" style="display:flex; justify-content:center; margin-bottom:20px;">
            <button id="btn-fish" class="tab-btn active" onclick="openTab('fish')">Ikan</button>
            <button id="btn-item" class="tab-btn" onclick="openTab('item')">Item</button>
        </div>
        <div id="fish-section" class="content-section grid active"></div>
        <div id="item-section" class="content-section grid"></div>
    </div>
</body>
</html>
"""

# --- ROUTE HANDLING ---
@app.route('/')
def index(): return render_template_string(dashboard_html)

@app.route('/api/public_data')
def get_public_data(): return jsonify({ "users": list(public_data.keys()), "data": public_data })

@app.route('/update', methods=['POST'])
def update_data():
    try:
        data = request.json
        user = data.get('Username')
        inv_data = data.get('Data', [])
        stats = data.get('Stats', {})
        fishes = [x for x in inv_data if x.get('Type') == 'Fish']
        items = [x for x in inv_data if x.get('Type') != 'Fish']
        public_data[user] = {
            "fishes": sort_inventory_by_rarity(fishes),
            "items": sort_inventory_by_rarity(items),
            "stats": stats
        }
        return jsonify({"status": "ok"})
    except: return jsonify({"error": "fail"}), 500

# --- START SERVER (REPLIT) ---
if __name__ == '__main__':
    print("🚀 SERVER STARTING...")
    serve(app, host='0.0.0.0', port=PORT)
