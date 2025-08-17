from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 'fallback-secret-key-change-in-production')

# Production configuration
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
else:
    app.config['DEBUG'] = True

# Party list
PARTIES = [
    "বাংলাদেশ জাতীয়তাবাদী দল - বি.এন.পি",
    "বাংলাদেশ আওয়ামী লীগ",
    "জাতীয় নাগরিক পার্টি - এনসিপি",
    "বাংলাদেশ জামায়াতে ইসলামী",
    "জাতীয় পার্টি"
]

# Meme URLs for different rankings
RANKING_MEMES = {
    1: "https://i.imgflip.com/2/1bij.jpg",  # Success Kid
    2: "https://i.imgflip.com/2/2fm6x.jpg",  # Disaster Girl
    3: "https://i.imgflip.com/2/5c7lwq.jpg",  # This is Fine
    4: "https://i.imgflip.com/2/1o00in.jpg",  # Sad Pablo Escobar
    5: "https://i.imgflip.com/2/1g8my4.jpg"  # Crying Cat
}


def init_db():
    """Initialize the database"""
    db_path = os.environ.get('DATABASE_URL', 'voting.db')
    if db_path.startswith('postgres://'):
        db_path = db_path.replace('postgres://', 'postgresql://', 1)

    # For SQLite (local/free hosting)
    if not db_path.startswith('postgresql://'):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create votes table
        c.execute('''CREATE TABLE IF NOT EXISTS votes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      party TEXT NOT NULL,
                      ip_address TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        # Create voters table to track IPs
        c.execute('''CREATE TABLE IF NOT EXISTS voters
                     (ip_address TEXT PRIMARY KEY,
                      voted_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

        conn.commit()
        conn.close()


def get_db_connection():
    """Get database connection"""
    db_path = os.environ.get('DATABASE_URL', 'voting.db')
    return sqlite3.connect(db_path)


def has_voted(ip_address):
    """Check if an IP address has already voted"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM voters WHERE ip_address = ?", (ip_address,))
    result = c.fetchone()
    conn.close()
    return result is not None


def cast_vote(party, ip_address):
    """Cast a vote and record the IP"""
    conn = get_db_connection()
    c = conn.cursor()

    # Insert vote
    c.execute("INSERT INTO votes (party, ip_address) VALUES (?, ?)",
              (party, ip_address))

    # Record IP as having voted
    c.execute("INSERT INTO voters (ip_address) VALUES (?)", (ip_address,))

    conn.commit()
    conn.close()


def get_vote_counts():
    """Get current vote counts for all parties"""
    conn = get_db_connection()
    c = conn.cursor()

    vote_counts = {}
    for party in PARTIES:
        c.execute("SELECT COUNT(*) FROM votes WHERE party = ?", (party,))
        count = c.fetchone()[0]
        vote_counts[party] = count

    conn.close()
    return vote_counts


def get_rankings():
    """Get parties ranked by vote count"""
    vote_counts = get_vote_counts()
    sorted_parties = sorted(vote_counts.items(),
                            key=lambda x: x[1], reverse=True)

    rankings = []
    for i, (party, votes) in enumerate(sorted_parties, 1):
        rankings.append({
            'rank': i,
            'party': party,
            'votes': votes,
            'meme': RANKING_MEMES.get(i, RANKING_MEMES[5])
        })

    return rankings


@app.route('/')
def index():
    """Main voting page"""
    # Better IP detection for production
    client_ip = request.headers.get('X-Forwarded-For',
                                    request.headers.get('X-Real-IP',
                                                        request.environ.get('HTTP_X_FORWARDED_FOR',
                                                                            request.remote_addr)))

    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    if has_voted(client_ip):
        return redirect(url_for('results'))

    return render_template('index.html', parties=PARTIES)


@app.route('/vote', methods=['POST'])
def vote():
    """Handle vote submission"""
    # Better IP detection for production
    client_ip = request.headers.get('X-Forwarded-For',
                                    request.headers.get('X-Real-IP',
                                                        request.environ.get('HTTP_X_FORWARDED_FOR',
                                                                            request.remote_addr)))

    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    if has_voted(client_ip):
        return jsonify({'success': False, 'message': 'আপনি ইতিমধ্যে ভোট দিয়েছেন!'})

    party = request.json.get('party')
    if party not in PARTIES:
        return jsonify({'success': False, 'message': 'ভুল দল নির্বাচন!'})

    try:
        cast_vote(party, client_ip)
        return jsonify({'success': True, 'message': 'আপনার ভোট সফলভাবে গ্রহণ করা হয়েছে!'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'ভোট দিতে সমস্যা হয়েছে!'})


@app.route('/results')
def results():
    """Results page"""
    # Better IP detection for production
    client_ip = request.headers.get('X-Forwarded-For',
                                    request.headers.get('X-Real-IP',
                                                        request.environ.get('HTTP_X_FORWARDED_FOR',
                                                                            request.remote_addr)))

    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    has_user_voted = has_voted(client_ip)
    rankings = get_rankings()
    return render_template('results.html', rankings=rankings, has_voted=has_user_voted)


@app.route('/api/results')
def api_results():
    """API endpoint for getting current results"""
    return jsonify(get_rankings())


if __name__ == '__main__':
    init_db()
    # Production ready configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'

    app.run(host='0.0.0.0', port=port, debug=debug)

# HTML Templates (save these as separate files in templates/ folder)

# templates/base.html
BASE_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}বাংলাদেশ জনমত সংগ্রহ{% endblock %}</title>
    
    <!-- Open Graph Meta Tags for Facebook/Social Media -->
    <meta property="og:title" content="🗳️ বাংলাদেশ জনমত সংগ্রহ - আপনার মতামত দিন!" />
    <meta property="og:description" content="🔥 এখনই ভোট দিন! দেখুন কোন দল এগিয়ে আছে। রিয়েল টাইম ফলাফল দেখুন এবং আপনার পছন্দের দলকে সমর্থন করুন। ১ ক্লিকেই ভোট দিন!" />
    <meta property="og:image" content="https://i.imgur.com/8YzW5pK.png" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta property="og:url" content="{{ request.url }}" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="বাংলাদেশ জনমত সংগ্রহ" />
    
    <!-- Twitter Card Meta Tags -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="🗳️ বাংলাদেশ জনমত সংগ্রহ - আপনার ভোট দিন!" />
    <meta name="twitter:description" content="🔥 এখনই ভোট দিন! রিয়েল টাইম ফলাফল দেখুন। কোন দল জিতছে?" />
    <meta name="twitter:image" content="https://i.imgur.com/8YzW5pK.png" />
    
    <!-- Additional Meta Tags -->
    <meta name="description" content="বাংলাদেশের রাজনৈতিক দলগুলোর জনপ্রিয়তা জানুন। রিয়েল টাইম ভোটিং এবং ফলাফল দেখুন।" />
    <meta name="keywords" content="বাংলাদেশ, নির্বাচন, ভোট, জনমত, রাজনীতি, আওয়ামী লীগ, বিএনপি, জামায়াত" />
    
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }
        .party-button {
            display: block;
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 16px;
        }
        .party-button:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .results-card {
            background: rgba(255, 255, 255, 0.1);
            margin: 15px 0;
            padding: 20px;
            border-radius: 15px;
            border-left: 5px solid #fff;
            transition: all 0.3s ease;
        }
        .results-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        .rank-1 { border-left-color: #FFD700; background: rgba(255, 215, 0, 0.1); }
        .rank-2 { border-left-color: #C0C0C0; background: rgba(192, 192, 192, 0.1); }
        .rank-3 { border-left-color: #CD7F32; background: rgba(205, 127, 50, 0.1); }
        .rank-4 { border-left-color: #FF6B6B; background: rgba(255, 107, 107, 0.1); }
        .rank-5 { border-left-color: #6C5CE7; background: rgba(108, 92, 231, 0.1); }
        
        .meme-img {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: 10px;
            float: right;
            margin-left: 20px;
        }
        .vote-count {
            font-size: 2em;
            font-weight: bold;
            color: #FFD700;
        }
        .back-btn {
            display: inline-block;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
            transition: all 0.3s ease;
        }
        .back-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .success-message {
            background: rgba(76, 175, 80, 0.3);
            border: 2px solid #4CAF50;
            color: #E8F5E8;
            animation: successPulse 3s ease-in-out;
        }
        @keyframes successPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7); }
            50% { box-shadow: 0 0 0 15px rgba(76, 175, 80, 0); }
        }
        .loading {
            text-align: center;
            padding: 20px;
        }
        .pulse {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# templates/index.html
INDEX_HTML = """
{% extends "base.html" %}

{% block title %}🗳️ বাংলাদেশ জনমত সংগ্রহ - ভোট দিন!{% endblock %}

{% block content %}
<div style="text-align: center; margin-bottom: 30px;">
    <h1>🗳️ বাংলাদেশ জনমত সংগ্রহ</h1>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 20px; border-radius: 15px; margin: 20px 0;">
        <h2 style="color: #FFD700; margin-bottom: 15px;">🔥 এখনই ভোট দিন!</h2>
        <p style="font-size: 18px; line-height: 1.6;">
            ✨ আপনার পছন্দের রাজনৈতিক দলকে সমর্থন করুন<br>
            📊 রিয়েল টাইম ফলাফল দেখুন<br>
            🏆 কোন দল এগিয়ে আছে জানুন<br>
            ⚡ মাত্র ১ ক্লিকেই ভোট সম্পন্ন
        </p>
    </div>
    <p style="font-size: 16px; color: #FFD700;">👇 নিচে আপনার পছন্দের দলে ক্লিক করুন 👇</p>
</div>

<div id="voting-form">
    {% for party in parties %}
    <button class="party-button" onclick="castVote('{{ party }}')">
        {{ party }}
    </button>
    {% endfor %}
</div>

<div id="message" style="text-align: center; margin-top: 20px; font-weight: bold;"></div>

<script>
    function castVote(party) {
        document.getElementById('message').innerHTML = 
            '<span style="color: #FFD700;" class="pulse">⏳ ভোট প্রক্রিয়াধীন...</span>';
            
        fetch('/vote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({party: party})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('message').innerHTML = 
                    '<span style="color: #4CAF50;">✅ ' + data.message + ' ধন্যবাদ! 🎉</span>';
                setTimeout(() => {
                    window.location.href = '/results';
                }, 1500);
            } else {
                document.getElementById('message').innerHTML = 
                    '<span style="color: #FF6B6B;">❌ ' + data.message + ' ফলাফল দেখুন! 📊</span>';
                setTimeout(() => {
                    window.location.href = '/results';
                }, 2000);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('message').innerHTML = 
                '<span style="color: #FF6B6B;">❌ কিছু সমস্যা হয়েছে!</span>';
        });
    }
</script>
{% endblock %}
"""

# templates/results.html
RESULTS_HTML = """
{% extends "base.html" %}

{% block title %}🏆 নির্বাচনী ফলাফল - বাংলাদেশ জনমত সংগ্রহ{% endblock %}

{% block content %}
<div style="text-align: center; margin-bottom: 30px;">
    <h1>🏆 নির্বাচনী ফলাফল</h1>
    <div style="background: rgba(255, 255, 255, 0.2); padding: 15px; border-radius: 10px; margin: 20px 0;">
        <p style="font-size: 18px; color: #FFD700;">📊 রিয়েল টাইম ফলাফল | ⚡ তাৎক্ষণিক আপডেট</p>
        <p style="font-size: 16px;">আরো মানুষকে ভোট দিতে উৎসাহিত করুন! 👥</p>
    </div>
</div>

<div id="results-container">
    <div class="loading pulse">ফলাফল লোড হচ্ছে...</div>
</div>

{% if has_voted %}
<div style="text-align: center; margin-top: 30px; background: rgba(76, 175, 80, 0.2); padding: 20px; border-radius: 15px; border: 2px solid #4CAF50;">
    <h3 style="color: #4CAF50; margin-bottom: 15px;">✅ আপনার ভোট গ্রহণ করা হয়েছে!</h3>
    <p style="font-size: 18px; color: #E8F5E8;">
        🎉 ধন্যবাদ! আপনার মতামত সফলভাবে রেকর্ড হয়েছে<br>
        🚫 আপনি দ্বিতীয়বার ভোট দিতে পারবেন না<br>
        📊 ফলাফল রিয়েল টাইমে আপডেট হচ্ছে
    </p>
</div>
{% else %}
<a href="/" class="back-btn">← আবার ভোট দিন</a>
{% endif %}

<div style="text-align: center; margin-top: 30px; background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 15px;">
    <h3 style="color: #FFD700;">📱 বন্ধুদের সাথে শেয়ার করুন!</h3>
    <p>আরো মানুষকে ভোট দিতে উৎসাহিত করুন এবং আসল জনমত জানুন!</p>
    <div style="margin: 15px 0;">
        <button onclick="shareOnFacebook()" class="party-button" style="display: inline-block; width: auto; margin: 5px; padding: 10px 20px;">
            📘 Facebook এ শেয়ার করুন
        </button>
        <button onclick="shareOnWhatsApp()" class="party-button" style="display: inline-block; width: auto; margin: 5px; padding: 10px 20px;">
            💬 WhatsApp এ শেয়ার করুন
        </button>
        <button onclick="copyLink()" class="party-button" style="display: inline-block; width: auto; margin: 5px; padding: 10px 20px;">
            🔗 লিংক কপি করুন
        </button>
    </div>
</div>

<script>
    function updateResults() {
        fetch('/api/results')
            .then(response => response.json())
            .then(rankings => {
                const container = document.getElementById('results-container');
                container.innerHTML = '';
                
                rankings.forEach((item, index) => {
                    const card = document.createElement('div');
                    card.className = `results-card rank-${item.rank}`;
                    
                    const rankEmojis = ['🥇', '🥈', '🥉', '😢', '💔'];
                    const rankEmoji = rankEmojis[item.rank - 1] || '💔';
                    
                    card.innerHTML = `
                        <img src="${item.meme}" alt="Rank ${item.rank} meme" class="meme-img">
                        <h3>${rankEmoji} ${item.rank === 1 ? 'WINNER' : item.rank + getSuffix(item.rank) + ' Place'}</h3>
                        <h4>${item.party}</h4>
                        <div class="vote-count">${item.votes} ভোট</div>
                        <div style="clear: both;"></div>
                    `;
                    
                    container.appendChild(card);
                });
            })
            .catch(error => {
                console.error('Error loading results:', error);
                document.getElementById('results-container').innerHTML = 
                    '<div style="color: #FF6B6B;">ফলাফল লোড করতে সমস্যা হচ্ছে</div>';
            });
    }
    
    function getSuffix(rank) {
        if (rank === 1) return 'st';
        if (rank === 2) return 'nd';
        if (rank === 3) return 'rd';
        return 'th';
    }
    
    // Social sharing functions
    function shareOnFacebook() {
        const url = encodeURIComponent(window.location.origin);
        const text = encodeURIComponent('🗳️ বাংলাদেশ জনমত সংগ্রহে আমি ভোট দিয়েছি! তুমিও দাও এবং দেখো কোন দল এগিয়ে আছে! 🔥');
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${url}&quote=${text}`, '_blank');
    }
    
    function shareOnWhatsApp() {
        const url = encodeURIComponent(window.location.origin);
        const text = encodeURIComponent('🗳️ বাংলাদেশ জনমত সংগ্রহ!\\n\\n🔥 এখনই ভোট দিন এবং রিয়েল টাইম ফলাফল দেখুন!\\n📊 কোন দল এগিয়ে আছে জানুন!\\n\\n');
        window.open(`https://wa.me/?text=${text}${url}`, '_blank');
    }
    
    function copyLink() {
        navigator.clipboard.writeText(window.location.origin).then(() => {
            alert('✅ লিংক কপি হয়েছে! এখন যেকোনো জায়গায় শেয়ার করুন!');
        });
    }
    
    // Initial load
    updateResults();
    
    // Auto refresh every 5 seconds for real-time updates
    setInterval(updateResults, 5000);
</script>
{% endblock %}
"""

# Create template files
os.makedirs('templates', exist_ok=True)

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(BASE_HTML)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(INDEX_HTML)

with open('templates/results.html', 'w', encoding='utf-8') as f:
    f.write(RESULTS_HTML)

print("✅ Simple Flask Voting App created successfully!")
print("\n🚀 To run the application:")
print("1. Install required packages: pip install flask")
print("2. Run: python app.py")
print("3. Open http://127.0.0.1:5000 (or the port shown in terminal)")
print("\n🔧 Changes made:")
print("- Removed Flask-SocketIO (no socket permission issues)")
print("- Added AJAX polling every 5 seconds for real-time updates")
print("- Added Bengali text and better animations")
print("- Added social sharing buttons")
print("- Fixed port conflict issues")
