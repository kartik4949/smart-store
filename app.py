# imports - standard imports
import os
import json
import sqlite3

# imports - third party imports
from flask import Flask, url_for, request, redirect
from flask import render_template as render

import requests


def sendtext(text):
    url = "https://www.fast2sms.com/dev/bulk"
    payload = (
        f"sender_id=FSTSMS&message={text}&language=english&route=p&numbers=9545593232"
    )
    headers = {
        "authorization": "z8h9b7THMNcvUeoBqPGdVnRxX6mJYCuIQW1rysOjfwg45FZaiKKR0kTxyYr2ZOwdtJgHnQ8LVojGicv1",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }
    response = requests.request("POST", url, data=payload, headers=headers)
    print(response.text)


# global constants
DATABASE_NAME = "inventory.sqlite"
BILL_DATABASE_NAME = "bills.sqlite"
bills_stack = []
prices = []


class bill:
    price = 0
    qty = 0
    item_name = ""
    prod_id = 0
    rate = 0


# setting up Flask instance
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY="dev",
    DATABASE=os.path.join(app.instance_path, "database", DATABASE_NAME),
)

# listing views
link = {x: x for x in ["location", "product", "movement", "bills", "invoice"]}
link["index"] = "/"


def init_database():
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    # initialize page content
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS products(prod_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prod_name TEXT UNIQUE NOT NULL,
                    prod_quantity INTEGER NOT NULL,
                    unallocated_quantity INTEGER);
    """
    )
    cursor.execute(
        """
    CREATE TRIGGER IF NOT EXISTS default_prod_qty_to_unalloc_qty
                    AFTER INSERT ON products
                    FOR EACH ROW
                    WHEN NEW.unallocated_quantity IS NULL
                    BEGIN
                        UPDATE products SET unallocated_quantity  = NEW.prod_quantity WHERE rowid = NEW.rowid;
                    END;

    """
    )

    # initialize page content
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS location(loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                 loc_name TEXT UNIQUE NOT NULL);
    """
    )

    # initialize page content
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS logistics(trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                prod_id INTEGER NOT NULL,
                                from_loc_id INTEGER NULL,
                                to_loc_id INTEGER NULL,
                                prod_quantity INTEGER NOT NULL,
                                trans_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(prod_id) REFERENCES products(prod_id),
                                FOREIGN KEY(from_loc_id) REFERENCES location(loc_id),
                                FOREIGN KEY(to_loc_id) REFERENCES location(loc_id));
    """
    )

    # initialize page content
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS bills(bill_id INTEGER UNIQUE PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    client_number INTEGER UNIQUE NOT NULL,
                    trans_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
    """
    )
    # initialize page content
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS bill_items(bill_id INTEGER NOT NULL,
                                prod_id INTEGER NOT NULL,
                                item_name TEXT NOT NULL,
                                qty INTEGER NOT NULL,
                                rate INTEGER NOT NULL,
                                price INTEGER NOT NULL,
                                FOREIGN KEY(bill_id) REFERENCES bills(bill_id)
                                );
    """
    )

    db.commit()


@app.route("/")
def summary():
    init_database()
    msg = None
    q_data, warehouse, products = None, None, None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM location")
        warehouse = cursor.fetchall()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.execute(
            """
        SELECT prod_name, unallocated_quantity, prod_quantity FROM products
        """
        )
        q_data = cursor.fetchall()
        cursor.execute(
            """
        SELECT bill_id, client_name,client_number, trans_time FROM bills
        """
        )
        bills_data = cursor.fetchall()
        cursor.execute(
            """
        SELECT * FROM bill_items
        """
        )
        bill_items_data = cursor.fetchall()

    except sqlite3.Error as e:
        msg = f"An error occurred: {e.args[0]}"
    if msg:
        print(msg)

    return render(
        "index.html",
        link=link,
        title="Summary",
        bills=bills_data,
        warehouse=warehouse,
        bill_items=bill_items_data,
        products=products,
        database=q_data,
    )


@app.route("/product", methods=["POST", "GET"])
def product():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    if request.method == "POST":
        prod_name = request.form["prod_name"]
        quantity = request.form["prod_quantity"]

        transaction_allowed = False
        prod_name = prod_name.strip().lower()
        if prod_name not in ["", " ", None]:
            if quantity not in ["", " ", None]:
                transaction_allowed = True
        sql = "SELECT * FROM products WHERE prod_name =?"
        cursor.execute(sql, (prod_name,))
        prod_name_exits = cursor.fetchall()
        if len(prod_name_exits):
            print("Already Added.")

        if transaction_allowed and not len(prod_name_exits):
            try:
                cursor.execute(
                    "INSERT INTO products (prod_name, prod_quantity) VALUES (?, ?)",
                    (prod_name, quantity),
                )
                db.commit()
            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = f"{prod_name} added successfully"

            if msg:
                print(msg)

            return redirect(url_for("product"))

    return render(
        "product.html",
        link=link,
        products=products,
        transaction_message=msg,
        title="Products Log",
    )


@app.route("/invoice", methods=["POST", "GET"])
def invoice():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM location")
    warehouse_data = cursor.fetchall()
    print(request.method)

    if request.method == "POST":
        print(request.form)
        warehouse_name = request.form["warehouse_name"]

        transaction_allowed = False
        if warehouse_name not in ["", " ", None]:
            transaction_allowed = True

        if transaction_allowed:
            try:
                cursor.execute(
                    "INSERT INTO location (loc_name) VALUES (?)", (warehouse_name,)
                )
                db.commit()
            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = f"{warehouse_name} added successfully"

            if msg:
                print(msg)

            return redirect(url_for("location"))

    return render(
        "invoice.html",
        link=link,
        warehouses=warehouse_data,
        transaction_message=msg,
        title="Warehouse Locations",
    )


@app.route("/location", methods=["POST", "GET"])
def location():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM location")
    warehouse_data = cursor.fetchall()

    if request.method == "POST":
        warehouse_name = request.form["warehouse_name"]

        transaction_allowed = False
        if warehouse_name not in ["", " ", None]:
            transaction_allowed = True

        if transaction_allowed:
            try:
                cursor.execute(
                    "INSERT INTO location (loc_name) VALUES (?)", (warehouse_name,)
                )
                db.commit()
            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = f"{warehouse_name} added successfully"

            if msg:
                print(msg)

            return redirect(url_for("location"))

    return render(
        "location.html",
        link=link,
        warehouses=warehouse_data,
        transaction_message=msg,
        title="Warehouse Locations",
    )


@app.route("/movement", methods=["POST", "GET"])
def movement():
    init_database()
    msg = None
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    cursor.execute("SELECT * FROM logistics")
    logistics_data = cursor.fetchall()

    # add suggestive content for page
    cursor.execute("SELECT prod_id, prod_name, unallocated_quantity FROM products")
    products = cursor.fetchall()

    cursor.execute("SELECT loc_id, loc_name FROM location")
    locations = cursor.fetchall()

    log_summary = []
    for p_id in [x[0] for x in products]:
        cursor.execute("SELECT prod_name FROM products WHERE prod_id = ?", (p_id,))
        temp_prod_name = cursor.fetchone()

        for l_id in [x[0] for x in locations]:
            cursor.execute("SELECT loc_name FROM location WHERE loc_id = ?", (l_id,))
            temp_loc_name = cursor.fetchone()

            cursor.execute(
                """
            SELECT SUM(log.prod_quantity)
            FROM logistics log
            WHERE log.prod_id = ? AND log.to_loc_id = ?
            """,
                (p_id, l_id),
            )
            sum_to_loc = cursor.fetchone()

            cursor.execute(
                """
            SELECT SUM(log.prod_quantity)
            FROM logistics log
            WHERE log.prod_id = ? AND log.from_loc_id = ?
            """,
                (p_id, l_id),
            )
            sum_from_loc = cursor.fetchone()

            if sum_from_loc[0] is None:
                sum_from_loc = (0,)
            if sum_to_loc[0] is None:
                sum_to_loc = (0,)

            log_summary += [
                (temp_prod_name + temp_loc_name + (sum_to_loc[0] - sum_from_loc[0],))
            ]

    # CHECK if reductions are calculated as well!
    # summary data --> in format:
    # {'Asus Zenfone 2': {'Mahalakshmi': 50, 'Gorhe': 50},
    # 'Prada watch': {'Malad': 50, 'Mahalakshmi': 115}, 'Apple iPhone': {'Airoli': 75}}
    alloc_json = {}
    for row in log_summary:
        try:
            if row[1] in alloc_json[row[0]].keys():
                alloc_json[row[0]][row[1]] += row[2]
            else:
                alloc_json[row[0]][row[1]] = row[2]
        except (KeyError, TypeError):
            alloc_json[row[0]] = {}
            alloc_json[row[0]][row[1]] = row[2]
    alloc_json = json.dumps(alloc_json)

    if request.method == "POST":
        # transaction times are stored in UTC
        prod_name = request.form["prod_name"]
        from_loc = request.form["from_loc"]
        to_loc = request.form["to_loc"]
        quantity = request.form["quantity"]

        # if no 'from loc' is given, that means the product is being shipped to a warehouse (init condition)
        if from_loc in [None, "", " "]:
            try:
                cursor.execute(
                    """
                    INSERT INTO logistics (prod_id, to_loc_id, prod_quantity) 
                    SELECT products.prod_id, location.loc_id, ? 
                    FROM products, location 
                    WHERE products.prod_name == ? AND location.loc_name == ?
                """,
                    (quantity, prod_name, to_loc),
                )

                # IMPORTANT to maintain consistency
                cursor.execute(
                    """
                UPDATE products 
                SET unallocated_quantity = unallocated_quantity - ? 
                WHERE prod_name == ?
                """,
                    (quantity, prod_name),
                )
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"

        elif to_loc in [None, "", " "]:
            print("To Location wasn't specified, will be unallocated")
            try:
                cursor.execute(
                    """
                INSERT INTO logistics (prod_id, from_loc_id, prod_quantity) 
                SELECT products.prod_id, location.loc_id, ? 
                FROM products, location 
                WHERE products.prod_name == ? AND location.loc_name == ?
                """,
                    (quantity, prod_name, from_loc),
                )

                # IMPORTANT to maintain consistency
                cursor.execute(
                    """
                UPDATE products 
                SET unallocated_quantity = unallocated_quantity + ? 
                WHERE prod_name == ?
                """,
                    (quantity, prod_name),
                )
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"

        # if 'from loc' and 'to_loc' given the product is being shipped between warehouses
        else:
            try:
                cursor.execute(
                    "SELECT loc_id FROM location WHERE loc_name == ?", (from_loc,)
                )
                from_loc = "".join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute(
                    "SELECT loc_id FROM location WHERE loc_name == ?", (to_loc,)
                )
                to_loc = "".join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute(
                    "SELECT prod_id FROM products WHERE prod_name == ?", (prod_name,)
                )
                prod_id = "".join([str(x[0]) for x in cursor.fetchall()])

                cursor.execute(
                    """
                INSERT INTO logistics (prod_id, from_loc_id, to_loc_id, prod_quantity)
                VALUES (?, ?, ?, ?)
                """,
                    (prod_id, from_loc, to_loc, quantity),
                )
                db.commit()

            except sqlite3.Error as e:
                msg = f"An error occurred: {e.args[0]}"
            else:
                msg = "Transaction added successfully"

        # print a transaction message if exists!
        if msg:
            print(msg)
            return redirect(url_for("movement"))

    return render(
        "movement.html",
        title="ProductMovement",
        link=link,
        trans_message=msg,
        products=products,
        locations=locations,
        allocated=alloc_json,
        logs=logistics_data,
        database=log_summary,
    )


@app.route("/delete")
def delete():
    type_ = request.args.get("type")
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if type_ == "location":
        id_ = request.args.get("loc_id")

        cursor.execute(
            "SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE to_loc_id = ? GROUP BY prod_id",
            (id_,),
        )
        in_place = cursor.fetchall()

        cursor.execute(
            "SELECT prod_id, SUM(prod_quantity) FROM logistics WHERE from_loc_id = ? GROUP BY prod_id",
            (id_,),
        )
        out_place = cursor.fetchall()

        # converting list of tuples to dict
        in_place = dict(in_place)
        out_place = dict(out_place)

        # print(in_place, out_place)
        all_place = {}
        for x in in_place.keys():
            if x in out_place.keys():
                all_place[x] = in_place[x] - out_place[x]
            else:
                all_place[x] = in_place[x]
        # print(all_place)

        for products_ in all_place.keys():
            cursor.execute(
                """
            UPDATE products SET unallocated_quantity = unallocated_quantity + ? WHERE prod_id = ?
            """,
                (all_place[products_], products_),
            )

        cursor.execute("DELETE FROM location WHERE loc_id == ?", str(id_))
        db.commit()

        return redirect(url_for("location"))

    elif type_ == "product":
        id_ = request.args.get("prod_id")
        cursor.execute("DELETE FROM products WHERE prod_id == ?", (str(id_),))
        db.commit()

        return redirect(url_for("product"))


@app.route("/print_invoice", methods=["POST", "GET"])
def print_invoice():
    type_ = request.args.get("type")
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if request.method == "POST":
        prod_id = request.form["prod_id"]
        prod_name = request.form["prod_name"]
        prod_quantity = request.form["prod_quantity"]
        prod_name = prod_name.strip().lower()

        if prod_name:
            cursor.execute(
                "UPDATE products SET prod_name = ? WHERE prod_id == ?",
                (prod_name, str(prod_id)),
            )
        if prod_quantity:
            cursor.execute(
                "SELECT prod_quantity FROM products WHERE prod_id = ?", (prod_id,)
            )
            old_prod_quantity = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE products SET prod_quantity = ?, unallocated_quantity =  unallocated_quantity + ? - ?"
                "WHERE prod_id == ?",
                (prod_quantity, prod_quantity, old_prod_quantity, str(prod_id)),
            )
        db.commit()

        return redirect(url_for("product"))

    return render(url_for(type_))


@app.route("/edit", methods=["POST", "GET"])
def edit():
    type_ = request.args.get("type")
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()

    if type_ == "location" and request.method == "POST":
        loc_id = request.form["loc_id"]
        loc_name = request.form["loc_name"]

        if loc_name:
            cursor.execute(
                "UPDATE location SET loc_name = ? WHERE loc_id == ?",
                (loc_name, str(loc_id)),
            )
            db.commit()

        return redirect(url_for("location"))

    if type_ == "bills" and request.method == "POST":
        return redirect(url_for("bills"))

    elif type_ == "product" and request.method == "POST":
        prod_id = request.form["prod_id"]
        prod_name = request.form["prod_name"]
        prod_quantity = request.form["prod_quantity"]
        prod_name = prod_name.strip().lower()

        if prod_name:
            cursor.execute(
                "UPDATE products SET prod_name = ? WHERE prod_id == ?",
                (prod_name, str(prod_id)),
            )
        if prod_quantity:
            cursor.execute(
                "SELECT prod_quantity FROM products WHERE prod_id = ?", (prod_id,)
            )
            old_prod_quantity = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE products SET prod_quantity = ?, unallocated_quantity =  unallocated_quantity + ? - ?"
                "WHERE prod_id == ?",
                (prod_quantity, prod_quantity, old_prod_quantity, str(prod_id)),
            )
        db.commit()

        return redirect(url_for("product"))

    return render(url_for(type_))


@app.route("/bills", methods=["POST", "GET"])
def bills():
    type_ = request.args.get("type")
    db = sqlite3.connect(DATABASE_NAME)
    cursor = db.cursor()
    if request.method == "GET":
        global bills_stack
        global prices

    if request.method == "POST":
        if type_ == "add_item_bill":
            cursor.execute(
                "SELECT prod_quantity FROM products WHERE prod_id == ?",
                (request.form["prod_id"],),
            )
            qty_left = cursor.fetchall()[0][0]
            if qty_left < int(request.form["qty"]):
                error_qty = f"Only {qty_left} items left"
                print(error_qty)
                return render(
                    "bills.html",
                    link=link,
                    total=sum(prices),
                    bills=bills_stack,
                    transaction_message=error_qty,
                    title="Bills",
                )
            else:
                bills_stack.append(
                    (
                        request.form["prod_id"],
                        request.form["item_name"],
                        request.form["qty"],
                        request.form["rate"],
                        request.form["price"],
                    )
                )
                prices.append(int(request.form["price"]))

        if type_ == "save":
            button_type = request.form["button-type"]
            client_name = request.form["client_name"]
            client_number = request.form["client_number"]

            sql_insert = (
                "INSERT or IGNORE INTO bills (client_name, client_number) VALUES (?, ?)"
            )
            cursor.execute(
                sql_insert, (request.form["client_name"], request.form["client_number"])
            )
            cursor.execute("SELECT * FROM bills")
            bills_data = cursor.fetchall()
            bill_id = bills_data[-1][0]
            alert_msg_dict = {}
            for items in bills_stack:
                cursor.execute(
                    "SELECT prod_quantity FROM products WHERE prod_id == ?", (items[0],)
                )
                qty_left = cursor.fetchall()[0][0]
                sql_insert_items = "INSERT INTO bill_items (bill_id , prod_id , item_name,qty,rate,price) VALUES (? , ? ,? ,? ,? ,?)"
                cursor.execute(
                    sql_insert_items,
                    (bill_id, items[0], items[1], items[2], items[3], items[4]),
                )
                updated_qty = int(qty_left) - int(items[2])
                if updated_qty < 2:
                    alert_msg_dict.update({items[1]:updated_qty})
                sql_product_table_update = (
                    "UPDATE products SET prod_quantity = ? WHERE prod_id == ?"
                )
                cursor.execute(sql_product_table_update, (updated_qty, items[0]))
            _bills_stack = bills_stack
            _prices = prices
            try:
                if len(alert_msg_dict):
                    text = [str(item) +" Only " + str(qty) + "left!!" for item,qty in alert_msg_dict.items()]
                    text.insert(0, "Alert!!")
                    sendtext("\n".join(text))
                db.commit()
            except:
                print("error in commit")
            else:
                bills_stack = []
                prices = []
            if button_type == "print":

                return render(
                    "invoice.html",
                    client_name=client_name,
                    link=link,
                    bills=_bills_stack,
                    transaction_message=None,
                    title="Bills",
                )

    return render(
        "bills.html",
        link=link,
        total=sum(prices),
        bills=bills_stack,
        transaction_message=None,
        title="Bills",
    )
