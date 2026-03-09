from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from functools import wraps
import os
import io
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

# Secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ankesa-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ankesa.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- FUNKSIONI NDIHMËS PËR DATAT ---
def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).date()
        except:
            return None

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ankesa(db.Model):
    __tablename__ = 'ankesa'
    id = db.Column(db.Integer, primary_key=True)
    nr_protokollit = db.Column(db.String(100), nullable=False)
    titulli_aktivitetit = db.Column(db.Text, nullable=False)
    autoriteti = db.Column(db.String(255), nullable=False)
    oe_ankues = db.Column(db.String(255), nullable=False)
    paramasa = db.Column(db.String(255))
    data_autorizimit = db.Column(db.Date)
    lloji_angazhimit = db.Column(db.String(50), nullable=False)
    eksperti_shqyrtues = db.Column(db.String(255))
    data_dorezimet = db.Column(db.Date, nullable=False)
    shqyrtimi_dite = db.Column(db.Integer)
    rekomandimi = db.Column(db.Text)
    vendimi = db.Column(db.Text)
    raport_file_url = db.Column(db.String(500))
    raport_file_name = db.Column(db.String(255))
    vendim_file_url = db.Column(db.String(500))
    vendim_file_name = db.Column(db.String(255))
    nr_fatures = db.Column(db.String(100))
    shuma_bruto = db.Column(db.Float)
    shuma_neto = db.Column(db.Float)
    statusi_pageses = db.Column(db.String(50), nullable=False)
    data_krijimit = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nrProtokollit': self.nr_protokollit,
            'titulliAktivitetit': self.titulli_aktivitetit,
            'autoriteti': self.autoriteti,
            'oeAnkues': self.oe_ankues,
            'paramasa': self.paramasa,
            'dataAutorizimit': self.data_autorizimit.strftime('%d/%m/%Y') if self.data_autorizimit else None,
            'llojiAngazhimit': self.lloji_angazhimit,
            'ekspertiShqyrtues': self.eksperti_shqyrtues,
            'dataDorezimet': self.data_dorezimet.strftime('%d/%m/%Y') if self.data_dorezimet else None,
            'shqyrtimiDite': self.shqyrtimi_dite,
            'rekomandimi': self.rekomandimi,
            'vendimi': self.vendimi,
            'raportFileUrl': self.raport_file_url,
            'raportFileName': self.raport_file_name,
            'vendimFileUrl': self.vendim_file_url,
            'vendimFileName': self.vendim_file_name,
            'nrFatures': self.nr_fatures,
            'shumaBruto': self.shuma_bruto,
            'shumaNeto': self.shuma_neto,
            'statusiPageses': self.statusi_pageses,
            'dataKrijimit': self.data_krijimit.isoformat()
        }

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/app.html')
def app_page():
    return send_from_directory('static', 'app.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username, password = data.get('username'), data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'], session['username'] = user.id, user.username
        return jsonify({'message': 'Login successful', 'username': user.username}), 200
    return jsonify({'error': 'Username ose password i gabuar'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'username': session.get('username')}), 200
    return jsonify({'authenticated': False}), 200

@app.route('/api/ankesa', methods=['GET'])
@login_required
def get_ankesa():
    ankesa_list = Ankesa.query.order_by(Ankesa.data_dorezimet.desc()).all()
    return jsonify([a.to_dict() for a in ankesa_list])

@app.route('/api/ankesa', methods=['POST'])
@login_required
def create_ankesa():
    data = request.json
    try:
        data_auth = parse_date(data.get('dataAutorizimit'))
        data_dor = parse_date(data.get('dataDorezimet'))
        if not data_dor:
             return jsonify({'error': 'Data e dorëzimit është e detyrueshme'}), 400
        
        shqyrtimi_dite = (data_dor - data_auth).days if data_auth and data_dor else None
        eksperti = 'N/A' if data.get('llojiAngazhimit') == 'Ekspert Shqyrtues' else data.get('ekspertiShqyrtues')

        ankesa = Ankesa(
            nr_protokollit=data['nrProtokollit'],
            titulli_aktivitetit=data['titulliAktivitetit'],
            autoriteti=data['autoriteti'],
            oe_ankues=data['oeAnkues'],
            paramasa=data.get('paramasa'),
            data_autorizimit=data_auth,
            lloji_angazhimit=data['llojiAngazhimit'],
            eksperti_shqyrtues=eksperti,
            data_dorezimet=data_dor,
            shqyrtimi_dite=shqyrtimi_dite,
            rekomandimi=data.get('rekomandimi'),
            vendimi=data.get('vendimi'),
            raport_file_url=data.get('raportFileUrl'),
            raport_file_name=data.get('raportFileName'),
            vendim_file_url=data.get('vendimFileUrl'),
            vendim_file_name=data.get('vendimFileName'),
            nr_fatures=data.get('nrFatures'),
            shuma_bruto=float(data['shumaBruto']) if data.get('shumaBruto') else None,
            shuma_neto=float(data['shumaNeto']) if data.get('shumaNeto') else None,
            statusi_pageses=data['statusiPageses']
        )
        db.session.add(ankesa); db.session.commit()
        return jsonify(ankesa.to_dict()), 201
    except Exception as e:
        db.session.rollback(); return jsonify({'error': str(e)}), 400

@app.route('/api/ankesa/export', methods=['GET'])
@login_required
def export_excel():
    ankesa_list = Ankesa.query.order_by(Ankesa.data_dorezimet.desc()).all()
    data = []
    for a in ankesa_list:
        data.append({
            'Nr. Protokollit': a.nr_protokollit,
            'Titulli i Aktivitetit': a.titulli_aktivitetit,
            'Autoriteti': a.autoriteti,
            'OE Ankues': a.oe_ankues,
            'Paramasa': a.paramasa,
            'Data e Autorizimit': a.data_autorizimit.strftime('%d/%m/%Y') if a.data_autorizimit else '',
            'Lloji i Angazhimit': a.lloji_angazhimit,
            'Eksperti': a.eksperti_shqyrtues,
            'Data e Dorëzimit': a.data_dorezimet.strftime('%d/%m/%Y') if a.data_dorezimet else '',
            'Ditë Shqyrtimi': a.shqyrtimi_dite,
            'Rekomandimi': a.rekomandimi,
            'Vendimi': a.vendimi,
            'Nr. Faturës': a.nr_fatures,
            'Shuma Bruto (€)': a.shuma_bruto,
            'Shuma Neto (€)': a.shuma_neto,
            'Statusi': a.statusi_pageses
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ankesat')
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"Ankesat_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    )

@app.route('/api/statistika', methods=['GET'])
@login_required
def get_statistika():
    total = Ankesa.query.count()
    paguar = Ankesa.query.filter_by(statusi_pageses='Paguar').count()
    papaguar = Ankesa.query.filter_by(statusi_pageses='Papaguar').count()
    pjeserisht = Ankesa.query.filter_by(statusi_pageses='Pjesërisht').count()
    total_shuma = db.session.query(db.func.sum(Ankesa.shuma_neto)).scalar() or 0
    return jsonify({
        'total': total, 
        'paguar': paguar, 
        'papaguar': papaguar, 
        'pjeserisht': pjeserisht, 
        'totalShuma': float(total_shuma)
    })

@app.route('/api/raport-mujor', methods=['GET'])
@login_required
def raport_mujor():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    if not month or not year:
        return jsonify({'error': 'Muaji dhe viti janë të detyrueshëm'}), 400
    ankesa_list = Ankesa.query.filter(
        db.extract('month', Ankesa.data_dorezimet) == month,
        db.extract('year', Ankesa.data_dorezimet) == year
    ).all()
    return jsonify({
        'total': len(ankesa_list),
        'totalNeto': sum(a.shuma_neto or 0 for a in ankesa_list),
        'ankesa': [a.to_dict() for a in ankesa_list]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
