import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from datetime import datetime
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    # Fetch the user's stocks and calculate total_assets
    stocks = db.execute("SELECT symbol, quantity, total_cost FROM portfolio WHERE user_id = ?", user_id)

    # Calculate the total_assets using a list comprehension with the lookup function
    total_assets = user_cash + sum((lookup(stock["symbol"])["price"] * stock["quantity"]) for stock in stocks)

    # Create the owned_prices dictionary with symbol-price pairs
    owned_prices = {stock["symbol"]: lookup(stock["symbol"])["price"] for stock in stocks}

    return render_template("index.html", stocks=stocks, total_assets=total_assets, user_cash=user_cash, owned_price=owned_prices)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        lookedup = lookup(symbol)

        # Find the desired share and check its valid
        if lookedup != None:
            price = lookedup["price"]
            try:
                quantity = int(request.form.get("shares"))
                if quantity <= 0:
                    return apology("invalid number of shares", 400)
            except ValueError:
                return apology("invalid number of shares", 400)

            # Calculate the total cost of the purchase
            total_cost = price * quantity

            # Check if the user has enough funds to make the purchase
            user_id = session["user_id"]
            user_data = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]
            user_cash = user_data["cash"]

            # Update the user's cash in the database (subtract the total cost)
            if total_cost <= user_cash:
                updated_cash = user_cash - total_cost
                time = datetime.now()
                now = datetime.strftime(time, '%Y-%m-%d %H:%M:%S')
                db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)
                db.execute("INSERT INTO transactions (user_id, symbol, buy_sell, time, unit_cost, quantity) VALUES (?, ?, 'buy', ?, ?, ?)",
                           user_id, symbol, now, price, quantity)

                # Check if the user owns the stock
                ownedStock = db.execute("SELECT symbol, total_cost FROM portfolio WHERE user_id IS ?", user_id)
                stock = [stock["symbol"] for stock in ownedStock]
                if symbol not in stock:
                    # Insert it into the 'portfolio' table
                    db.execute("INSERT INTO portfolio (user_id, symbol, quantity, total_cost) VALUES (?, ?, ?, ?)",
                               user_id, symbol, quantity, total_cost)
                    # Redirect the user back to the index page
                    return redirect("/")

                else:
                    current_stock = db.execute("SELECT quantity, total_cost FROM portfolio WHERE user_id = ? AND symbol = ?",
                                               user_id, symbol)
                    current_quantity, current_total_cost = current_stock[0]["quantity"], current_stock[0]["total_cost"]
                    new_quantity = current_quantity + quantity
                    new_total_cost = current_total_cost + total_cost

                    current_cost = [stock["total_cost"] for stock in current_stock]
                    new_total_cost = total_cost + int(current_cost[0])
                    db.execute("UPDATE portfolio SET quantity = ?, total_cost = ? WHERE user_id = ? AND symbol = ?",
                               new_quantity, new_total_cost, user_id, symbol)

                    # Redirect the user back to the index page
                    return redirect("/")

            else:
                return apology("Not enough funds to make the purchase", 403)

        else:
            return apology("Invalid symbol", 400)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    # Fetch the user's trades
    trades = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)

    return render_template("history.html", trades=trades)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        lookedup = lookup(symbol)

        if lookedup is not None:
            price = usd(lookedup["price"])
            symbol = lookedup["symbol"]
            return render_template("quote.html", price=price, symbol=symbol)
        else:
            # return render_template("quote.html")
            return apology("Invalid symbol", 400)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    if request.method == "POST":
        new_username = request.form.get("username")

        if not request.form.get("username"):
            return apology("must provide username", 400)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # verify that the username is unique
        rows = db.execute("SELECT * FROM users WHERE username = ?", new_username)
        if len(rows) > 0:
            return apology("username is taken", 400)

        # password is not stored in any variable for security and then insert the new username and hashed password
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match", 400)
        else:
            hashed = generate_password_hash(request.form.get("password"), method='pbkdf2', salt_length=16)
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", new_username, hashed)
            return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user_id = session["user_id"]
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
    stocks = db.execute("SELECT symbol FROM portfolio WHERE user_id = ?", user_id)

    # This is master list of stock to sell
    liStocks = (stock["symbol"] for stock in stocks)

    if request.method == "GET":
        return render_template("sell.html", stocks=liStocks, user_cash=user_cash)

    elif request.method == "POST":
        symbol = request.form.get("symbol")
        # Protrect from user editing the Select input with dev tools
        if symbol not in liStocks:
            return apology("You dont own that!", 400)

        # Set quantity, price and sale value
        quantity = float(request.form.get("shares"))
        price = lookup(symbol)["price"]
        sale_value = quantity * price

        # Set up list of the cost and quantity for owned stock
        current_status = db.execute("SELECT total_cost, quantity FROM portfolio WHERE user_id = ? AND symbol = ?", user_id, symbol)
        current_value = current_status[0]['total_cost']
        owned = current_status[0]['quantity']

        # Verify that quantity is enough to sell
        if quantity <= owned:
            new_value = current_value - sale_value
            current_quantity = current_status[0]['quantity']
            updated_quantity = current_quantity - quantity

            # Delete "0 shares" lines or update quantity
            if updated_quantity == 0:
                db.execute("DELETE FROM portfolio WHERE user_id = ? AND symbol = ?",
                           user_id, symbol)
            else:
                db.execute("UPDATE portfolio SET quantity = ?, total_cost = ? WHERE user_id = ? AND symbol = ?",
                           updated_quantity, new_value, user_id, symbol)

            # Update cash in user db, set up registry of transaction
            updated_cash = user_cash + sale_value
            db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)
            time = datetime.now()
            now = datetime.strftime(time, '%Y-%m-%d %H:%M:%S')
            db.execute("INSERT INTO transactions (user_id, symbol, buy_sell, time, unit_cost, quantity) VALUES (?, ?, 'sell', ?, ?, ?)",
                       user_id, symbol, now, price, quantity)

            flash("Sold!")

            return redirect("/")
        else:
            return apology("Trying to sell too many shares", 400)