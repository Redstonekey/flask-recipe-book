import os
import sqlite3
from werkzeug.utils import secure_filename
from flask import Flask, send_from_directory, abort, redirect, render_template, request, url_for, session, flash, jsonify, abort, send_file, render_template_string
from sqlite3 import IntegrityError
import tempfile
import shutil
import zipfile
import uuid
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
PUBLIC_PICTURES_FOLDER = 'static/public-pictures'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PUBLIC_PICTURES_FOLDER, exist_ok=True)
app.secret_key = 'jasdhfjasefoanvjff74809'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 





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

def init_public_rezepte_db():
    conn = sqlite3.connect('public_rezepte.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PublicRezepte (
            uuid TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            zutaten TEXT NOT NULL,
            rezept TEXT NOT NULL,
            dauer NUMBER NOT NULL,
            bild TEXT,
            user_email TEXT
        )
    ''')
    conn.commit()
    conn.close()

# HI!





def add_public_rezept_ignore_duplicates(rezept_name):
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
        recipe = cursor.fetchone()
        conn.close()

        if recipe:
            conn = sqlite3.connect('public_rezepte.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM PublicRezepte WHERE name = ? AND user_email = ?', (recipe[1], email))
            public_recipe = cursor.fetchone()

            public_uuid = str(uuid.uuid4())
            public_recipe = (
                public_uuid,
                recipe[1],  # name
                recipe[2],  # zutaten
                recipe[3],  # rezept
                recipe[4],  # dauer
                recipe[5],  # bild
                email       # user_email
            )

            # Copy the image to the public pictures folder
            if recipe[5]:
                src = os.path.join(SCRIPT_DIR, 'user', f'{email}', 'bilder', recipe[5])
                dst = os.path.join(PUBLIC_PICTURES_FOLDER, f"{public_uuid}.jpg")
                shutil.copy(src, dst)
                public_recipe = public_recipe[:-2] + (f"public-pictures/{public_uuid}.jpg", email)

            cursor.execute('INSERT INTO PublicRezepte (uuid, name, zutaten, rezept, dauer, bild, user_email) VALUES (?, ?, ?, ?, ?, ?, ?)', public_recipe)
            conn.commit()
            conn.close()
            return jsonify({'uuid': public_uuid}), 201
        else:
            return "Recipe not found", 404





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
    conn = sqlite3.connect('userdb/user.db')
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

@app.route('/public/<uuid>', methods=['GET'])
def get_public_recipe(uuid):
    conn = sqlite3.connect('public_rezepte.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM PublicRezepte WHERE uuid = ?', (uuid,))
    recipe = cursor.fetchone()
    conn.close()
    if recipe:
        # print(recipe)
        # return 'hi'
        return render_template('rezept_detail_public.html', recipe={
            'uuid': recipe[0],
            'name': recipe[1],
            'zutaten': recipe[2],
            'rezept': recipe[3],
            'dauer': recipe[4],
            'bild': recipe[5]
        })
    else:
        abort(404)

@app.route('/check-public/<rezept_name>')
def check_public(rezept_name):
    if 'email' in session:
        email = session.get('email')
        print(email)
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
        recipe = cursor.fetchone()
        conn.close()

        if recipe:
            conn = sqlite3.connect('public_rezepte.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM PublicRezepte WHERE name = ? AND user_email = ?', (recipe[1], email))
            public_recipe = cursor.fetchone()

            if public_recipe:
                return render_template('rezept_detail.html', rezept=recipe, public=True, uuid=public_recipe[0])
            else :
                add_public_rezept_ignore_duplicates(rezept_name)
                return render_template('rezept_detail.html', rezept=recipe, public=True, uuid=public_recipe[0])
        return jsonify({'error': 'Recipe not found in public database'}), 404
    return redirect(url_for('login'))

@app.route('/add-public/<rezept_name>')
def add_public_rezept(rezept_name):
    if 'email' in session:
        email = session.get('email')
        db_path = os.path.join(f'user/{email}/', 'rezepte.db')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Rezepte WHERE name = ?', (rezept_name,))
        recipe = cursor.fetchone()
        conn.close()

        if recipe:
            conn = sqlite3.connect('public_rezepte.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM PublicRezepte WHERE name = ? AND user_email = ?', (recipe[1], email))
            public_recipe = cursor.fetchone()

            if public_recipe:
                return jsonify({'error': 'Recipe already exists in public database', 'uuid': public_recipe[0]}), 409

            public_uuid = str(uuid.uuid4())
            public_recipe = (
                public_uuid,
                recipe[1],  # name
                recipe[2],  # zutaten
                recipe[3],  # rezept
                recipe[4],  # dauer
                recipe[5],  # bild
                email       # user_email
            )

            # Copy the image to the public pictures folder
            if recipe[5]:
                src = os.path.join(SCRIPT_DIR, 'user', f'{email}', 'bilder', recipe[5])
                dst = os.path.join(PUBLIC_PICTURES_FOLDER, f"{public_uuid}.jpg")
                shutil.copy(src, dst)
                public_recipe = public_recipe[:-2] + (f"public-pictures/{public_uuid}.jpg", email)

            cursor.execute('INSERT INTO PublicRezepte (uuid, name, zutaten, rezept, dauer, bild, user_email) VALUES (?, ?, ?, ?, ?, ?, ?)', public_recipe)
            conn.commit()
            conn.close()
            return jsonify({'uuid': public_uuid}), 201
        else:
            return "Recipe not found", 404
    return redirect(url_for('login'))

@app.route('/android')
def android_start():
    if 'email' in session:
        return redirect(url_for('index'))
    return render_template('android_start.html')



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


@app.route('/user/<email>/bilder/<filename>')
def serve_image(email, filename):
    # Sicherstellen, dass der Benutzer authentifiziert ist und auf sein eigenes Bild zugreift
    if 'email' not in session or session['email'] != email:
        abort(403)  # Forbidden - Wenn der Benutzer nicht eingeloggt ist oder das Bild eines anderen Benutzers anfordert

    image_path = os.path.join(f'user/{email}/bilder', filename)
    
    # Prüfen, ob die Bilddatei existiert
    if os.path.exists(image_path):
        return send_from_directory(os.path.dirname(image_path), filename)
    
    return "Bild nicht gefunden", 404


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
            UPLOAD_FOLDER = os.path.join(f'user/{email}', 'bilder')
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
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


@app.route('/setdbup')
def setdbup():
    try:
        init_db()
        init_public_rezepte_db()
        init_user_db()

    except Exception as e:
        print(e)
        return 'ERROR'

    return 'DB set up'



@app.route("/signup", methods=['GET', 'POST'])
def signup():
  if request.method == 'POST':
    email = request.form['email']
    password = request.form['password']

    try:
      conn = sqlite3.connect('userdb/user.db') 
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
        conn = sqlite3.connect('userdb/user.db')
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




@app.route('/download', methods=['GET', 'POST'])
def download():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(SCRIPT_DIR, 'userdb', 'user.db')
    BILDER_FOLDER = os.path.join(SCRIPT_DIR, 'user')
    UPLOADS_FOLDER = os.path.join(SCRIPT_DIR, 'static', 'uploads')
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'TEST_PW':
            # Create a temporary ZIP file
            zip_path = os.path.join(tempfile.gettempdir(), 'backup.zip')
            with zipfile.ZipFile(zip_path, 'w') as backup_zip:
                # Add the database file to the ZIP
                if os.path.exists(DATABASE_PATH):
                    backup_zip.write(DATABASE_PATH, arcname='user.db')
                else:
                    return "Database file not found", 404
                
                # Add the Bilder folder contents to the ZIP
                if os.path.exists(BILDER_FOLDER):
                    for root, _, files in os.walk(BILDER_FOLDER):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, SCRIPT_DIR)  # Preserve folder structure
                            backup_zip.write(file_path, arcname=arcname)

                # Add the uploads folder contents to the ZIP
                if os.path.exists(UPLOADS_FOLDER):
                    for root, _, files in os.walk(UPLOADS_FOLDER):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, SCRIPT_DIR)  # Preserve folder structure
                            backup_zip.write(file_path, arcname=arcname)
                else:
                    return "Uploads folder not found", 404

            # Send the created ZIP file as a downloadable attachment
            response = send_file(zip_path, as_attachment=True, download_name='backup.zip')
            response.call_on_close(lambda: os.remove(zip_path))  # Remove the zip file after sending
            return response
        else:
            return "Incorrect password", 403

    # HTML form rendered directly within Flask
    form_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Download Backup</title></head>
    <body>
        <h2>Enter Password to Download Backup</h2>
        <form method="POST">
            <label>Password: <input type="password" name="password"></label>
            <input type="submit" value="Download">
        </form>
    </body>
    </html>
    """
    return render_template_string(form_html)





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
    init_public_rezepte_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
