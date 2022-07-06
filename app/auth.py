import string
import zlib
from base64 import b64decode
import face_recognition
import validators
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from app import db
from .models import UserModel
from .misc import writeImg

auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    return render_template("login.html")


@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = UserModel.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))

        # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('profile'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@auth.route('/register')
def register():
    return render_template("register.html")


@auth.route('/register', methods=['POST'])
def register_post():
    register_post.voterno = request.form.get('voterno')
    register_post.email = request.form.get('email')
    register_post.name = request.form.get('name')
    register_post.password1 = request.form.get('password1')
    register_post.password2 = request.form.get('password2')

    user = UserModel.query.filter_by(email=register_post.email).first()  # if this returns a user, email already exists in db
    voter_no = UserModel.query.filter_by(voter_num=register_post.voterno).first()

    error = False
    # if a user or roll no is found, we want to redirect to signup page 
    if user:
        flash('Email address already exists.', 'error')
        error = True

    if voter_no:
        flash('Voter number already exists', 'error')
        error = True

    if register_post.password1 != register_post.password2:  # if passwords do not match, redirect
        flash('Passwords do not match. Please try again.', 'error')
        error = True

    if (len(register_post.password1) or len(register_post.password2)) < 8:
        flash('Password too short. Should be atleast 8 characters.', 'error')
        error = True

    if not validators.email(register_post.email):
        flash('Enter a valid email', 'error')
        error = True

    if not set(register_post.name).issubset(string.ascii_letters + " "):
        flash('Name can only contain alphabets.', 'error')
        error = True

    if not 10000000 <= int(register_post.voterno) < 99999999:
        flash('Roll Number is not valid. Should be 8 digits.', 'error')
        error = True

    if error:
        return redirect(url_for('auth.register'))
    else:
        return redirect(url_for('auth.facesetup'))


@auth.route("/facesetup", methods=['GET', 'POST'])
def facesetup():
    if request.method == "POST":

        encoded_image = (request.form.get("pic") + "==").encode('utf-8')

        new_image_handle = open('./app/static/face/' + str(register_post.voterno) + '.jpg', 'wb')

        new_image_handle.write(writeImg(encoded_image))
        new_image_handle.close()
        image_of_bill = face_recognition.load_image_file('./app/static/face/' + str(register_post.voterno) + '.jpg')
        try:
            bill_face_encoding = face_recognition.face_encodings(image_of_bill)[0]
        except:
            return render_template("face.html", message=1)

        new_user = UserModel(voter_num=register_post.voterno, email=register_post.email, name=register_post.name,
                             password=generate_password_hash(register_post.password1, method='sha256'), photo='/app/static/face/' + str(register_post.voterno) + '.jpg')
        db.session.add(new_user)
        db.session.commit()
        flash('User successfully registered.', 'success')
        return redirect(url_for('auth.register'))

    else:
        return render_template("face.html")