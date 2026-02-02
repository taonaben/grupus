import psycopg2


def main():
    conn = psycopg2.connect('postgres://avnadmin:AVNS_-mO2Z1a6ZqqW9EHFpMx@pg-2711f371-bakeryerp.d.aivencloud.com:16091/defaultdb?sslmode=require')

    query_sql = 'SELECT VERSION()'

    cur = conn.cursor()
    cur.execute(query_sql)

    version = cur.fetchone()[0]
    print(version)


if __name__ == "__main__":
    main()