from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime
import geocoder

app = Flask(__name__)
app.secret_key = "e0l2n5v4"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

geolocator = Nominatim(user_agent="myapp")

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    fname = db.Column(db.String(150))
    lname = db.Column(db.String(150))
    email = db.Column(db.String(150))
    pword = db.Column(db.String(150))
    events = db.relationship("Event", backref = "user")

    def __init__(self, _fname, _lname, _email, _pword):
        self.fname = _fname
        self.lname = _lname
        self.email = _email
        self.pword = _pword

class Event(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    userid = db.Column(db.Integer, db.ForeignKey("user.id"))
    cause = db.Column(db.String(500))
    description = db.Column(db.String(5000))
    addr = db.Column(db.String(500))
    addr_lat = db.Column(db.Float())
    addr_long = db.Column(db.Float())
    date = db.Column(db.DateTime)

    def __init__(self, _userid, _cause, _description, _addr, _addr_lat, _addr_long, _date):
        self.userid = _userid
        self.cause = _cause
        self.description = _description
        self.addr = _addr
        self.addr_lat = _addr_lat
        self.addr_long = _addr_long
        self.date = _date

@app.route("/")
def main():
    return render_template("main.html")

@app.route("/explore/")
def home():
    if "email" in session:
        fname = session["fname"]
        lname = session["lname"]
        email = session["email"]
        foundUser = User.query.filter_by(email = email).first()
        allEvents = Event.query.all()

        latlng = geocoder.ip("me").latlng
        coor = (latlng[0], latlng[1])
        nearby = []
        for e in allEvents:
            coor_e = (e.addr_lat, e.addr_long)
            if float(geodesic(coor, coor_e).kilometers) < 20:
                nearby.append(e)

        return render_template("home.html", fname = fname, lname = lname, events = foundUser.events, nearby_events = nearby)
    else:
        return redirect(url_for("login"))

@app.route("/login/", methods = ["GET", "POST"])
def login():
    if "email" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form["em"]
        pword = request.form["pw"]

        foundUser = User.query.filter_by(email = email).first()
        if foundUser:
            if pword == foundUser.pword:
                session["fname"] = foundUser.fname
                session["lname"] = foundUser.lname
                session["email"] = foundUser.email
                session["id"] = foundUser.id
                return redirect(url_for("home"))
            else:
                flash("Incorrect email or password!")
                return redirect(url_for("login"))
        else:
            flash("Incorrect email or password!")
            return redirect(url_for("login"))
    else:
        return render_template("login.html")

@app.route("/signup/", methods = ["GET", "POST"])
def signup():
    if request.method == "POST":
        fname = request.form["fn"]
        lname = request.form["ln"]
        email = request.form["em"]
        pword = request.form["pw"]
        rpword = request.form["rpw"]

        if pword != rpword:
            flash("Passwords do not match!", "error")
            return redirect(url_for("signup"))
        
        foundUser = User.query.filter_by(email = email).first()
        if foundUser:
            flash("An account already exists under this email!", "error")
            return redirect(url_for("signup"))
        
        newuser = User(fname, lname, email, pword)
        db.session.add(newuser)
        db.session.commit()
        return redirect(url_for("home"))
    else:
        return render_template("signup.html")

@app.route("/newevent/", methods = ["GET", "POST"])
def newevent():
    if not "email" in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        cause = request.form["cs"]
        description = request.form["ds"]
        addr = request.form["ad"]
        loc = geolocator.geocode(str(addr))

        if loc == None:
            flash("Address not found!", "error")
            return redirect(url_for("signup"))
        
        addr_lat = loc.latitude
        addr_long = loc.longitude
        date = datetime.strptime(str(request.form["dt"]), "%Y-%m-%d")
        userid = session["id"]
        foundUser = User.query.filter_by(email = session["email"]).first()

        newevent = Event(userid, cause, description, addr, addr_lat, addr_long, date)
        db.session.add(newevent)
        foundUser.events.append(newevent)
        db.session.commit()

        return redirect(url_for("event", event_id = newevent.id))
    else:
        email = session["email"]
        foundUser = User.query.filter_by(email = email).first()
        return render_template("newevent.html", fname = foundUser.fname, lname = foundUser.lname, events = foundUser.events)

@app.route("/event/<event_id>")
def event(event_id):
    foundEvent = Event.query.filter_by(id = event_id).first()
    foundUser = User.query.filter_by(id = foundEvent.userid).first()
    fname = ""
    lname = ""
    events = []
    if "email" in session:
        currUser = User.query.filter_by(email = session["email"]).first()
        fname = currUser.fname
        lname = currUser.lname
        events = currUser.events
    return render_template("event.html", fname = fname, lname = lname, events = events, user = str(foundUser.fname + " " + foundUser.lname), cause = foundEvent.cause, description = foundEvent.description, addr = foundEvent.addr, addr_lat = foundEvent.addr_lat, addr_long = foundEvent.addr_long, date = foundEvent.date.strftime("%d %B, %Y"))

@app.route("/debug/")
def debug():
    foundUser = User.query.filter_by(email = session["email"]).first()
    print(len(foundUser.events))
    return f"<h1>debugging page</h1>"

if __name__ == "__main__":
    db.create_all()
    app.run()