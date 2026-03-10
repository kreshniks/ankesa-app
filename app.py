from flask import Flask, request, jsonify, send_from_directory, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from functools import wraps
import os
import io
import pandas as pd # Shtohet për Excel
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ankesa-secret-key-2026')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ankesa.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# FUNKSIONI NDIHMËS PËR DATAT (Zgjidh gabimin 400)
def parse_date(date_str):
    if not date_str: return None
    try:
        # Provon formatin DD/MM/YYYY që vjen nga UI
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            # Provon formatin ISO (standardi i vjetër)
            return datetime.fromisoformat(date_str).date()
        except:
            return None

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
            'dataAutorizimit': self.data_autorizimit.strftime('%d/%m/%Y') if self.data_autorizimit else None,
            'llojiAngazhimit': self.lloji_angazhimit,
            'ekspertiShqyrtues': self.eksperti_shqyrtues,
            'dataDorezimet': self.data_dorezimet.strftime('%d/%m/%Y') if self.data_dorezimet else None,
            'shqyrtimiDite': self.shqyrtimi_dite,
            'statusiPageses': self.statusi_pageses,
            'shumaNeto': self.shuma_neto,
            'raportFileUrl': self.raport_file_url,
            'vendimFileUrl': self.vendim_file_url
        }

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/app.html')
def app_page(): return send_from_directory('static', 'app.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['user_id'] = 1
        return jsonify({'message': 'Erresire'}), 200
    return jsonify({'error': 'Gabim'}), 401

@app.route('/api/ankesa', methods=['GET'])
@login_required
def get_ankesa():
    ankesat = Ankesa.query.order_by(Ankesa.data_dorezimet.desc()).all()
    return jsonify([a.to_dict() for a in ankesat])

@app.route('/api/ankesa', methods=['POST'])
@login_required
def create_ankesa():
    data = request.json
    try:
        data_auth = parse_date(data.get('dataAutorizimit'))
        data_dor = parse_date(data.get('dataDorezimet'))
        
        shqyrtimi_dite = (data_dor - data_auth).days if data_auth and data_dor else None
        
        ankesa = Ankesa(
            nr_protokollit=data['nrProtokollit'],
            titulli_aktivitetit=data['titulliAktivitetit'],
            autoriteti=data['autoriteti'],
            oe_ankues=data['oeAnkues'],
            data_autorizimit=data_auth,
            data_dorezimet=data_dor,
            lloji_angazhimit=data['llojiAngazhimit'],
            eksperti_shqyrtues='N/A' if data.get('llojiAngazhimit') == 'Ekspert Shqyrtues' else data.get('ekspertiShqyrtues'),
            shqyrtimi_dite=shqyrtimi_dite,
            shuma_bruto=float(data['shumaBruto']) if data.get('shumaBruto') else 0,
            shuma_neto=float(data['shumaNeto']) if data.get('shumaNeto') else 0,
            statusi_pageses=data['statusiPageses'],
            raport_file_url=data.get('raportFileUrl'),
            vendim_file_url=data.get('vendimFileUrl')
        )
        db.session.add(ankesa)
        db.session.commit()
        return jsonify(ankesa.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/statistika')
@login_required
def get_stats():
    total = Ankesa.query.count()
    total_shuma = db.session.query(db.func.sum(Ankesa.shuma_neto)).scalar() or 0
    return jsonify({'total': total, 'totalShuma': float(total_shuma)})

# FUNKSIONI PËR EKSPORTIN (Që mungonte)
@app.route('/api/ankesa/export')
@login_required
def export_excel():
    ankesat = Ankesa.query.all()
    df = pd.DataFrame([a.to_dict() for a in ankesat])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name="ankesat.xlsx")
