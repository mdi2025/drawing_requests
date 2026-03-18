from db_handler import db

def test():
    print("Testing Return Query Style (With Params):")
    # Using a real table to be safe
    query = "SELECT DATE_FORMAT(now(), '%%d-%%m-%%Y %%H:%%i') as ts FROM drawing_users WHERE id = %s"
    res = db.fetch_all(query, (1,))
    if res:
        print("Result (Double %% + Params):", res[0]['ts'])
    else:
        print("Result (Double %% + Params): NO DATA (check if id=1 exists)")

    query2 = "SELECT DATE_FORMAT(now(), '%d-%m-%Y %H:%i') as ts FROM drawing_users WHERE id = %s"
    try:
        res2 = db.fetch_all(query2, (1,))
        if res2:
            print("Result (Single % + Params):", res2[0]['ts'])
    except Exception as e:
        print("Result (Single % + Params): ERROR", e)

if __name__ == "__main__":
    test()
