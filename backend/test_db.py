import psycopg2


def main():
    conn = psycopg2.connect(
        "dbname=grupus user=postgres password=postgres host=localhost port=5432"
    )

    query_sql = "SELECT VERSION()"

    cur = conn.cursor()
    cur.execute(query_sql)

    version = cur.fetchone()[0]
    print(version)


if __name__ == "__main__":
    main()
