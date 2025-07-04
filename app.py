from flask import Flask, request,render_template
from sqlalchemy import create_engine, text
import pandas as pd
import pickle
from datetime import datetime
import json
import os



conexion = "postgresql://user:QaJwixwfNPNuBWWk4zxsIXMqWeOnh3JM@dpg-d1j5ps6mcj7s73a8p09g-a.oregon-postgres.render.com/dbname_vzb4"
engine= create_engine(conexion)

with open("personality.pkl", 'rb') as file:
            model_loaded = pickle.load(file)

app = Flask(__name__)
app.config["DEBUG"] = True

def create_predictions_table():
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            input JSONB NOT NULL,
            personality TEXT NOT NULL
        );
    """)

    with engine.connect() as conn:
        conn.execute(create_table_sql)
        conn.commit()
        print("Tabla 'predictions' verificada o creada.")


create_predictions_table()

@app.route('/api/personality/predict', methods=['POST'])
def predict():
    data = request.json

    X = pd.DataFrame([data])
    prediction = model_loaded.predict(X)[0]

    input_json = json.dumps(data)

    query_insert = text("""
        INSERT INTO predictions (timestamp, input, personality)
        VALUES (:timestamp, :input, :personality)
    """)

    with engine.connect() as conn:
        conn.execute(query_insert, {
            'timestamp': datetime.now(),
            'input': input_json,
            'personality': str(prediction)
        })
        conn.commit()

    query_select = "SELECT * FROM predictions"
    result = pd.read_sql(query_select, con=engine).to_dict(orient="records")
    return result


@app.route('/api/personality/history', methods=['GET'])
def history():
    if "id" in request.args:
        prediction_id = int(request.args['id'])
        query = "SELECT * FROM predictions WHERE id = %s"
        df = pd.read_sql(query, con=engine, params=(prediction_id,))
        if df.empty:
            return {"error": "Prediction not found"}
        return df.to_dict(orient="records")[0]
    else:
        query = "SELECT * FROM predictions"
        df = pd.read_sql(query, con=engine)
        return df.to_dict(orient="records")
    

from flask import redirect, url_for

@app.route('/predict', methods=['GET'])
def predict_form():
    # Solo muestra el formulario
    return render_template("predict.html")

@app.route('/predict', methods=['POST'])
def predict_submit():
    form_data = request.form.to_dict()

    form_data["Stage_fear"] = '1' if form_data.get("Stage_fear") == "Yes" else '0'
    form_data["Drained_after_socializing"] = '1' if form_data.get("Drained_after_socializing") == "Yes" else '0'

    X = pd.DataFrame([form_data])
    prediction = model_loaded.predict(X)[0]

    input_json = json.dumps(form_data)
    query_insert = text("""
        INSERT INTO predictions (timestamp, input, personality)
        VALUES (:timestamp, :input, :personality)
        RETURNING id
    """)

    with engine.connect() as conn:
        result = conn.execute(query_insert, {
            'timestamp': datetime.now(),
            'input': input_json,
            'personality': str(prediction)
        })
        inserted_id = result.fetchone()[0]
        conn.commit()

    return redirect(url_for('result', id=inserted_id))

@app.route('/result', methods=['GET'])
def result():
    if "id" not in request.args:
        return "ID no proporcionado", 400

    prediction_id = int(request.args['id'])
    query = "SELECT * FROM predictions WHERE id = %s"
    df = pd.read_sql(query, con=engine, params=(prediction_id,))

    if df.empty:
        return "Predicción no encontrada", 404

    record = df.iloc[0]
    data = record['input']

    return render_template("result.html", prediction=record['personality'], data=data)

if __name__ == "__main__": 
    app.run()