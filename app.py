from flask import Flask, render_template, redirect, session, flash, request
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import UserForm, LoginForm
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///flask_feedback"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "userhero"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)

toolbar = DebugToolbarExtension(app)

def create_tables():
    db.create_all()

@app.route('/')
def home_page():
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if 'username' in session:
        return redirect(f'/users/{session["username"]}')
    
    form = UserForm()


    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data

        # Register new user
        new_user = User.register(username, password, email, first_name, last_name)
        db.session.add(new_user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()  # Rollback the transaction on failure
            form.username.errors.append('Username taken. Please pick another')
            return render_template('register.html', form=form)

        # Store user in session and flash a success message
        session['username'] = new_user.username
        flash('Welcome! You successfully created your account!', "success")
        return redirect(f'/users/{new_user.username}')

    # Render form for GET request or if form validation fails
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(f'/users/{session["username"]}')
    
    form = LoginForm()

    
    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)
        if user:
            session['username'] = user.username
            flash('Successfully logged in!', 'success')
            return redirect(f'/users/{user.username}')
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
        """Log out the user."""
        session.pop('username', None)
        flash("You have been logged out.", "success")
        return redirect('/login')

@app.route('/users/<username>', methods=['GET'])
def user_profile(username):
    """user page"""
    if 'username' not in session:
        flash("Please login first to access this page!", "danger")
        return redirect('/login')
    user = User.query.filter_by(username=username).first_or_404()
    feedback_list = Feedback.query.filter_by(username=username).all()

    return render_template('user_profile.html', user=user, feedback_list=feedback_list)

@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    """Remove the user and all feedback."""
    if 'username' not in session or session['username'] != username:
        flash("Please login first to access this page!", "danger")
        return redirect('/login')
    
    user = User.query.filter_by(username=username).first_or_404()
    Feedback.query.filter_by(username=username).delete()
    db.session.delete(user)
    db.session.commit()
    
    session.pop('username', None)
    flash("Your account has been deleted.", "success")
    return redirect('/')

@app.route('/users/<username>/feedback/add', methods=['GET', 'POST'])
def add_feedback(username):
    """Display a form to add feedback and handle feedback submission."""
    if 'username' not in session or session['username'] != username:
        flash("Please login first to access this page!", "danger")
        return redirect('/login')

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("Title and content are required.", "danger")
            return redirect(f'/users/{username}/feedback/add')

        feedback = Feedback(title=title, content=content, username=username)
        db.session.add(feedback)
        db.session.commit()
        flash("Feedback added!", "success")
        return redirect(f'/users/{username}')

    return render_template('add_feedback.html')

@app.route('/feedback', methods=['GET', 'POST'])
def user_feedback():
    """user feedback"""
    if 'username' not in session:
        flash("Please login first to access this page!", "danger")
        return redirect('/login')
    username = session['username']
    user = User.query.get(username)

    if request.method == "POST":
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("Title and Content are required.", "danger")
            return redirect('/feedback')
        
        feedback = Feedback(title=title, content=content, username=username)
        db.session.add(feedback)
        db.session.commit()
        flash("Feedback submitted successfully!", "success")
        return redirect('/feedback')
    user_feedback = Feedback.query.filter_by(username=username).all()

    return render_template('feedback.html', feedbacks=user_feedback) 

@app.route('/feedback/<int:feedback_id>/update', methods=['GET', 'POST'])
def edit_feedback(feedback_id):
    """Display a form to edit feedback and handle update submission."""
    feedback = Feedback.query.get_or_404(feedback_id)
    if 'username' not in session or session['username'] != feedback.username:
        flash("You do not have permission to edit this feedback.", "danger")
        return redirect('/login')

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if not title or not content:
            flash("Title and content are required.", "danger")
            return redirect(f'/feedback/{feedback_id}/update')

        feedback.title = title
        feedback.content = content
        db.session.commit()
        flash("Feedback updated!", "success")
        return redirect(f'/users/{feedback.username}')

    return render_template('edit_feedback.html', feedback=feedback)

@app.route('/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(feedback_id):
    """Delete a specific piece of feedback."""
    feedback = Feedback.query.get_or_404(feedback_id)
    if 'username' not in session or session['username'] != feedback.username:
        flash("You do not have permission to delete this feedback.", "danger")
        return redirect('/login')

    db.session.delete(feedback)
    db.session.commit()
    flash("Feedback deleted!", "success")
    return redirect(f'/users/{feedback.username}')
