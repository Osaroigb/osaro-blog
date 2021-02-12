from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from datetime import datetime
import smtplib
import sqlalchemy

from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from functools import wraps
import os

# Setup Flask Application
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Setup authentication
login_manager = LoginManager()
login_manager.init_app(app)

# Gravatar images
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# Setup relational database
# CONFIGURE TABLES
class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    # *******Add parent relationship*******#
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # This will act like a List of Comment objects attached to each User.

    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):

    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)

    # ***************Child Relationship*************#
    # Create Foreign Key, "users.id" (the users refers to the tablename of User)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):

    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # *******Add child relationship*******#
    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def home():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():

        hashed_password = generate_password_hash(
            password=register_form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            email=register_form.email.data,
            password=hashed_password,
            name=register_form.name.data
        )

        db.session.add(new_user)

        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("You already signed up with that email, log in instead!")
            return redirect(url_for("login"))
        else:
            login_user(new_user)
            return redirect(url_for("home"))

    return render_template("register.html", form=register_form, user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():

        user_email = login_form.email.data
        user_password = login_form.password.data

        available_user = User.query.filter_by(email=user_email).first()

        if available_user:

            if check_password_hash(available_user.password, user_password):

                login_user(available_user)
                # if the above check passes, then we know the user exists and has the right credential
                return redirect(url_for("home"))
            else:
                flash("Incorrect password, please try again.")
                # if the password is wrong, reload the page
                return redirect(url_for("login"))
        else:
            flash("This email does not exist, please try again.")
            # if the user doesn't exist reload the page
            return redirect(url_for("login"))

    return render_template("login.html", form=login_form, user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/about")
def get_about():
    return render_template("about.html", user=current_user)


@app.route("/contact", methods=["GET", "POST"])
def get_contact():

    if request.method == "GET":

        return render_template("contact.html", user=current_user)

    elif request.method == "POST":

        data = request.form

        my_email = "emmyigbinovia@gmail.com"
        pass_word = "abisola12"
        other_email = "emmyigbinovia@gmail.com"
        text = f'Subject:Blog Message\n\nName: {data["name"]}\nEmail: {data["email"]}\nPhone: {data["number"]}\n' \
               f'Message: {data["message"]}'

        with smtplib.SMTP("smtp.gmail.com") as connection:
            connection.starttls()
            connection.login(user=my_email, password=pass_word)
            connection.sendmail(from_addr=my_email, to_addrs=other_email, msg=text)

        msg = "Successfully sent your message"

        return render_template("contact.html", msg=msg, user=current_user)


@app.route("/post/<int:index>", methods=["GET", "POST"])
def get_post(index):

    post_to_get = BlogPost.query.get(int(index))

    comment_list = Comment.query.all()
    comment_form = CommentForm()

    if comment_form.validate_on_submit():

        if current_user.is_authenticated:

            new_comment = Comment(
                text=comment_form.body.data,
                author_id=current_user.id,
                post_id=post_to_get.id
            )

            db.session.add(new_comment)
            db.session.commit()

            return redirect(url_for("home"))
        else:
            flash("You need to login or register to add comments.")
            return redirect(url_for("login"))

    return render_template("post.html", post=post_to_get, user=current_user,
                           form=comment_form, comments=comment_list)


@app.route("/new-post", methods=["GET", "POST"])
@login_required
@admin_only
def new_post():

    post_form = CreatePostForm()

    if post_form.validate_on_submit():

        today = datetime.now()
        formatted_date = today.strftime("%B %d, %Y")

        new_blogpost = BlogPost(
            author_id=current_user.id,
            title=post_form.title.data,
            subtitle=post_form.subtitle.data,
            date=formatted_date,
            body=post_form.body.data,
            img_url=post_form.img_url.data
        )

        db.session.add(new_blogpost)

        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("You already wrote a blog post with that title!")
            return redirect(url_for("new_post"))
        else:
            return redirect(url_for("home"))

    return render_template("make-post.html", form=post_form, user=current_user)


@app.route("/edit-post/<post_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_post(post_id):

    post_to_edit = BlogPost.query.get(int(post_id))

    edit_form = CreatePostForm(
        title=post_to_edit.title,
        subtitle=post_to_edit.subtitle,
        img_url=post_to_edit.img_url,
        author=post_to_edit.author,
        body=post_to_edit.body
    )

    if edit_form.validate_on_submit():

        post_to_edit.title = edit_form.title.data
        post_to_edit.subtitle = edit_form.subtitle.data
        post_to_edit.body = edit_form.body.data
        post_to_edit.author = edit_form.author.data
        post_to_edit.img_url = edit_form.img_url.data

        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            flash("You already wrote a blog post with that title!")
            return redirect(url_for("edit_post", post_id=post_id))
        else:
            return redirect(url_for("get_post", index=post_id))

    return render_template("make-post.html", post=post_to_edit, form=edit_form, user=current_user)


@app.route("/delete-post")
@login_required
@admin_only
def delete_post():
    post_id = request.args.get("index")
    post_to_delete = BlogPost.query.get(int(post_id))
    db.session.delete(post_to_delete)
    db.session.commit()

    return redirect(url_for("home"))


if __name__ == "__main__":
    # db.create_all()
    app.run(debug=True)
