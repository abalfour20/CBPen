from flask import Flask, render_template, request, jsonify, url_for, redirect, flash
from controller import get_port_view, get_service_view, get_subdomain_view, get_multiple_view
from configurations import get_allowed_sites, get_contributors, \
    get_terms, get_policies, get_scan_types, get_vm_urls
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

app = Flask(__name__)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'cloudblazers'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "signin"


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()

        if existing_user_username:
            raise ValidationError("Username already exists! Please choose another one.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField("Login")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


@app.route('/home')
@login_required
def index():
    return render_template('index.html')


@app.route('/multiple', methods=['GET', 'POST'])
@login_required
def get_multiple():
    scan_types = get_scan_types()
    if request.method == "POST":
        ip_addresses = [s.strip() for s in request.form["ip_addresses"].split(",")]
        virtual_machines = [s.strip() for s in get_vm_urls()]
        scan_type = request.form["scan_type"]
        # To get results in non parallel execution add parallel=False to the following method call
        data = get_multiple_view(ip_addresses, virtual_machines, scan_type)

        return render_template(
            'multiple.html',
            scan_types=scan_types,
            data=data
        )
    else:
        return render_template('multiple.html', scan_types=scan_types)


@app.route('/portsjson', methods=['GET'])
def get_ports_json():
    site = request.args.get('site', default='', type=str)
    if site != "":
        return jsonify(get_port_view(site))


@app.route('/ports', methods=['GET', 'POST'])
@login_required
def get_ports():
    sites = get_allowed_sites()
    if request.method == "POST":
        site = request.form["site"]
        data = get_port_view(site)
        return render_template(
            'ports.html',
            sites=sites,
            site=site,
            hosts=data["hosts"],
            total_time=data["total_time"]
        )
    return render_template('ports.html', sites=sites)


@app.route('/servicesjson', methods=['GET'])
def get_services_json():
    site = request.args.get('site', default='', type=str)
    if site != "":
        return jsonify(get_service_view(site))


@app.route('/services', methods=['GET', 'POST'])
@login_required
def get_services():
    sites = get_allowed_sites()
    if request.method == "POST":
        site = request.form["site"]
        data = get_service_view(site)
        return render_template(
            'services.html',
            sites=sites,
            site=site,
            hosts=data["hosts"],
            total_time=data["total_time"]
        )
    return render_template('services.html', sites=sites)


@app.route('/subdomainsjson', methods=['GET'])
def get_subdomains_ssl_json():
    site = request.args.get('site', default='', type=str)
    if site != "":
        return jsonify(get_subdomain_view(site))


@app.route('/subdomains', methods=['GET', 'POST'])
@login_required
def get_subdomains_ssl():
    sites = get_allowed_sites()
    if request.method == "POST":
        site = request.form["site"]
        data = get_subdomain_view(site)
        return render_template(
            'subdomains.html',
            sites=sites,
            site=site,
            total_time=data["total_time"],
            subdomains=data["subdomains"],
            ssl_certificates=data["ssl_certificates"]
        )
    return render_template('subdomains.html', sites=sites)


@app.route('/about')
@login_required
def about():
    contributors = get_contributors()
    return render_template('about.html', contributors=contributors)


@app.route('/', methods=['GET', 'POST'])
def signin():
    form = LoginForm()
    if request.method == "POST":
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user:
                if bcrypt.check_password_hash(user.password, form.password.data):
                    login_user(user)
                    return redirect(url_for('index'))
                else:
                    flash('Username and password does not match', 'error')
            else:
                flash('No user is found with the username', 'error')
        return render_template('signin.html', form=form)
    else:
        return render_template('signin.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        try:
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
        except Exception as ex:
            print(str(ex))
            flash('Error in registration', 'error')
    return render_template('signup.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('signin'))


@app.route('/terms')
@login_required
def terms():
    our_terms = get_terms()
    policies = get_policies()
    return render_template('terms.html', terms=our_terms, policies=policies)
