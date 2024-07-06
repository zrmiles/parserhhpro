from flask import Flask, request, jsonify, render_template, redirect, url_for
import psycopg2
import requests
import math
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

DB_HOST = os.getenv('DB_HOST', 'db')
DB_NAME = os.getenv('DB_NAME', 'vacancies')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')

base_url = 'https://api.hh.ru/vacancies'
headers = {
    'Authorization': 'Bearer USERU4IN27K9Q2E5418O7438NC6GKJS896LPPH3FQOK2RD6F80004L83TOG8I1L7',
    'Content-Type': 'application/json'
}

def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        raise e

def create_vacancies_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            salary_from INTEGER,
            salary_to INTEGER,
            currency VARCHAR(10),
            url TEXT,
            region_id INTEGER,
            region VARCHAR(255),
            experience VARCHAR(255),
            employment VARCHAR(255)
        )
    """)

def insert_vacancy(cursor, name, company, salary_from, salary_to, currency, url, region_id, region, experience, employment):
    print(f"Inserting vacancy: {name}, {company}")
    cursor.execute(
        """
        INSERT INTO vacancies (name, company, salary_from, salary_to, currency, url, region_id, region, experience, employment) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (name, company, salary_from, salary_to, currency, url, region_id, region, experience, employment)
    )
    print(f"Inserted vacancy: {name}, {company}")

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering index page: {e}")
        return str(e)

@app.route('/search', methods=['POST'])
def search_vacancies():
    keyword = request.form.get('keyword')
    if not keyword:
        return jsonify({"error": "Keyword is required"}), 400

    params = {
        'text': keyword,
        'per_page': 100,
        'page': 0
    }

    try:
        conn = connect_to_db()
        cursor = conn.cursor()
        create_vacancies_table(cursor)

        # Очистка таблицы перед вставкой новых данных
        cursor.execute("TRUNCATE TABLE vacancies RESTART IDENTITY")

        total_saved = 0
        while params['page'] * params['per_page'] < 2000:
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code != 200:
                return jsonify({"error": f"API request failed with status {response.status_code}"}), 400

            data = response.json()
            vacancies = data.get('items', [])
            if not vacancies:
                break

            for vacancy in vacancies:
                try:
                    name = vacancy.get('name')
                    company = vacancy.get('employer', {}).get('name')
                    salary = vacancy.get('salary', {})
                    salary_from = salary.get('from')
                    salary_to = salary.get('to')
                    currency = salary.get('currency')
                    url = vacancy.get('alternate_url')
                    region_id = vacancy.get('area', {}).get('id')
                    region = vacancy.get('area', {}).get('name')
                    experience = vacancy.get('experience', {}).get('name')
                    employment = vacancy.get('employment', {}).get('name')

                    if None in [name, company, url]:
                        continue

                    insert_vacancy(cursor, name, company, salary_from, salary_to, currency, url, region_id, region, experience, employment)
                except Exception as e:
                    print(f"Error processing vacancy: {vacancy}")
                    print(f"Exception: {e}")

            conn.commit()
            total_saved += len(vacancies)
            params['page'] += 1

        cursor.close()
        conn.close()
        print(f"Total saved: {total_saved}")
        return redirect(url_for('show_vacancies', page=1))
    except Exception as e:
        print(f"Error during search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/results')
def show_vacancies():
    try:
        page = request.args.get('page', 1, type=int)
        limit = 10
        offset = (page - 1) * limit

        filters = {
            'salary_from': request.args.get('salary_from'),
            'salary_to': request.args.get('salary_to'),
            'region': request.args.get('region'),
            'experience': request.args.get('experience'),
            'keyword': request.args.get('keyword'),
            'currency': request.args.get('currency')
        }

        conn = connect_to_db()
        cursor = conn.cursor()
        
        query = "SELECT name, company, salary_from, salary_to, currency, url, region, experience, employment FROM vacancies WHERE 1=1"
        params = []
        
        if filters['salary_from']:
            query += " AND salary_from >= %s"
            params.append(filters['salary_from'])
        if filters['salary_to']:
            query += " AND salary_to <= %s"
            params.append(filters['salary_to'])
        if filters['region']:
            query += " AND region ILIKE %s"
            params.append(f"%{filters['region']}%")
        if filters['experience']:
            query += " AND experience ILIKE %s"
            params.append(f"%{filters['experience']}%")
        if filters['keyword']:
            query += " AND name ILIKE %s"
            params.append(f"%{filters['keyword']}%")
        if filters['currency']:
            query += " AND currency ILIKE %s"
            params.append(f"%{filters['currency']}%")
        
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        vacancies = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM vacancies WHERE 1=1")
        total_vacancies = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        total_pages = math.ceil(total_vacancies / limit)
        return render_template('results.html', vacancies=vacancies, page=page, total_pages=total_pages)
    except Exception as e:
        print(f"Error fetching vacancies: {e}")
        return str(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
