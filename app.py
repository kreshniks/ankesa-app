from flask import Flask, request, jsonify, send_from_directory, session, send_file
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

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ankesa-secret-key-2026')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ankesa.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# FUNKSIONI NDIHMËS PËR DATAT
def parse_date(date_str):
    if not date_str: return None
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        try:
            return datetime.fromisoformat(date_str).date()
        except:
            return None

class Ankesa(db.Model):
    __tablename__ = 'ankesa'
    id = db.Column(db.Integer, primary_key=True)
    nr_protokollit = db.Column(db.String(100), nullable=False)
    nr_prokurimit = db.Column(db.String(100)) # Fusha e re
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
            'nrProkurimit': self.nr_prokurimit,
            'titulliAktivitetit': self.titulli_aktivitetit,
            'autoriteti': self.autoriteti,
            'oeAnkues': self.oe_ankues,
            'dataAutorizimit': self.data_autorizimit.strftime('%d/%m/%Y') if self.data_autorizimit else None,
            'llojiAngazhimit': self.lloji_angazhimit,
            'ekspertiShqyrtues': self.eksperti_shqyrtues,
            'dataDorezimet': self.data_dorezimet.strftime('%d/%m/%Y') if self.data_dorezimet else None,
            'shqyrtimiDite': self.shqyrtimi_dite,
            'rekomandimi': self.rekomandimi,
            'vendimi': self.vendimi,
            'nrFatures': self.nr_fatures,
            'statusiPageses': self.statusi_pageses,
            'shumaNeto': self.shuma_neto,
            'shumaBruto': self.shuma_bruto,
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
        return jsonify({'message': 'Suksese'}), 200
    return jsonify({'error': 'Gabim në kredencialet'}), 401

@app.route('/api/ankesa', methods=['GET'])
@login_required
def get_ankesa():
    # NDRYSHIMI: Renditja sipas data_autorizimit (më e afërta lart)
    ankesat = Ankesa.query.order_by(Ankesa.data_autorizimit.desc().nullslast()).all()
    return jsonify([a.to_dict() for a in ankesat])

@app.route('/api/ankesa', methods=['POST'])
@login_required
def create_ankesa():
    data = request.json
    try:
        data_auth = parse_date(data.get('dataAutorizimit'))
        data_dor = parse_date(data.get('dataDorezimet'))
        
        shqyrtimi_dite = (data_dor - data_auth).days if data_auth and data_dor else None
        
        # NDRYSHIMI: Logjika për N/A në llojin e angazhimit
        lloji = data.get('llojiAngazhimit')
        eksperti = data.get('ekspertiShqyrtues')
        if lloji in ['Ekspert Shqyrtues', 'Superekspertizë']:
            eksperti = 'N/A'
        
        ankesa = Ankesa(
            nr_protokollit=data['nrProtokollit'],
            nr_prokurimit=data.get('nrProkurimit'),
            titulli_aktivitetit=data['titulliAktivitetit'],
            autoriteti=data['autoriteti'],
            oe_ankues=data['oeAnkues'],
            data_autorizimit=data_auth,
            data_dorezimet=data_dor,
            lloji_angazhimit=lloji,
            eksperti_shqyrtues=eksperti,
            shqyrtimi_dite=shqyrtimi_dite,
            rekomandimi=data.get('rekomandimi'),
            vendimi=data.get('vendimi'),
            nr_fatures=data.get('nrFatures'),
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

@app.route('/api/ankesa/export')
@login_required
def export_excel():
    # Eksporti përdor të njëjtën renditje si lista
    ankesat = Ankesa.query.order_by(Ankesa.data_autorizimit.desc().nullslast()).all()
    
    data_list = []
    for a in ankesat:
        data_list.append({
            'Nr. Protokollit': a.nr_protokollit,
            'Nr. Prokurimit': a.nr_prokurimit,
            'Titulli': a.titulli_aktivitetit,
            'Autoriteti': a.autoriteti,
            'OE Ankues': a.oe_ankues,
            'Data Autorizimit': a.data_autorizimit.strftime('%d/%m/%Y') if a.data_autorizimit else '',
            'Lloji Angazhimit': a.lloji_angazhimit,
            'Eksperti': a.eksperti_shqyrtues,
            'Data Dorëzimit': a.data_dorezimet.strftime('%d/%m/%Y') if a.data_dorezimet else '',
            'Shuma Bruto': a.shuma_bruto,
            'Shuma Neto': a.shuma_neto,
            'Statusi': a.statusi_pageses,
            'Fatura': a.nr_fatures
        })
    
    df = pd.DataFrame(data_list)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ekspertizat')
    output.seek(0)
    
    return send_file(
        output, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        as_attachment=True, 
        download_name=f"Ekspertizat_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
