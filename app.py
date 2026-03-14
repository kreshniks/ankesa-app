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

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sekreti-2026')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///ankesa.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def parse_date(date_str):
    """Parse date from various formats"""
    if not date_str: 
        return None
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
    
    # PHASE 1: Basic Registration Fields (Required)
    nr_protokollit = db.Column(db.String(100), nullable=False)
    titulli_aktivitetit = db.Column(db.Text, nullable=False)
    autoriteti = db.Column(db.String(255), nullable=False)
    oe_ankues = db.Column(db.String(255), nullable=False)
    lloji_angazhimit = db.Column(db.String(50), nullable=False)
    shuma_bruto = db.Column(db.Float, nullable=False)
    shuma_neto = db.Column(db.Float, nullable=False)
    
    # PHASE 1: Basic Registration Fields (Optional)
    nr_prokurimit = db.Column(db.String(100))
    data_autorizimit = db.Column(db.Date)
    eksperti_shqyrtues = db.Column(db.String(255))
    
    # PHASE 2: Completion Fields (All Optional - Added Later)
    data_dorezimet = db.Column(db.Date)  # ✅ NULLABLE - Added in Phase 2
    shqyrtimi_dite = db.Column(db.Integer)
    rekomandimi = db.Column(db.Text)
    vendimi = db.Column(db.Text)
    seanca = db.Column(db.String(3))
    raport_file_url = db.Column(db.String(500))
    raport_file_name = db.Column(db.String(255))
    vendim_file_url = db.Column(db.String(500))
    vendim_file_name = db.Column(db.String(255))
    
    # PHASE 3: Billing Fields (Optional - Added in Billing Tab)
    nr_fatures = db.Column(db.String(100))
    statusi_pageses = db.Column(db.String(50), default='Papaguar')
    
    # Legacy field (not used in new workflow)
    paramasa = db.Column(db.String(255))
    
    # System fields
    data_krijimit = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for JSON response"""
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
            'seanca': self.seanca,
            'nrFatures': self.nr_fatures,
            'statusiPageses': self.statusi_pageses or 'Papaguar',
            'shumaNeto': self.shuma_neto,
            'shumaBruto': self.shuma_bruto,
            'raportFileUrl': self.raport_file_url,
            'vendimFileUrl': self.vendim_file_url
        }

# Create tables
with app.app_context():
    db.create_all()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session: 
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES ====================

@app.route('/')
def index(): 
    return send_from_directory('static', 'index.html')

@app.route('/app.html')
def app_page(): 
    return send_from_directory('static', 'app.html')

@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['user_id'] = 1
        return jsonify({'message': 'Suksese'}), 200
    return jsonify({'error': 'Gabim'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated"""
    return jsonify({'authenticated': 'user_id' in session}), 200

@app.route('/api/ankesa', methods=['GET'])
@login_required
def get_ankesa():
    """Get all ekspertiza records (ordered by newest first)"""
    ankesat = Ankesa.query.order_by(Ankesa.data_krijimit.desc()).all()
    return jsonify([a.to_dict() for a in ankesat])

@app.route('/api/ankesa', methods=['POST'])
@login_required
def create_ankesa():
    """
    Create new ekspertiza (PHASE 1 - Basic Registration)
    
    Required fields:
    - nrProtokollit
    - titulliAktivitetit
    - autoriteti
    - oeAnkues
    - llojiAngazhimit
    - shumaBruto
    - shumaNeto
    
    Optional fields (can be added later in PHASE 2):
    - dataDorezimet (will be None initially)
    - rekomandimi, vendimi, seanca, etc.
    """
    data = request.json
    try:
        d_auth = parse_date(data.get('dataAutorizimit'))
        d_dor = parse_date(data.get('dataDorezimet'))  # Can be None in Phase 1
        
        # Handle Eksperti Shqyrtues logic
        lloji = data.get('llojiAngazhimit')
        eksperti = data.get('ekspertiShqyrtues')
        if lloji in ['Ekspert Shqyrtues', 'Superekspertizë']:
            eksperti = 'N/A'
        
        # Calculate days if both dates exist
        shqyrtimi_days = None
        if d_auth and d_dor:
            shqyrtimi_days = (d_dor - d_auth).days
        
        ankesa = Ankesa(
            # Phase 1: Required fields
            nr_protokollit=data['nrProtokollit'],
            titulli_aktivitetit=data['titulliAktivitetit'],
            autoriteti=data['autoriteti'],
            oe_ankues=data['oeAnkues'],
            lloji_angazhimit=lloji,
            shuma_bruto=float(data['shumaBruto']) if data.get('shumaBruto') else 0,
            shuma_neto=float(data['shumaNeto']) if data.get('shumaNeto') else 0,
            
            # Phase 1: Optional fields
            nr_prokurimit=data.get('nrProkurimit'),
            data_autorizimit=d_auth,
            eksperti_shqyrtues=eksperti,
            
            # Phase 2: Completion fields (can be None)
            data_dorezimet=d_dor,
            shqyrtimi_dite=shqyrtimi_days,
            rekomandimi=data.get('rekomandimi'),
            vendimi=data.get('vendimi'),
            seanca=data.get('seanca'),
            raport_file_url=data.get('raportFileUrl'),
            vendim_file_url=data.get('vendimFileUrl'),
            
            # Phase 3: Billing fields
            nr_fatures=data.get('nrFatures'),
            statusi_pageses=data.get('statusiPageses', 'Papaguar')
        )
        
        db.session.add(ankesa)
        db.session.commit()
        return jsonify(ankesa.to_dict()), 201
        
    except KeyError as e:
        db.session.rollback()
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/ankesa/<int:id>', methods=['PUT'])
@login_required
def update_ankesa(id):
    """
    Update existing ekspertiza (PHASE 2 - Completion or PHASE 3 - Billing)
    
    This endpoint is used for:
    - Phase 2: Adding completion data (dataDorezimet, rekomandimi, etc.)
    - Phase 3: Adding billing data (nrFatures, statusiPageses)
    """
    ankesa = Ankesa.query.get_or_404(id)
    data = request.json
    
    try:
        d_auth = parse_date(data.get('dataAutorizimit'))
        d_dor = parse_date(data.get('dataDorezimet'))
        
        # Handle Eksperti Shqyrtues logic
        lloji = data.get('llojiAngazhimit')
        eksperti = data.get('ekspertiShqyrtues')
        if lloji in ['Ekspert Shqyrtues', 'Superekspertizë']:
            eksperti = 'N/A'
        
        # Calculate days if both dates exist
        shqyrtimi_days = None
        if d_auth and d_dor:
            shqyrtimi_days = (d_dor - d_auth).days
        
        # Update all fields
        ankesa.nr_protokollit = data['nrProtokollit']
        ankesa.nr_prokurimit = data.get('nrProkurimit')
        ankesa.titulli_aktivitetit = data['titulliAktivitetit']
        ankesa.autoriteti = data['autoriteti']
        ankesa.oe_ankues = data['oeAnkues']
        ankesa.data_autorizimit = d_auth
        ankesa.data_dorezimet = d_dor
        ankesa.lloji_angazhimit = lloji
        ankesa.eksperti_shqyrtues = eksperti
        ankesa.shqyrtimi_dite = shqyrtimi_days
        ankesa.rekomandimi = data.get('rekomandimi')
        ankesa.vendimi = data.get('vendimi')
        ankesa.seanca = data.get('seanca')
        ankesa.nr_fatures = data.get('nrFatures')
        ankesa.shuma_bruto = float(data['shumaBruto']) if data.get('shumaBruto') else 0
        ankesa.shuma_neto = float(data['shumaNeto']) if data.get('shumaNeto') else 0
        ankesa.statusi_pageses = data.get('statusiPageses', 'Papaguar')
        ankesa.raport_file_url = data.get('raportFileUrl')
        ankesa.vendim_file_url = data.get('vendimFileUrl')
        
        db.session.commit()
        return jsonify(ankesa.to_dict()), 200
        
    except KeyError as e:
        db.session.rollback()
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/ankesa/<int:id>', methods=['DELETE'])
@login_required
def delete_ankesa(id):
    """Delete an ekspertiza"""
    ankesa = Ankesa.query.get_or_404(id)
    try:
        db.session.delete(ankesa)
        db.session.commit()
        return jsonify({'message': 'Deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/ankesa/export')
@login_required
def export_excel():
    """
    Export all ekspertiza to Excel
    
    Includes all 20 fields with proper formatting:
    - Auto-adjusted column widths
    - Text wrapping
    - Vertical alignment
    """
    ankesat = Ankesa.query.order_by(Ankesa.data_krijimit.desc()).all()
    
    data_list = []
    for i, a in enumerate(ankesat, 1):
        data_list.append({
            'Nr': i,
            'Nr. Protokollit': a.nr_protokollit,
            'Nr. Prokurimit': a.nr_prokurimit or '',
            'Titulli i Aktivitetit': a.titulli_aktivitetit,
            'Autoriteti Kontraktues': a.autoriteti,
            'OE Ankues': a.oe_ankues,
            'Data Autorizimit': a.data_autorizimit.strftime('%d/%m/%Y') if a.data_autorizimit else '',
            'Data Dorëzimit': a.data_dorezimet.strftime('%d/%m/%Y') if a.data_dorezimet else '',
            'Lloji Angazhimit': a.lloji_angazhimit,
            'Eksperti Shqyrtues': a.eksperti_shqyrtues or 'N/A',
            'Shqyrtimi (ditë)': a.shqyrtimi_dite or '',
            'Rekomandimi': a.rekomandimi or '',
            'Vendimi': a.vendimi or '',
            'Seanca': a.seanca or '',
            'Raport (URL)': a.raport_file_url or '',
            'Vendimi (URL)': a.vendim_file_url or '',
            'Nr. Faturës': a.nr_fatures or '',
            'Shuma Bruto (€)': a.shuma_bruto or 0,
            'Shuma Neto (€)': a.shuma_neto or 0,
            'Statusi Pagesës': a.statusi_pageses or 'Papaguar'
        })
    
    df = pd.DataFrame(data_list)
    out = io.BytesIO()
    
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ekspertizat')
        
        # Get the worksheet
        worksheet = writer.sheets['Ekspertizat']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Max width 50
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Enable text wrapping for all cells
        from openpyxl.styles import Alignment
        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    
    out.seek(0)
    return send_file(
        out, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        as_attachment=True, 
        download_name="Ekspertizat.xlsx"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
