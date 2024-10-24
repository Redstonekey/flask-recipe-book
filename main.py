import os
import sqlite3
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, request, url_for, session, flash, jsonify
from sqlite3 import IntegrityError

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.secret_key = 'jasdhfjasefoanvjff74809'

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
            bild TEXT,
            userid
        )
    ''')
    conn.commit()
    conn.close()



def init_rezepte_db(email):
    # Erstelle den Ordner für den Benutzer, falls er nicht existiert
    user_folder = f"user/{email}/"
    os.makedirs(user_folder, exist_ok=True)
    
    # Definiere den Pfad zur Datenbank
    db_path = os.path.join(user_folder, 'rezepte.db')
    
    # Verbinde zur Datenbank
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rezepte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            zutaten TEXT NOT NULL,
            rezept TEXT NOT NULL,
            dauer NUMBER NOT NULL,
            bild TEXT,
            userid TEXT
        )
    ''')
    conn.commit()
    conn.close()



def init_user_db():
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT ,
            password Text
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Rezept des Tages auswählen (hier: zufälliges Rezept)
        cursor.execute('SELECT * FROM Rezepte ORDER BY RANDOM() LIMIT 1')
        rezept_des_tages = cursor.fetchone()

        # Alle Rezepte abrufen
        cursor.execute('SELECT * FROM Rezepte')
        rezepte_list = cursor.fetchall()

        conn.close()

        return render_template('index.html', rezepte=rezepte_list, rezept_des_tages=rezept_des_tages)
    return redirect(url_for('signup'))


@app.route('/create-acc')
def create_acc_for_admin():
    email = 'admin@admin.com'
    password = 'test'

    try:
      conn = sqlite3.connect('user.db') 
      c = conn.cursor()
      c.execute(
          """INSERT INTO user (
            email,
            password
          ) VALUES (?, ?)""",
          (email, password))
      conn.commit()
      conn.close()
    except Exception as e:
      print(e)
      return f'Acc already exists error: {e}'
    print()
    print()
    print()
    print()
    print()
    print()
    print('Account got created by /create-acc')
    print()
    print()
    print()
    print()
    print()
    print()
    os.makedirs('user/' + email)
    init_rezepte_db(email)

    return 'Account creation succsesfull'



@app.route('/datenschutz')
def datenschutz():
    return('500 Internal Server Error')



@app.route('/suche_zutaten')
def suche_zutaten():
    if 'email' in session:
        email = session.get('email')
        query = request.args.get('zutaten', '').lower()

        if not query:
            return render_template('zutaten_ergebnisse.html')

        # Zutaten aufteilen und formatieren
        zutaten_liste = [zutat.strip() for zutat in query.split(',')]

        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
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
    return redirect(url_for('login'))





@app.route('/ads.txt')
def ads():
    return 'google.com, pub-7826802472457776, DIRECT, f08c47fec0942fa0', 200

@app.route('/search')
def search():
    return render_template('search_bar.html')

@app.route('/suche')
def suche():
    if 'email' in session:
        email = session.get('email')
        query = request.args.get('query', '').lower()

        if not query:
            return render_template('search_bar.html')

        # Formatieren des Suchbegriffs für die Suche in der Datenbank
        formatted_query = query.replace(' ', '-')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Suche nach Rezepten, die den Suchbegriff im Namen oder in den Zutaten enthalten
        cursor.execute('''
            SELECT * FROM Rezepte
            WHERE name LIKE ? OR zutaten LIKE ?
        ''', ('%' + formatted_query + '%', '%' + query + '%'))

        ergebnisse = cursor.fetchall()
        conn.close()

        return render_template('suche.html', rezepte=ergebnisse, query=query)
    return redirect(url_for('login'))

@app.route('/add')
def add():
    if 'email' in session:
        email = session.get('email')
        return render_template('upload.html')
    return redirect(url_for('login'))




@app.route('/submit_send', methods=['POST'])
def submit_send():
    if 'email' in session:
        email = session.get('email')
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

            db_path = os.path.join( f'user/{email}/', 'rezepte.db')
            conn = sqlite3.connect(db_path)

            db_path = os.path.join(f'user/{email}/', 'rezepte.db')
            conn = sqlite3.connect(db_path)
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
    return redirect(url_for('login'))

@app.route('/rezepte/<rezept_name>')
def show_rezept(rezept_name):
    if 'email' in session:
        email = session.get('email')
        # Rezept aus der Datenbank abrufen
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
        rezept = cursor.fetchone()  # Ändere .fetchall() zu .fetchone()
        conn.close()

        if rezept:
            return render_template('rezept_detail.html', rezept=rezept)
        else:
            return f"Rezept mit Name '{rezept_name}' nicht gefunden.", 404
    return redirect(url_for('login'))

@app.route('/rezepte/')
def rezepte_slash():
    return redirect(url_for('rezepte'))

@app.route('/rezepte')
def rezepte():
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte')
        rezepte_list = cursor.fetchall()
        conn.close()

        return render_template('rezepte.html', rezepte=rezepte_list)
    return redirect(url_for('login'))

@app.route('/rezept_bearbeiten/<rezept_name>', methods=['GET'])
def bearbeiten(rezept_name):
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
        rezept = cursor.fetchone()
        conn.close()

        if rezept:
            return render_template('rezept_bearbeiten.html', rezept=rezept)
        else:
            return f"Rezept mit Name '{rezept_name}' nicht gefunden.", 404
    return redirect(url_for('login'))

# Route zum Verarbeiten des Bearbeitungsformulars
@app.route('/rezept_bearbeiten/<rezept_name>', methods=['POST'])
def bearbeiten_submit(rezept_name):
    if 'email' in session:
        email = session.get('email')
        name = request.form['name']
        zutaten = request.form['zutaten']
        rezept = request.form['rezept']
        dauer = 'ca. ' + request.form['dauer'] + ' Minuten'

        formatted_name = name.lower()  # Keine Bindestriche hier

        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE Rezepte
            SET name = ?, zutaten = ?, rezept = ?, dauer = ?
            WHERE name = ?
        ''', (formatted_name, zutaten, rezept, dauer, rezept_name))
        conn.commit()
        conn.close()

        return redirect(url_for('show_rezept', rezept_name=formatted_name))
    return redirect(url_for('login'))

#löschen eines Rezeptes
@app.route('/rezept_loeschen/<rezept_name>', methods=['POST'])
def loeschen(rezept_name):
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM Rezepte WHERE name = ?', (rezept_name,))
        conn.commit()
        conn.close()

        return redirect(url_for('rezepte'))
    return redirect(url_for('login'))






@app.route("/signup", methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    email = request.form['email']
    password = request.form['password']

    try:
      conn = sqlite3.connect('user.db') 
      c = conn.cursor()
      c.execute(
          """INSERT INTO user (
            email,
            password
          ) VALUES (?, ?)""",
          (email, password))
      conn.commit()
      conn.close()
    except Exception as e:
      print(e)
      flash(f'Email already exists Error: {e}')
      return redirect(url_for('signup'))

    
    print(email + ' ' +password)
    os.makedirs('user/' + email)
    init_rezepte_db(email)


    
    return redirect(url_for('login'))
  return render_template('signup.html')



@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Verbindung zur Datenbank
        conn = sqlite3.connect('user.db')
        cursor = conn.cursor()
        query = "SELECT * FROM user WHERE email = ? AND password = ?"
        cursor.execute(query, (email, password))
        result = cursor.fetchone()
        conn.close()

        if result:
            # Speichern von Nutzerdaten in der Session
            session['email'] = email
            return redirect(url_for('index'))
            # return redirect(url_for('index'))
        else:
            flash('Email oder Passwort falsch!')
            return render_template('login.html')
    return render_template('login.html')




@app.route("/test/status")
def TEST_HOME():
    if 'email' in session:
        return 'LOGED IN!'
    return redirect(url_for('login'))



@app.route("/logout")
def logout():
    # Clear the session
    session.pop('email', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()  # Datenbank initialisieren, wenn die App gestartet wird
    init_user_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
