from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime
from collections import Counter

app = Flask(__name__)
CORS(app)  # Permite que tu frontend hable con el backend

# ==============================================
# CONFIGURACIÓN - ¡CAMBIAR CON TUS DATOS REALES!
# ==============================================

# Estas credenciales las obtienes de tu cuenta de Belvo
BELVO_SECRET_ID = "TU_SECRET_ID_AQUI"        # <-- CAMBIAR
BELVO_SECRET_PASSWORD = "TU_SECRET_PASSWORD" # <-- CAMBIAR
BELVO_ENVIRONMENT = "sandbox"  # Cambiar a "production" cuando estés listo

# ==============================================
# 1. GENERAR TOKEN PARA EL WIDGET
# ==============================================

@app.route('/api/token', methods=['GET'])
def generar_token():
    """
    Genera un token temporal para que el widget de Belvo funcione.
    Este token dura 10 minutos y es seguro.
    """
    try:
        url = f"https://{BELVO_ENVIRONMENT}.belvo.com/api/token/"
        
        payload = {
            "id": BELVO_SECRET_ID,
            "password": BELVO_SECRET_PASSWORD,
            "scopes": "read_institutions,write_links,read_links,read_balances,read_transactions"
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        return jsonify({
            "success": True,
            "access_token": data.get("access_token")
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==============================================
# 2. OBTENER TRANSACCIONES REALES
# ==============================================

@app.route('/api/transacciones', methods=['POST'])
def obtener_transacciones():
    """
    Recibe el link_id del widget y obtiene las transacciones reales del banco.
    """
    try:
        data = request.json
        link_id = data.get('link_id')
        
        if not link_id:
            return jsonify({"success": False, "error": "Falta link_id"}), 400
        
        # Obtener transacciones del mes actual
        url = f"https://{BELVO_ENVIRONMENT}.belvo.com/api/transactions/"
        
        hoy = datetime.now().date()
        primer_dia_mes = hoy.replace(day=1)
        
        payload = {
            "link": link_id,
            "date_from": primer_dia_mes.isoformat(),
            "date_to": hoy.isoformat()
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Autenticación básica con las credenciales de Belvo
        response = requests.post(
            url, 
            json=payload, 
            auth=(BELVO_SECRET_ID, BELVO_SECRET_PASSWORD)
        )
        response.raise_for_status()
        
        transacciones = response.json()
        
        # ====== PROCESAR DATOS ======
        resultados = procesar_transacciones(transacciones)
        
        return jsonify({
            "success": True,
            "datos": resultados
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==============================================
# 3. PROCESAR LAS TRANSACCIONES
# ==============================================

def procesar_transacciones(transacciones):
    """
    Extrae descripciones y montos de las transacciones.
    """
    resultados = transacciones.get('results', [])
    
    # Filtrar solo ingresos (monto > 0)
    ingresos = [t for t in resultados if t.get('amount', 0) > 0]
    
    ventas = []
    for ingreso in ingresos:
        descripcion = ingreso.get('description', 'Sin descripción')
        monto = abs(ingreso.get('amount', 0))
        fecha = ingreso.get('created_at', datetime.now())
        
        ventas.append({
            'descripcion': descripcion,
            'monto': monto,
            'fecha': fecha
        })
    
    # Contar por descripción
    contador = Counter([v['descripcion'] for v in ventas])
    
    # Resumen de ventas
    resumen_ventas = [
        {
            "producto": desc, 
            "unidades": count, 
            "ingreso_total": sum(v['monto'] for v in ventas if v['descripcion'] == desc)
        }
        for desc, count in contador.items()
    ]
    resumen_ventas.sort(key=lambda x: x['unidades'], reverse=True)
    
    return {
        "total_ingresos": sum(v['monto'] for v in ventas),
        "total_ventas": sum(contador.values()),
        "total_productos": len(resumen_ventas),
        "resumen_ventas": resumen_ventas[:10],  # Top 10
        "detalle_ventas": ventas  # Todas las transacciones
    }

# ==============================================
# 4. INICIAR EL SERVIDOR
# ==============================================

if __name__ == '__main__':
    print("🚀 Servidor DataVentas iniciado")
    print("📍 Puerto: 5000")
    print("🔗 http://localhost:5000")
    app.run(debug=True, port=5000)
