import json
import os
import string

import face_recognition
import flask
import validators
from flask import redirect, render_template, flash, url_for, request
from flask_cors import cross_origin
from flask_login import login_required, current_user, logout_user
from werkzeug.security import generate_password_hash

from app import app
from .misc import writeImg
from .models import VotesModel, CandidateModel, UserModel, db


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/profile")
@login_required
def profile():
    prez = CandidateModel.query.filter_by(post="President").all()
    vice = CandidateModel.query.filter_by(post="Vice-President").all()
    voter = VotesModel.query.filter_by(voter_num=current_user.voter_num).first()
    return render_template("profile.html", name=current_user.name, prez=prez, vice=vice, voter=voter)


@app.route("/profile", methods=["GET", "POST"])
def post_vote():
    post_vote.president = request.form.get('president')
    post_vote.vicepresident = request.form.get('vice-president')

    voted = VotesModel.query.filter_by(voter_num=current_user.voter_num).first()
    if not voted:
        return redirect(url_for('facereg'))
    else:
        return redirect(url_for('profile'))


@app.route('/edit_member')
@login_required
def edit():
    return render_template("edit_user.html")


@app.route('/edit_member', methods=['POST'])
@login_required
def edit_member():
    email = request.form.get('email')
    name = request.form.get('name')
    password1 = request.form.get('password1')
    password2 = request.form.get('password2')

    user = UserModel.query.filter_by(email=email).first()  # if this returns a user, email already exists in db
    error = False
    # if a user or roll no is found, we want to redirect to signup page
    if current_user.email != request.form.get('email'):
        if user:
            flash('Email address already exists.', 'error')
            error = True

    if password1 != password2:  # if passwords do not match, redirect
        flash('Passwords do not match. Please try again.', 'error')
        error = True

    if (len(password1) or len(password2)) < 8:
        flash('Password too short. Should be atleast 8 characters.', 'error')
        error = True

    if not validators.email(email):
        flash('Enter a valid email', 'error')
        error = True

    if not set(name).issubset(string.ascii_letters + " "):
        flash('Name can only contain alphabets.', 'error')
        error = True

    if error:
        return redirect(url_for('edit_member'))
    else:
        user = db.engine.execute(
            f"UPDATE users SET email = '{email}', name = '{name}', password='{generate_password_hash(password1, method='sha256')}' WHERE voter_num = {current_user.voter_num}")
        # db.session.add(user)
        db.session.commit()
        flash('User successfully updated.', 'success')
        return redirect(url_for('edit_member'))


@app.route("/facereg", methods=["GET", "POST"])
@login_required
def facereg():
    if request.method == "POST":
        president = post_vote.president
        vicepresident = post_vote.vicepresident

        encoded_image = (request.form.get("pic") + "==").encode('utf-8')
        new_image_handle = open('./app/static/face/unknown/' + str(flask.session['_id']) + '.jpg', 'wb')
        new_image_handle.write(writeImg(encoded_image))
        new_image_handle.close()
        try:
            image_of_bill = face_recognition.load_image_file('./app/static/face/' + str(current_user.voter_num) + '.jpg')

        except:
            return render_template("camera.html", message=5)

        bill_face_encoding = face_recognition.face_encodings(image_of_bill)[0]

        unknown_image = face_recognition.load_image_file(
            './app/static/face/unknown/' + str(flask.session['_id']) + '.jpg')
        try:
            unknown_face_encoding = face_recognition.face_encodings(unknown_image)[0]
        except:
            return render_template("camera.html", message=2)

        # compare faces
        results = face_recognition.compare_faces([bill_face_encoding], unknown_face_encoding, tolerance=0.5)
        if results[0]:
            voter = VotesModel(voter_num=current_user.voter_num, voter_id=current_user.id, post_1=int(president),
                               post_2=int(vicepresident))
            db.session.add(voter)
            db.session.commit()
            os.remove('./app/static/face/unknown/' + str(flask.session['_id']) + '.jpg')
            return redirect(url_for('profile'))
        else:
            return render_template("camera.html", message=3)

    else:
        return render_template("camera.html")


@app.route("/candidate")
def candidate():
    prez = CandidateModel.query.filter_by(post="President").all()
    vice = CandidateModel.query.filter_by(post="Vice-President").all()
    return render_template("candidate.html", prez=prez, vice=vice)


@app.route("/candidate_register")
@login_required
def candidate_register():
    if current_user.admin != 1:
        logout_user()
        flash('You do not have required authorization')
        return redirect(url_for('auth.login'))
    else:
        return render_template("candidate_register.html")


@app.route("/candidate_register", methods=["POST"])
def candidate_post():
    voter_num = request.form.get('voter_num')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    post = request.form.get('post')
    pic_path = request.form.get('pic_path')
    agenda = request.form.get('agenda')

    voter_no = UserModel.query.filter_by(voter_num=voter_num).first()
    cand = CandidateModel.query.filter_by(voter_num=voter_num).first()

    error = False

    if not 10000000 <= int(voter_num) < 99999999:
        flash('Roll Number is not valid. Should be 8 digits.', 'error')
        error = True

    if cand:
        flash('Candidate has already been registered.', 'error')
        return redirect(url_for('candidate_register'))

    if not set(first_name).issubset(string.ascii_letters + " "):
        flash('Name can only contain alphabets.', 'error')
        error = True

    if not set(last_name).issubset(string.ascii_letters + " "):
        flash('Name can only contain alphabets.', 'error')
        error = True

    if not first_name and not last_name:
        flash('Name cannot be left blank.', 'error')
        error = True

    if error:
        return redirect(url_for('candidate_register'))
    else:
        candidate = CandidateModel(voter_num=voter_num, first_name=first_name, last_name=last_name, post=post,
                                   pic_path=pic_path, agenda=agenda)
        db.session.add(candidate)
        db.session.commit()
        flash('Candidate successfully registered.', 'success')
        return redirect(url_for('candidate_register'))


@app.route("/live_result")
def live_result():
    prez = CandidateModel.query.filter_by(post="President").all()
    vice = CandidateModel.query.filter_by(post="Vice-President").all()
    labels = []
    data = []
    labels1 = []
    data1 = []
    for candidate in prez:
        name = candidate.first_name + " " + candidate.last_name
        labels.append(name)
        vote = VotesModel.query.filter(VotesModel.post_1 == candidate.voter_num).count()
        data.append(vote)
    for candidate in vice:
        name = candidate.first_name + " " + candidate.last_name
        labels1.append(name)
        vote = VotesModel.query.filter(VotesModel.post_2 == candidate.voter_num).count()
        data1.append(vote)

    return render_template('graph.html', labels=labels, data=data, labels1=labels1, data1=data1)


@app.route("/vote/count")
@cross_origin()
def voteCount():
    prez = CandidateModel.query.filter_by(post="President").all()
    vice = CandidateModel.query.filter_by(post="Vice-President").all()
    labels = []
    data = []
    labels1 = []
    data1 = []
    for candidate in prez:
        name = candidate.first_name + " " + candidate.last_name
        labels.append(name)
        vote = VotesModel.query.filter(VotesModel.post_1 == candidate.voter_num).count()
        data.append(vote)
    for candidate in vice:
        name = candidate.first_name + " " + candidate.last_name
        labels1.append(name)
        vote = VotesModel.query.filter(VotesModel.post_2 == candidate.voter_num).count()
        data1.append(vote)

    output = {"data": data,
              "labels": labels,
              "data1": data1,
              "labels1": labels1}
    response = app.response_class(
        response=json.dumps(output),
        status=200,
        mimetype='application/json'
    )
    return response
