
import os
import sqlite3
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, request, url_for
from sqlite3 import IntegrityError

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_db():
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rezepte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            zutaten TEXT NOT NULL,
            rezept TEXT NOT NULL,
            dauer NUMBER NOT NULL,
            bild TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()

    # Rezept des Tages auswählen (hier: zufälliges Rezept)
    cursor.execute('SELECT * FROM Rezepte ORDER BY RANDOM() LIMIT 1')
    rezept_des_tages = cursor.fetchone()

    # Alle Rezepte abrufen
    cursor.execute('SELECT * FROM Rezepte')
    rezepte_list = cursor.fetchall()

    conn.close()

    return render_template('index.html', rezepte=rezepte_list, rezept_des_tages=rezept_des_tages)

@app.route('/datenschutz')
def datenschutz():
    return('500 Internal Server Error')



@app.route('/suche_zutaten')
def suche_zutaten():
    query = request.args.get('zutaten', '').lower()

    if not query:
        return render_template('zutaten_ergebnisse.html')

    # Zutaten aufteilen und formatieren
    zutaten_liste = [zutat.strip() for zutat in query.split(',')]

    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()

    # Dynamische SQL-Abfrage zur Zählung der Übereinstimmungen und Sortierung der Ergebnisse
    placeholders = ' + '.join([f"(zutaten LIKE '%{zutat}%')" for zutat in zutaten_liste])
    sql_query = f'''
        SELECT *, ({placeholders}) as matching_count
        FROM Rezepte
        WHERE {' OR '.join([f"zutaten LIKE ?" for _ in zutaten_liste])}
        ORDER BY matching_count DESC
    '''

    cursor.execute(sql_query, [f'%{zutat}%' for zutat in zutaten_liste])

    ergebnisse = cursor.fetchall()
    conn.close()

    return render_template('zutaten_ergebnisse.html', rezepte=ergebnisse, query=query)




@app.route('/ads.txt')
def ads():
    return('google.com, pub-7826802472457776, DIRECT, f08c47fec0942fa0')

@app.route('/search')
def search():
    return render_template('search_bar.html')

@app.route('/suche')
def suche():
    query = request.args.get('query', '').lower()

    if not query:
        return render_template('search_bar.html')

    # Formatieren des Suchbegriffs für die Suche in der Datenbank
    formatted_query = query.replace(' ', '-')

    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()

    # Suche nach Rezepten, die den Suchbegriff im Namen oder in den Zutaten enthalten
    cursor.execute('''
        SELECT * FROM Rezepte
        WHERE name LIKE ? OR zutaten LIKE ?
    ''', ('%' + formatted_query + '%', '%' + query + '%'))

    ergebnisse = cursor.fetchall()
    conn.close()

    return render_template('suche.html', rezepte=ergebnisse, query=query)

@app.route('/add')
def add():
    return render_template('upload.html')

@app.route('/submit_send', methods=['POST'])
def submit_send():
    # Formulardaten abrufen
    name = request.form['name']
    zutaten = request.form['zutaten']
    rezept = request.form['rezept']
    dauer = 'ca. ' + request.form['dauer'] + ' Minuten'

    # Bildverarbeitung
    bild = request.files.get('bild')
    bild_name = None
    if bild and bild.filename:
        bild_name = secure_filename(bild.filename)
        bild_path = os.path.join(UPLOAD_FOLDER, bild_name)
        bild.save(bild_path)

    # Rezeptnamen formatieren
    formatted_name = name.lower()

    try:

        # Daten in die Datenbank einfügen
        conn = sqlite3.connect('rezepte.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Rezepte (name, zutaten, rezept, dauer, bild) VALUES (?, ?, ?, ?, ?)',
            (formatted_name, zutaten, rezept, dauer, bild_name))
        conn.commit()
        conn.close()
    except IntegrityError as e:
        print('error,', e)
        return redirect(url_for('add'))

    # Weiterleitung zur neuen Seite mit dem hinzugefügten Rezept
    return redirect(url_for('show_rezept', rezept_name=formatted_name))

@app.route('/rezepte/<rezept_name>')
def show_rezept(rezept_name):
    # Rezept aus der Datenbank abrufen
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
    rezept = cursor.fetchone()  # Ändere .fetchall() zu .fetchone()
    conn.close()

    if rezept:
        return render_template('rezept_detail.html', rezept=rezept)
    else:
        return f"Rezept mit Name '{rezept_name}' nicht gefunden.", 404

@app.route('/rezepte/')
def rezepte_slash():
    return redirect(url_for('rezepte'))
@app.route('/rezepte')
def rezepte():
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Rezepte')
    rezepte_list = cursor.fetchall()
    conn.close()

    return render_template('rezepte.html', rezepte=rezepte_list)

@app.route('/rezept_bearbeiten/<rezept_name>', methods=['GET'])
def bearbeiten(rezept_name):
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
    rezept = cursor.fetchone()
    conn.close()

    if rezept:
        return render_template('rezept_bearbeiten.html', rezept=rezept)
    else:
        return f"Rezept mit Name '{rezept_name}' nicht gefunden.", 404

# Route zum Verarbeiten des Bearbeitungsformulars
@app.route('/rezept_bearbeiten/<rezept_name>', methods=['POST'])
def bearbeiten_submit(rezept_name):
    name = request.form['name']
    zutaten = request.form['zutaten']
    rezept = request.form['rezept']
    dauer = 'ca. ' + request.form['dauer'] + ' Minuten'

    formatted_name = name.lower()  # Keine Bindestriche hier

    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE Rezepte
        SET name = ?, zutaten = ?, rezept = ?, dauer = ?
        WHERE name = ?
    ''', (formatted_name, zutaten, rezept, dauer, rezept_name))
    conn.commit()
    conn.close()

    return redirect(url_for('show_rezept', rezept_name=formatted_name))

#löschen eines Rezeptes
@app.route('/rezept_loeschen/<rezept_name>', methods=['POST'])
def loeschen(rezept_name):
    conn = sqlite3.connect('rezepte.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Rezepte WHERE name = ?', (rezept_name,))
    conn.commit()
    conn.close()

    return redirect(url_for('rezepte'))




if __name__ == '__main__':
    init_db()  # Datenbank initialisieren, wenn die App gestartet wird
    app.run(debug=False, host='0.0.0.0', port=5000)
